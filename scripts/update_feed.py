#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMM 钢铁 CBAM 计算器 —— feed.json 自动更新器 (v3, 每周一)

GitHub Actions 每周一自动:
  1) 欧委会官方页 -> CBAM 证书季度价, 写入 cert
  2) 有新季度价时, 在 news 顶部自动加一条中英快讯 (与 TRQ 追踪器同款写法)
  3) news 其余条目由 SMM 每周一整理, 脚本原样保留, 不抓任何新闻网站

安全原则:
  - 任何一步失败都不写文件, 保留上一版 (页面永远有可用数据)
  - 只有内容真的变了才写文件, 不产生空提交
"""
import json, re, sys, html, datetime, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
FEED = ROOT / "feed.json"
EC_URL = "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/price-cbam-certificates_en"
MAX_NEWS = 14
CJK = re.compile(r"[一-鿿]")
UA = {"User-Agent": "Mozilla/5.0 (compatible; SMM-CBAM-feed/3.0)"}
MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]


def fetch(url, timeout=45):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).replace("\xa0", " ").strip()


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


def prev_key(k):
    yr, q = k.split(" "); y, n = int(yr), int(q[1])
    return "%d Q%d" % (y - 1, 4) if n == 1 else "%d Q%d" % (y, n - 1)


def price_note(k, cert, today):
    yr, q = k.split(" "); v = cert[k]; p = cert.get(prev_key(k))
    zh = "欧委会公布 %s %s 证书价 €%.2f" % (yr, q, v)
    en = "Commission publishes the %s %s certificate price at €%.2f" % (q, yr, v)
    if p:
        pct = (v / p - 1) * 100
        zh += "，较上季 €%.2f %s %.1f%%" % (p, "上涨" if pct >= 0 else "下跌", abs(pct))
        en += ", %s %.1f%% from €%.2f the previous quarter" % ("up" if pct >= 0 else "down", abs(pct), p)
    zh += "；本计算器已自动切换。"
    en += "; the calculator has switched automatically."
    return ({"d": today.strftime("%m-%d"), "t": zh, "u": EC_URL},
            {"d": "%s %d" % (MON[today.month - 1], today.day), "t": en, "u": EC_URL})


def main():
    today = datetime.date.today()
    feed = json.loads(FEED.read_text("utf-8"))
    old = json.dumps({k: v for k, v in feed.items() if k != "updated"}, ensure_ascii=False, sort_keys=True)
    cert, new_keys = dict(feed.get("cert", {})), []
    try:
        got = parse_cert(fetch(EC_URL))
        if got:
            for k, v in sorted(got.items()):
                if cert.get(k) != v: cert[k] = v; new_keys.append(k)
        else:
            print("WARN: 欧委会页面未解析到价格, 保持原值")
    except Exception as e:                                    # noqa: BLE001
        print("WARN: 证书价抓取失败 -> %s" % e)

    news = feed.get("news") or {}
    zh, en = list(news.get("zh", [])), list(news.get("en", []))
    for k in sorted(new_keys):
        nz, ne = price_note(k, cert, today)
        if not any(("%s %s" % tuple(k.split(" "))) in (x.get("t") or "") and "证书价" in (x.get("t") or "") for x in zh):
            zh.insert(0, nz); en.insert(0, ne)
    en = [x for x in en if x.get("t") and not CJK.search(x["t"])]
    if not zh or not en:
        print("ABORT: 快讯为空, 不写入"); return 0

    feed["cert"] = cert
    feed["news"] = {"zh": zh[:MAX_NEWS], "en": en[:MAX_NEWS]}
    feed.pop("curated", None)
    new = json.dumps({k: v for k, v in feed.items() if k != "updated"}, ensure_ascii=False, sort_keys=True)
    if new == old:
        print("no change"); return 0
    feed["updated"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    FEED.write_text(json.dumps(feed, ensure_ascii=False, indent=1) + "\n", "utf-8")
    print("updated: cert=%d new=%s zh=%d en=%d" % (len(cert), new_keys, len(feed["news"]["zh"]), len(feed["news"]["en"])))
    return 0


if __name__ == "__main__":
    try: sys.exit(main())
    except Exception as e:                                    # noqa: BLE001
        print("FATAL: %s -- feed.json 未改动" % e); sys.exit(0)
