# 情报页 MD 镜像规范（HTML ↔ MD 双份输出）

> 2026-08-24 定稿。原则：**每个弹幕情报 HTML 页必须同步生成同名 MD 镜像**，
> 存放于 `knowledge/intel_pages/`（文件名与 reports/ 下 HTML 一致，扩展名 .md）。
> MD 镜像 = HTML 内容的"可整理文本版"，不是摘要——必须覆盖 HTML 全部关键段，
> 方便情报库检索、跨会话理解与用户查询。

## 为什么需要 MD 镜像

```text
HTML 是发布层（人看、产品用）；JSON 是数据层（机器查）；
MD 是文本层（情报库整理、Agent 理解、全文检索、画像引用）。
三层同源：每场情报先落到 JSON 结构化库，再同时产出 HTML + MD。
```

## 硬性要求

1. 每生成一个 `reports/intel_danmu_*.html`，必须同步生成
   `knowledge/intel_pages/intel_danmu_*.md`，结构镜像 HTML 的 10 段骨架。
2. 缺少 MD 镜像 = 情报未交付（与"库里有、页面没有"同级防错）。
3. 内容必须覆盖：
   - 元信息（比赛/联赛/赛制/时间/数据源/条数/结果状态）；
   - 10 段正文（结果总览 / 逐局复盘 / 队伍画像 / 人员画像 / 灰信号 /
     联赛规律 / 预测验证 / 盘口 / 含义 LONG-SHORT / 溯源）；
   - 验证与回填状态（弹幕口径 vs 官方确认）。
4. 灰信号段必须带纪律声明（观众质疑非结论），与 HTML 一致。
5. 引用可溯源：数据文件路径、Polymarket 事件 slug、外部交叉来源。

## MD 镜像文件名与 reports 对应

```text
reports/intel_danmu_DNS-KRX_2026-08-24.html
  -> knowledge/intel_pages/intel_danmu_DNS-KRX_2026-08-24.md
```

## 目录结构

```text
knowledge/intel_pages/
  README.md                 镜像索引（按日期/联赛聚合）
  intel_danmu_<场次>_<日期>.md   每场一份全文镜像
```

## 与情报库其他层的关系

```text
docs/data/intel/*.json   <- 结构化数据层（机器查询/画像/统计）
knowledge/intel_pages/   <- MD 文本层（全文镜像，可读可检索）
knowledge/DANMU_INTEL.md <- 聚合账本（每场一条批次记录，链接镜像）
reports/intel_*.html     <- 发布层（SAP 风格，用户/产品展示）
reports/intel_quick_lookup.html 等 <- 查询层（从 JSON 生成，用户自助查）
```
