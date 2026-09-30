#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMM 钢铁 CBAM 成本计算器 —— feed.json 自动更新器 (v2)

每天在 GitHub Actions 上自动:
  1) 欧委会官方页 -> CBAM 证书季度价
  2) 中文站 news.smm.cn            -> 中文快讯 (只留钢铁口径)
  3) 英文站 news.metal.com 黑色频道 -> 英文快讯 (只留钢铁口径)
  4) feed.json 的 "curated" 区 = 每周由 Claude 从 SMM 内部接口挑的精选,
     自动抓取只排在它后面, 永不冲掉; 过了 until 日期自动退场

安全原则:
  - 任何一步失败都不写文件, 保留上一版 (页面永远有可用数据)
  - 抓不到就保留旧条目, 绝不写空
  - 中英分站、分开过滤; 英文列表强制剔除任何含中文的条目
  - 只有内容真的变了才写文件, 不产生空提交
"""
import json, re, sys, html, datetime, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
FEED = ROOT / "feed.json"

EC_URL = "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/price-cbam-certificates_en"

ZH_PAGES = [
    "https://news.smm.cn/keywords/CBAM",
    "https://news.smm.cn/keywords/%E7%A2%B3%E5%85%B3%E7%A8%8E",
    "https://news.smm.cn/keywords/%E9%92%A2%E9%93%81",
    "https://news.smm.cn/keywords/%E7%83%AD%E5%8D%B7",
    "https://news.smm.cn/keywords/%E9%92%A2%E6%9D%90",
]
EN_PAGES = ["https://news.metal.com/en/ferrous-metals"]

MAX_NEWS  = 6
MAX_AGE_D = 150

CJK = re.compile(r"[一-鿿]")
UA  = {"User-Agent": "Mozilla/5.0 (compatible; SMM-CBAM-feed/2.0)"}

ZH_STEEL = re.compile(
    "钢|铁矿|热卷|热轧|冷轧|螺纹|线材|板材|"
    "方坯|镀锌|镀层|粗钢|生铁|高炉|电炉|转炉|"
    "废钢|焦煤|焦炭|烧结|球团|铁水|型钢|中厚板|HRC|CRC")
ZH_OTHER = re.compile(
    "铝|铜|镍|锌|锡|铅|锂|钴|稀土|白银|黄金|"
    "多晶硅|工业硅|光伏|碳酸锂|钨|钼|锑")
EN_STEEL = re.compile(
    r"steel|iron ore|\bHRC\b|\bCRC\b|rebar|billet|slab|wire rod|galvani[sz]|"
    r"coking coal|\bcoke\b|pig iron|blast furnace|\bBOF\b|\bEAF\b|ferrous|scrap", re.I)
EN_OTHER = re.compile(
    r"copper|alumin|nickel|\bzinc\b|\btin\b|\blead\b|lithium|cobalt|rare earth|"
    r"silver|\bgold\b|polysilicon|photovoltaic|tungsten|molybdenum|antimony", re.I)

EN_MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"])}


def fetch(url, timeout=45):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    for enc in ("utf-8", "gb18030"):
        try: return raw.decode(enc)
        except UnicodeDecodeError: continue
    return raw.decode("utf-8", "ignore")


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).replace(" ", " ").strip()


def is_steel(title, lang):
    """只留钢铁口径: 必须命中钢铁词; 别的金属词出现得更靠前就丢掉。"""
    S, O = (ZH_STEEL, ZH_OTHER) if lang == "zh" else (EN_STEEL, EN_OTHER)
    ms = S.search(title)
    if not ms: return False
    mo = O.search(title)
    return not (mo and mo.start() < ms.start())


def fresh(iso, today):
    try: d = datetime.date(*map(int, iso.split("-")))
    except Exception: return False           # noqa: BLE001
    return 0 <= (today - d).days <= MAX_AGE_D


def parse_cert(page):
    out = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S | re.I):
        cells = [strip_tags(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
        if len(cells) < 3: continue
        qm = re.search(r"Q([1-4])\s*(20\d\d)|(20\d\d)\s*Q([1-4])", cells[0])
        if not qm: continue
        q, yr = qm.group(1) or qm.group(4), qm.group(2) or qm.group(3)
        for c in cells[1:]:
            pm = re.fullmatch(r"(\d{1,3})[.,](\d{1,2})", c.strip())
            if pm:
                v = float(pm.group(1) + "." + pm.group(2))
                if 1.0 <= v <= 1000.0: out["%s Q%s" % (yr, q)] = v
                break
    return out


def parse_zh(page, today):
    items, seen = [], set()
    pat = re.compile(r'<a[^>]+href="(https?://[^"]*?(?:/news/|/content/)[^"#?]*)"[^>]*>(.*?)</a>', re.S | re.I)
    for m in pat.finditer(page):
        url, t = m.group(1), re.sub(r"\s+", " ", strip_tags(m.group(2)))
        t = re.sub(r"^原创", "", t)
        if not (10 <= len(t) <= 64) or not CJK.search(t) or url in seen: continue
        dm = re.search(r"(20\d\d)-(\d{2})-(\d{2})", page[m.end(): m.end() + 6000])
        if not dm or not fresh(dm.group(0), today) or not is_steel(t, "zh"): continue
        seen.add(url)
        items.append({"d": "%s-%s" % (dm.group(2), dm.group(3)), "t": t, "u": url, "_s": dm.group(0)})
    return items


def parse_en(page, today):
    items, seen = [], set()
    pat = re.compile(r'<a[^>]+href="(https?://news\.metal\.com/[^"]*?newscontent/[^"#?]*)"[^>]*>(.*?)</a>', re.S | re.I)
    for m in pat.finditer(page):
        url, raw = m.group(1), re.sub(r"\s+", " ", strip_tags(m.group(2)))
        dm = re.search(r"([A-Z][a-z]{2})\s+(\d{1,2}),\s*(20\d\d)", raw)
        if not dm: continue
        t = re.sub(r"^\d+\s*", "", raw[:dm.start()].strip()).strip()
        if not (15 <= len(t) <= 90) or CJK.search(t) or url in seen: continue
        mo = EN_MONTHS.get(dm.group(1))
        if not mo: continue
        iso = "%s-%02d-%02d" % (dm.group(3), mo, int(dm.group(2)))
        if not fresh(iso, today) or not is_steel(t, "en"): continue
        seen.add(url)
        items.append({"d": "%s %d" % (dm.group(1), int(dm.group(2))), "t": t, "u": url, "_s": iso})
    return items


def finalize(items, limit, lang):
    out, seen = [], set()
    for it in sorted(items, key=lambda x: x.get("_s", ""), reverse=True):
        t = (it.get("t") or "").strip()
        if not t or t in seen: continue
        if lang == "en" and CJK.search(t): continue
        seen.add(t)
        out.append({"d": it.get("d", ""), "t": t, "u": it.get("u", "")})
        if len(out) >= limit: break
    return out


def main():
    today = datetime.date.today()
    feed  = json.loads(FEED.read_text("utf-8"))
    old   = json.dumps({k: v for k, v in feed.items() if k != "updated"}, ensure_ascii=False, sort_keys=True)
    cert, notes = dict(feed.get("cert", {})), []

    try:
        got = parse_cert(fetch(EC_URL))
        if got:
            for k, v in sorted(got.items()):
                if cert.get(k) != v: cert[k] = v; notes.append(k)
        else:
            print("WARN: 欧委会页面未解析到价格, 保持原值")
    except Exception as e:                                    # noqa: BLE001
        print("WARN: 证书价抓取失败 -> %s" % e)

    zh_new, en_new = [], []
    for u in ZH_PAGES:
        try:
            g = parse_zh(fetch(u), today); zh_new += g; print("  zh %-46s %d" % (u[-46:], len(g)))
        except Exception as e: print("WARN: %s -> %s" % (u, e))    # noqa: BLE001
    for u in EN_PAGES:
        try:
            g = parse_en(fetch(u), today); en_new += g; print("  en %-46s %d" % (u[-46:], len(g)))
        except Exception as e: print("WARN: %s -> %s" % (u, e))    # noqa: BLE001

    head_zh, head_en = [], []
    for k in notes:
        yr, q = k.split(" ")
        head_zh.append({"d": today.strftime("%m-%d"), "_s": "Z2",
                        "t": "欧委会公布 %s %s CBAM 证书价 €%.2f" % (yr, q, cert[k]), "u": EC_URL})
        head_en.append({"d": today.strftime("%b ") + str(today.day), "_s": "Z2",
                        "t": "EC publishes %s %s CBAM certificate price EUR %.2f" % (q, yr, cert[k]), "u": EC_URL})

    cur, cur_ok = feed.get("curated") or {}, True
    if cur.get("until"):
        try: cur_ok = datetime.date(*map(int, cur["until"].split("-"))) >= today
        except Exception: cur_ok = False                      # noqa: BLE001
    cur_zh = [dict(x, _s="Z1%03d" % (999 - i)) for i, x in enumerate(cur.get("zh", []))] if cur_ok else []
    cur_en = [dict(x, _s="Z1%03d" % (999 - i)) for i, x in enumerate(cur.get("en", []))] if cur_ok else []
    if cur and not cur_ok:
        print("  精选已过期 (until=%s), 本轮不用" % cur.get("until"))

    # 旧条目永远垫底: 抓取失败时滚动条不会缩水, 成功时又会被新条目顶下去
    prev_zh = [dict(x, _s="") for x in feed.get("news", {}).get("zh", [])]
    prev_en = [dict(x, _s="") for x in feed.get("news", {}).get("en", [])]
    zh = finalize(head_zh + cur_zh + zh_new + prev_zh, MAX_NEWS, "zh")
    en = finalize(head_en + cur_en + en_new + prev_en, MAX_NEWS, "en")
    if not zh_new and not cur_zh: print("WARN: 中文未抓到新条目, 保留旧快讯")
    if not en_new and not cur_en: print("WARN: 英文未抓到新条目, 保留旧快讯")
    if not zh or not en:
        print("ABORT: 快讯为空, 不写入"); return 0

    feed["cert"] = cert
    feed["news"] = {"zh": zh, "en": en}
    feed.setdefault("sources", {}).update({"cert": EC_URL, "news_zh": ZH_PAGES, "news_en": EN_PAGES})

    new = json.dumps({k: v for k, v in feed.items() if k != "updated"}, ensure_ascii=False, sort_keys=True)
    if new == old:
        print("no change"); return 0
    feed["updated"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    FEED.write_text(json.dumps(feed, ensure_ascii=False, indent=1) + "\n", "utf-8")
    print("updated: cert=%d zh=%d en=%d (精选 %d/%d)" % (len(cert), len(zh), len(en), len(cur_zh), len(cur_en)))
    return 0


if __name__ == "__main__":
    try: sys.exit(main())
    except Exception as e:                                    # noqa: BLE001
        print("FATAL: %s -- feed.json 未改动" % e); sys.exit(0)
