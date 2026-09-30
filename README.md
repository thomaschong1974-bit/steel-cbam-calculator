# SMM 钢铁 CBAM 成本计算器

单文件、自包含、中英双语的欧盟 CBAM（碳边境调节机制）钢铁成本测算工具。
覆盖 CN 72–73（不锈钢扁平材 7218–7223 除外）184 个 HS 编码、48 个原产国口径默认值、
7 条生产路线基准，以及欧盟钢铁进口关税配额（TRQ）283 个配额序号。

**在线地址**：https://thomaschong1974-bit.github.io/steel-cbam-calculator/

> 本工具为估算与商务参考，不构成合规、法律或税务意见。正式申报以欧盟 CBAM Registry 与
> 经核查的排放报告为准。

---

## 仓库结构

| 文件 | 作用 |
|---|---|
| `index.html` | 计算器本体。单文件、自包含、可离线打开 |
| `feed.json` | 每日自动更新的数据源：CBAM 证书季度价 + SMM 快讯 |
| `scripts/update_feed.py` | 刷新 `feed.json` 的脚本 |
| `.github/workflows/update-feed.yml` | 每天定时跑上面那个脚本并自动提交 |

## 自动更新怎么跑

每天 UTC 06:00（北京时间 14:00），GitHub Actions 会：

1. 抓欧委会官网的 CBAM 证书价 → 写入 `feed.json` 的 `cert`
2. 抓 SMM 中文站（`news.smm.cn`）与英文站（`news.metal.com` 黑色频道）的最新标题
   → 只留钢铁口径 → 写入 `feed.json` 的 `news`
3. 内容真的变了才提交，不产生空提交

页面打开时读 `feed.json`；**读不到、格式坏、数值异常，一律静默回退到 `index.html`
内嵌的值 —— 计算结果永远不会因为取数失败而出错。**

### `feed.json` 的三层快讯

上面的压下面的：

| 层 | 字段 | 来源 | 维护 |
|---|---|---|---|
| ① 证书价公告 | 自动生成 | 欧委会官网 | 自动 |
| ② 每周精选 | `curated` | SMM 内部接口挑选，中英双语 | 每周手动更新一次 |
| ③ 每日抓取 | `news` | SMM 公开页 | 自动 |

`curated.until` 是保鲜期，过期自动退场，自动抓取不会覆盖它。

## 首次部署

1. **Settings → Pages**：Source 选 `Deploy from a branch`，分支 `main`、目录 `/ (root)`
2. **Settings → Actions → General → Workflow permissions**：选 **Read and write permissions**
   （漏了这步，每天的自动更新推不上去）
3. **Actions → update-feed → Run workflow**：手动跑一次，出绿勾即正常

## 发客户的链接

在网址后加 `?who=` 标记来源，客户不用输任何东西即可使用：

```
https://thomaschong1974-bit.github.io/steel-cbam-calculator/?who=客户简称
```

Umami 的 `visit` / `probe_open_*` / `feedback` 事件会带上该标记；
客户点反馈按钮时，表单的「访问来源」字段自动预填。不带 `?who=` 也能正常打开。

## 数据来源

| 内容 | 依据 |
|---|---|
| 分原产国默认值 | IR (EU) 2025/2621，经 IR (EU) 2026/1740 更正（追溯自 2026-01-01） |
| 免费分配基准值 | IR (EU) 2025/2620（A/B 列，两个年份档） |
| 计算方法 | IR (EU) 2025/2547；Reg (EU) 2023/956；Reg (EU) 2025/2083（Omnibus） |
| CBAM 系数法律基础 | Directive 2003/87/EC Art 10a(1a) |
| 证书价 | 欧委会按季公布（2027 年起改为按周） |
| 钢铁进口配额 TRQ | Reg (EU) 2026/1384；IR (EU) 2026/1457 |

所有数值均按官方 Excel / PDF 逐条核对。

---

SMM · Shanghai Metals Market
