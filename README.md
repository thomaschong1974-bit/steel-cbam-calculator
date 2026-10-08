# SMM 钢铁 CBAM 计算器

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
| `feed.json` | 数据源：CBAM 证书季度价 + CBAM 快讯（每周一更新） |
| `scripts/update_feed.py` | 刷新 `feed.json` 的脚本 |
| `.github/workflows/update-feed.yml` | 每周一定时跑上面那个脚本并自动提交 |

## 更新节奏：每周一

与 [TRQ 配额追踪器](https://thomaschong1974-bit.github.io/eu-steel-trq/) 同款，**快讯固定每周一更新**。

| 内容 | 谁来更新 | 什么时候 |
|---|---|---|
| CBAM 证书价（`feed.json` 的 `cert`） | GitHub Actions 自动抓欧委会官网，有新价时在快讯顶部自动加一条 | 每周一 UTC 06:00 / 15:00（北京 14:00 / 23:00）；可在 Actions 页面手动加跑 |
| CBAM 快讯（`feed.json` 的 `news`） | Claude 每周一整理，产出新的 `feed.json`，用 GitHub Desktop 推送 | 每周一上午 |
| 顶部倒计时（⏳） | 页面自动计算，无需维护 | 实时 |

快讯条：点「CBAM 快讯 ▾」或点滚动区，展开「全部 CBAM 快讯（最新在上）」面板；× 或 Esc 关闭。

页面打开时读 `feed.json`；**读不到、格式坏、数值异常，一律静默回退到 `index.html`
内嵌的值 —— 计算结果永远不会因为取数失败而出错。**

## 首次部署

1. **Settings → Pages**：Source 选 `Deploy from a branch`，分支 `main`、目录 `/ (root)`
2. **Settings → Actions → General → Workflow permissions**：选 **Read and write permissions**
   （漏了这步，自动更新推不上去）
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
