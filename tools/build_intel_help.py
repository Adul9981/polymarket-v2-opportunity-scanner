#!/usr/bin/env python3
"""Build the public help/FAQ page and the site-wide assistant assets."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
VERSION = "20261124a"

TG_CONSULT = "https://t.me/serene7mc"
TG_CHANNEL = "https://t.me/polymarket_ad/"


FAQ_ITEMS = [
    {
        "topic": "start",
        "label": "第一次来应该先看哪里",
        "keywords": ["第一次", "怎么用", "入口", "开始", "先看", "导航", "网站", "使用"],
        "answer": {
            "title": "先看今日比赛，再进入赛前情报",
            "lead": "网站把赛程、队伍与选手数据、赛前市场共识和历史复盘放在同一套页面里。",
            "points": [
                ["今日比赛", "查看今天已确认的场次、开赛时间和当前状态。"],
                ["赛前情报", "查看队伍近期表现、联赛排名、名单、伤停、地图或英雄池与市场数据。"],
                ["完整数据页", "每场可展开完整 JSON、CSV，并支持排序、打印和导出。"],
                ["历史情报库", "比赛结束后回看结果、验证结论和复盘闭环。"],
            ],
            "footer": "推荐路径：今日比赛 → 对应赛前情报 → 完整数据页。",
        },
    },
    {
        "topic": "match",
        "label": "比赛基本情况包含哪些内容",
        "keywords": ["比赛情况", "比赛数据", "基本信息", "队伍", "联赛", "排名", "近期", "h2h", "交手"],
        "answer": {
            "title": "先确认比赛对象、时间和赛制",
            "lead": "一场比赛的基础层包括比赛项目、联赛、对阵双方、开赛时间、赛制和当前状态。",
            "points": [
                ["队伍层", "近期战绩、赛季排名、主客场或联盟记录、连胜连败和 H2H。"],
                ["赛事层", "联赛阶段、赛制、赛程、积分榜、射手榜或赛事队伍统计。"],
                ["电竞专项", "阵容名单、选手指标、地图池、英雄池、BP 与位置数据。"],
                ["足球与 NBA", "伤停、首发或近期首发、球队统计、球员统计和联赛排名。"],
            ],
            "footer": "比赛页的价值不是堆字段，而是让你能在同一时间口径下做横向比较。",
        },
    },
    {
        "topic": "status",
        "label": "比赛状态会自动更新吗",
        "keywords": ["状态", "更新时间", "自动更新", "进行中", "已结束", "未开始", "刷新"],
        "answer": {
            "title": "会更新，但事实状态优先于页面时间",
            "lead": "赛程与状态由自动发布流程持续刷新；页面同时参考官方状态、赛事源和已完成的小局/结算信号。",
            "points": [
                ["状态口径", "未开始、进行中、已结束以结构和官方状态优先，弹幕不能单独决定比赛结果。"],
                ["跨时区", "页面按北京时间展示，底层事件时间可能使用 UTC。"],
                ["数据延迟", "外部源本身可能延迟；页面会保留抓取时间，不用旧数据伪装成实时。"],
                ["异常情况", "状态冲突或数据缺口会标注待确认，不会为了页面完整而硬写结论。"],
            ],
            "footer": "如果你看到状态与官方比分离散，优先以官方结算和页面最新抓取时间为准。",
        },
    },
    {
        "topic": "prematch",
        "label": "赛前情报里有什么",
        "keywords": ["赛前", "情报", "完整数据", "地图池", "英雄池", "伤停", "首发", "名单", "选手"],
        "answer": {
            "title": "赛前情报是一套结构化数据包",
            "lead": "它不是一张摘要卡，而是把一场比赛能用于分析的字段拆成可浏览、可导出的详情页。",
            "points": [
                ["LoL / CS2 / Dota2", "队伍统计、全部选手数据、赛事名单、近期比赛、H2H、地图池或英雄池。"],
                ["足球 / NBA", "联赛排名、近期表现、伤停、名单或近期首发、球队与球员统计、H2H。"],
                ["市场层", "只展示赛前市场共识与去水概率，不把赔率当成确定胜率。"],
                ["缺口层", "没有样本、没有官方首发或 provider 未返回时会明确标缺口。"],
            ],
            "footer": "详情页提供 JSON 与 CSV 下载，适合继续做自己的表和分析。",
        },
    },
    {
        "topic": "lineup",
        "label": "阵容和首发是官方确认的吗",
        "keywords": ["阵容", "首发", "名单", "伤停", "替补", "换人", "official", "官方"],
        "answer": {
            "title": "必须区分赛事名单、近期首发和本场官方首发",
            "lead": "这三种数据的证明强度不同，不能混写。",
            "points": [
                ["赛事名单", "只说明该队在该赛事登记过哪些人。"],
                ["近期首发", "说明过去比赛使用过什么阵容，不代表本场一定沿用。"],
                ["本场官方首发", "要等比赛方正式公布或官方阵容接口确认。"],
                ["伤停与缺阵", "有来源就展示，没有来源就标待确认，不根据旧名单猜。"],
            ],
            "footer": "未确认时页面会明确写“首发待官方确认”。",
        },
    },
    {
        "topic": "market",
        "label": "市场百分比是不是胜率",
        "keywords": ["百分比", "胜率", "赔率", "概率", "市场", "共识", "盘口", "热门"],
        "answer": {
            "title": "百分比是市场共识，不是真实概率",
            "lead": "页面会把赛前市场报价换算并去水，但它仍只是当时市场愿意交易出的价格。",
            "points": [
                ["能说明什么", "市场参与者如何定价、哪一方更热门、价格是否快速变化。"],
                ["不能说明什么", "不能保证结果，也不能替代阵容、伤停、地图池和临场信息。"],
                ["强热门也会输", "高百分比不等于稳赢，低百分比也不等于没有机会。"],
                ["风险", "薄市场、临近开赛和突发消息都会让价格迅速失效。"],
            ],
            "footer": "把市场共识当作一条证据，不要把它当作结论。",
        },
    },
    {
        "topic": "hallucination",
        "label": "幻觉的核心识别方法",
        "keywords": ["幻觉", "识别", "真假", "假消息", "编造", "可靠", "可信", "验证", "错误"],
        "answer": {
            "title": "幻觉不是“看起来像真的”，而是表示与底层约束不一致",
            "lead": "识别情报幻觉，重点不是文字是否流畅，而是它有没有来源、时间、身份和可证伪条件。",
            "points": [
                ["来源幻觉", "结论没有来源，或把单一转述写成事实。先问：证据在哪里？"],
                ["时间幻觉", "用旧阵容、旧排名或旧伤停冒充当前状态。先问：是什么时候的数据？"],
                ["身份幻觉", "队伍别名、选手昵称或位置被错误匹配。先问：对象是否唯一？"],
                ["因果幻觉", "观众情绪、盘口波动或单场样本被写成确定原因。先问：这只是相关还是因果？"],
                ["概率幻觉", "把市场价、模型值或历史命中率当成确定结果。先问：样本、误差和反例是什么？"],
            ],
            "footer": "最有效的反幻觉动作：看来源、看时间、看缺口、找反例。",
        },
    },
    {
        "topic": "evidence",
        "label": "事实、共识和推测怎么分开",
        "keywords": ["事实", "共识", "推测", "证据", "标签", "置信", "多源", "来源"],
        "answer": {
            "title": "把证据分层，结论才不会混在一起",
            "lead": "页面优先把事实、市场共识、观众信号和 AI 推断分开呈现。",
            "points": [
                ["事实层", "官方赛程、比赛结果、阵容与可核验统计。"],
                ["市场层", "报价、去水概率、流动性和价格变化。"],
                ["共识层", "弹幕、评论或历史样本形成的群体倾向，只代表共识。"],
                ["推断层", "基于已有证据做出的可能解释，必须标为推测。"],
            ],
            "footer": "没有证据的合理想象，不应出现在事实栏。",
        },
    },
    {
        "topic": "missing",
        "label": "为什么有些比赛没有完整数据",
        "keywords": ["没有数据", "数据缺失", "缺口", "为空", "找不到", "样本不足", "provider"],
        "answer": {
            "title": "缺失不是把字段填满，而是明确告诉用户缺什么",
            "lead": "外部比赛组件并不总能提供完整字段，某些赛事阶段、球员或联赛本身就没有历史样本。",
            "points": [
                ["名单可用但统计不足", "能看到人，但没有足够场次计算个人指标。"],
                ["赛事未返回", "外部结构源临时失败或尚未建立该场数据。"],
                ["本场未确认", "阵容、伤停或首发仍待官方信息。"],
                ["市场缺口", "比赛卡仍保留，但不展示伪造赔率。"],
            ],
            "footer": "无样本不硬撑，是本站比“字段看起来很多”更重要的原则。",
        },
    },
    {
        "topic": "personal",
        "label": "这个网站是谁做的",
        "keywords": ["个人", "作者", "站长", "是谁", "介绍", "coveym", "serene", "背景"],
        "answer": {
            "title": "coveym · 预测市场与赛事情报研究",
            "lead": "我长期记录预测市场、电竞赛事前情报、足球与 NBA 数据核验，以及交易与判断的复盘。",
            "points": [
                ["关注方向", "数据可追溯、结论可证伪、过程可复盘。"],
                ["工具目标", "把分散的比赛信息整理成能快速比较和继续分析的结构化页面。"],
                ["内容原则", "不承诺收益，不把观众情绪当事实，不用旧数据冒充当前状态。"],
                ["公开入口", "YouTube @coveym，Telegram 个人号 @serene7mc，频道 @polymarket_ad。"],
            ],
            "footer": "这个站点的核心不是“预测答案”，而是减少信息差和认知幻觉。",
        },
    },
    {
        "topic": "contact",
        "label": "怎么联系或关注更新",
        "keywords": ["联系", "咨询", "客服", "tg", "telegram", "频道", "个人号", "合作", "关注"],
        "answer": {
            "title": "根据目的选择入口",
            "lead": "工具问题、合作和具体咨询走个人号；日常更新和公开观察走频道。",
            "points": [
                ["个人咨询", "@serene7mc · 工具使用、数据问题、合作与具体交流。"],
                ["TG 频道", "@polymarket_ad · 网站更新、赛事观察和公开内容。"],
                ["网站内", "先看今日比赛、赛前情报和历史情报库，再针对具体比赛提问。"],
            ],
            "footer": "涉及具体数据问题时，附上比赛名称、页面链接和截图会更快定位。",
            "cta": True,
        },
    },
    {
        "topic": "risk",
        "label": "会保证盈利吗",
        "keywords": ["保证", "赚钱", "盈利", "收益", "推荐", "下注", "稳赢", "风险"],
        "answer": {
            "title": "不保证收益，也不替你做交易决定",
            "lead": "本站提供比赛资料、结构化数据和识别幻觉的方法，不构成投资或投注建议。",
            "points": [
                ["数据有误差", "来源延迟、样本不足和口径差异都可能影响判断。"],
                ["市场会变化", "阵容、伤停、临场信息和价格都可能快速改变。"],
                ["历史不等于未来", "过去命中不能保证下一次结果。"],
                ["先控制风险", "任何决策都应先确定能承受的最大损失。"],
            ],
            "footer": "工具负责提供证据，最终决策和风险由使用者本人承担。",
        },
    },
    {
        "topic": "mobile",
        "label": "手机和电脑都能用吗",
        "keywords": ["手机", "电脑", "移动端", "兼容", "平板", "浏览器", "页面"],
        "answer": {
            "title": "手机与桌面共用一套响应式页面",
            "lead": "导航、比赛列表、详情表格和问答助手会根据屏幕宽度重新排版。",
            "points": [
                ["手机", "问答助手使用底部全宽面板；宽表格可横向滚动。"],
                ["桌面", "问答助手固定在右侧；详情页仍可排序、打印和导出。"],
                ["长内容", "FAQ 使用折叠项，默认只展开你正在看的问题。"],
                ["访问", "GitHub Pages 和服务器地址都可以打开同一套站点。"],
            ],
            "footer": "如果手机上出现内容溢出，优先反馈具体页面与机型。",
        },
    },
]


QUICK_QUESTIONS = [
    "第一次来应该先看哪里",
    "比赛基本情况包含哪些内容",
    "幻觉的核心识别方法",
    "阵容和首发是官方确认的吗",
    "市场百分比是不是胜率",
    "怎么联系或关注更新",
]


HELP_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<link rel="icon" type="image/svg+xml" href="../favicon.svg">
<meta name="description" content="弹幕情报台使用指南、比赛数据说明、AI 幻觉识别与常见问题。">
<title>问答与使用指南 · 弹幕情报台</title>
<style>
:root{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--accent:#0071e3;--soft:#eaf3ff;--warm:#fff7ed;--warm-line:#fed7aa;--green:#16845b;--green-soft:#edf9f3}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.65;-webkit-font-smoothing:antialiased}
main{width:min(1120px,calc(100% - 32px));margin:0 auto;padding:34px 0 72px}
.hero{padding:clamp(28px,6vw,62px);border-radius:30px;background:radial-gradient(circle at 88% 0%,#dcecff 0,transparent 38%),linear-gradient(145deg,#fff,#fafdff);border:1px solid var(--line);box-shadow:0 18px 60px rgba(29,29,31,.06)}
.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:800}
h1{margin:12px 0 14px;font-size:clamp(34px,6vw,64px);line-height:1.04;letter-spacing:-.045em;max-width:820px}
.lead{max-width:760px;margin:0;color:var(--sub);font-size:clamp(15px,2vw,19px)}
.actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:24px}
.btn{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:0 18px;border-radius:999px;text-decoration:none;font-size:14px;font-weight:700;border:1px solid var(--line);background:#fff;color:var(--ink);cursor:pointer}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.quicknav{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0 0}
.quicknav a{padding:16px;border-radius:18px;background:rgba(255,255,255,.82);border:1px solid var(--line);text-decoration:none;color:var(--ink)}
.quicknav b{display:block;font-size:14px}.quicknav span{display:block;margin-top:4px;color:var(--sub);font-size:12px}
.section{margin-top:34px;scroll-margin-top:70px}
.section-head{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin-bottom:14px}
h2{margin:0;font-size:clamp(23px,3.5vw,34px);letter-spacing:-.03em}
.section-head p{margin:0;color:var(--sub);font-size:13px;max-width:620px}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:22px;padding:22px;box-shadow:0 8px 28px rgba(29,29,31,.04)}
.card h3{margin:0 0 10px;font-size:17px}
.card p{margin:0;color:var(--sub);font-size:13px}
.fields{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:14px}
.field{padding:13px 14px;border-radius:14px;background:#fafafa;border:1px solid var(--line)}
.field b{display:block;font-size:12px}.field span{display:block;margin-top:4px;color:var(--sub);font-size:11.5px}
.hallucination{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}
.hcard{padding:17px;border-radius:18px;background:#fff;border:1px solid var(--line)}
.hcard .num{display:grid;place-items:center;width:30px;height:30px;border-radius:9px;background:var(--warm);border:1px solid var(--warm-line);color:#9a5a13;font-size:11px;font-weight:800}
.hcard h3{margin:12px 0 7px;font-size:14px}.hcard p{margin:0;color:var(--sub);font-size:12px}.hcard strong{display:block;margin-top:10px;font-size:11.5px;color:#8a4d10}
.faq{display:grid;gap:9px}
details{background:#fff;border:1px solid var(--line);border-radius:16px;overflow:hidden}
summary{cursor:pointer;padding:15px 18px;font-size:14px;font-weight:700;list-style:none;display:flex;align-items:center;gap:10px}
summary::-webkit-details-marker{display:none}
summary:after{content:"+";margin-left:auto;color:var(--accent);font-size:19px;font-weight:500}
details[open] summary:after{content:"−"}
.answer{padding:0 18px 17px;color:var(--sub);font-size:13px}
.answer ul{margin:8px 0 0;padding-left:18px}.answer li{margin:5px 0}
.note{margin-top:12px;padding:12px 14px;border-radius:13px;background:var(--soft);color:#24537e;font-size:12px}
.profile{display:grid;grid-template-columns:1.15fr .85fr;gap:16px}
.profile .card:first-child{background:linear-gradient(145deg,#fff,#f8fbff)}
.profile ul{margin:12px 0 0;padding-left:18px;color:var(--sub);font-size:13px}.profile li{margin:6px 0}
.contact{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-top:10px;padding:14px 16px;border-radius:14px;background:#fafafa;border:1px solid var(--line);text-decoration:none;color:var(--ink)}
.contact b{display:block;font-size:13px}.contact span{display:block;color:var(--sub);font-size:11px;margin-top:2px}.contact em{font-style:normal;color:var(--accent);font-weight:800}
.start{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.start a{padding:18px;border-radius:18px;background:#fff;border:1px solid var(--line);color:var(--ink);text-decoration:none}
.start b{display:block}.start span{display:block;margin-top:5px;color:var(--sub);font-size:12px}
footer{margin-top:36px;text-align:center;color:var(--sub);font-size:11px;line-height:1.8}
@media(max-width:880px){.quicknav,.hallucination{grid-template-columns:repeat(2,1fr)}.profile{grid-template-columns:1fr}.start{grid-template-columns:1fr}}
@media(max-width:620px){main{width:min(100% - 20px,1120px);padding-top:18px}.hero{border-radius:22px}.quicknav,.grid,.fields,.hallucination{grid-template-columns:1fr}.section-head{display:block}.section-head p{margin-top:6px}.card{padding:18px;border-radius:18px}.actions .btn{width:100%}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
</style>
</head>
<body>
<main>
<section class="hero">
<div class="eyebrow">HELP CENTER / ANTI-HALLUCINATION</div>
<h1>看懂比赛数据，也看懂数据什么时候会骗人。</h1>
<p class="lead">这里说明比赛情报包含什么、数据如何更新、阵容和概率应该怎样理解，并提供一套识别 AI 幻觉与叙事幻觉的检查方法。</p>
<div class="actions">
<a class="btn primary" href="today.html">从今日比赛开始</a>
<a class="btn" href="intel_prematch.html">打开赛前情报</a>
<button class="btn" type="button" data-assistant-open>打开问答助手</button>
</div>
<div class="quicknav">
<a href="#match"><b>01 比赛基本情况</b><span>时间、赛制、状态和数据字段</span></a>
<a href="#hallucination"><b>02 幻觉识别</b><span>五类最常见的情报失真</span></a>
<a href="#faq"><b>03 常见问题</b><span>阵容、概率、更新与缺口</span></a>
<a href="#about"><b>04 关于与联系</b><span>个人介绍、TG 频道与咨询</span></a>
</div>
</section>

<section class="section" id="match">
<div class="section-head"><h2>比赛基本情况</h2><p>先确认对象、时间和赛制，再进入队伍、选手与市场层。</p></div>
<div class="grid">
<article class="card"><h3>基础信息</h3><p>项目、联赛、双方、开赛时间、赛制与当前状态构成一场比赛的最底层事实。</p><div class="fields">
<div class="field"><b>比赛项目</b><span>LoL、CS2、Dota2、足球、NBA</span></div>
<div class="field"><b>联赛与阶段</b><span>一级项目分类，二级联赛或赛事</span></div>
<div class="field"><b>开赛时间</b><span>页面默认按北京时间展示</span></div>
<div class="field"><b>当前状态</b><span>未开始 / 进行中 / 已结束 / 待确认</span></div>
</div></article>
<article class="card"><h3>队伍与选手</h3><p>赛前详情把近期表现、排名、名单、伤停和选手指标放在同一口径里，便于横向比较。</p><div class="fields">
<div class="field"><b>近期表现</b><span>近场胜负、主客场、连胜连败</span></div>
<div class="field"><b>联赛排名</b><span>赛季位置、分区与联盟记录</span></div>
<div class="field"><b>名单与伤停</b><span>赛事名单、近期首发、缺阵情况</span></div>
<div class="field"><b>选手数据</b><span>样本、均值、百分位和全部字段</span></div>
</div></article>
</div>
<div class="note"><b>口径提醒：</b>“赛事名单”和“最近首发”不等于本场官方首发。只有比赛方正式确认后，才会作为本场阵容事实。</div>
</section>

<section class="section" id="hallucination">
<div class="section-head"><h2>幻觉的核心识别</h2><p>流畅、具体、看起来很专业，都不等于真实。先检查来源、时间、身份、因果和概率。</p></div>
<div class="hallucination">
<article class="hcard"><div class="num">01</div><h3>来源幻觉</h3><p>没有来源，或把单一转述写成事实。</p><strong>先问：证据在哪里？</strong></article>
<article class="hcard"><div class="num">02</div><h3>时间幻觉</h3><p>旧阵容、旧排名、旧伤停冒充当前状态。</p><strong>先问：数据是什么时候的？</strong></article>
<article class="hcard"><div class="num">03</div><h3>身份幻觉</h3><p>队伍别名、选手昵称和位置被错误匹配。</p><strong>先问：对象是否唯一？</strong></article>
<article class="hcard"><div class="num">04</div><h3>因果幻觉</h3><p>盘口波动、情绪或单场样本被写成确定原因。</p><strong>先问：相关还是因果？</strong></article>
<article class="hcard"><div class="num">05</div><h3>概率幻觉</h3><p>市场价、模型值和历史命中率被当成保证。</p><strong>先问：样本和反例呢？</strong></article>
</div>
<div class="grid" style="margin-top:14px">
<article class="card"><h3>证据分层</h3><p>事实层看官方赛程、结果和确认阵容；市场层看报价与去水概率；共识层看观众与历史样本；推断层必须明确标注推测。</p></article>
<article class="card"><h3>最有效的反幻觉动作</h3><p>看来源、看时间、看身份映射、看数据缺口，再主动寻找反例。任何一条关键结论都应该能被证伪。</p></article>
</div>
</section>

<section class="section" id="faq">
<div class="section-head"><h2>常见问题解答</h2><p>点击问题展开。悬浮助手也能按关键词直接回答。</p></div>
<div class="faq">
<details open><summary>第一次来应该先看哪里？</summary><div class="answer">推荐路径：<b>今日比赛 → 对应赛前情报 → 完整数据页</b>。比赛结束后再从历史情报库回看结果、验证过程和复盘结论。</div></details>
<details><summary>比赛状态会自动更新吗？</summary><div class="answer">会。自动发布流程持续刷新赛程和状态，并优先使用官方状态、赛事源和已完成信号。外部源延迟时会保留抓取时间并标注待确认。</div></details>
<details><summary>赛前情报包含哪些数据？</summary><div class="answer">LoL、CS2、Dota2 包括队伍统计、全部选手数据、赛事名单、近期比赛、H2H、地图池或英雄池；足球和 NBA 包括排名、近期表现、伤停、名单或近期首发、球队和球员统计。</div></details>
<details><summary>阵容或首发是官方确认的吗？</summary><div class="answer">页面严格区分“赛事名单”“近期首发”和“本场官方首发”。前两者不能冒充本场阵容，未确认时会明确写待官方确认。</div></details>
<details><summary>市场百分比等于真实胜率吗？</summary><div class="answer">不等于。它表示赛前市场共识和当时可交易价格，不能替代阵容、伤停、地图池、临场信息，也不保证结果。</div></details>
<details><summary>为什么有些比赛没有完整数据？</summary><div class="answer">可能是赛事阶段没有历史样本、外部结构源未返回、本场阵容尚未确认或市场数据缺口。页面选择明确留空，不伪造字段。</div></details>
<details><summary>能否下载后继续分析？</summary><div class="answer">可以。单场完整数据页提供 JSON 和 CSV，并支持表头排序、打印和另存为 PDF。</div></details>
<details><summary>网站会保证盈利或给出稳赢推荐吗？</summary><div class="answer">不会。本站提供资料、结构化数据和判断方法，不构成投资或投注建议，也不承诺收益。</div></details>
<details><summary>手机和电脑都能用吗？</summary><div class="answer">可以。页面采用响应式布局；手机端问答助手为底部全宽面板，宽表格可横向滚动，桌面端为右侧悬浮面板。</div></details>
</div>
</section>

<section class="section" id="about">
<div class="section-head"><h2>个人情况与联系</h2><p>为什么做这个站，以及从哪里继续了解。</p></div>
<div class="profile">
<article class="card">
<h3>coveym · 预测市场与赛事情报研究</h3>
<p>长期记录预测市场、电竞赛事前情报、足球与 NBA 数据核验，以及判断过程的复盘。</p>
<ul>
<li>关注可追溯的数据、可证伪的结论和可复盘的决策。</li>
<li>把分散的比赛信息整理成适合继续分析的结构化页面。</li>
<li>不把观众情绪当事实，不用旧数据冒充当前状态。</li>
<li>对外只提供研究参考，不承诺盈利，也不替用户做交易决定。</li>
</ul>
</article>
<article class="card">
<h3>继续了解</h3>
<p>工具问题、数据反馈和合作走个人号；网站更新与公开观察走频道。</p>
<a class="contact" href="__TG_CONSULT__" target="_blank" rel="noopener noreferrer" data-track-link="telegram"><div><b>个人咨询 · Telegram</b><span>@serene7mc</span></div><em>↗</em></a>
<a class="contact" href="__TG_CHANNEL__" target="_blank" rel="noopener noreferrer" data-track-link="telegram"><div><b>TG 更新频道</b><span>@polymarket_ad</span></div><em>↗</em></a>
</article>
</div>
</section>

<section class="section" id="start">
<div class="section-head"><h2>现在开始使用</h2><p>先从你最关心的问题进入，不需要先读完所有说明。</p></div>
<div class="start">
<a href="today.html"><b>看今天有什么比赛</b><span>赛程、时间和当前状态</span></a>
<a href="intel_prematch.html"><b>看完整赛前数据</b><span>队伍、选手、地图与市场</span></a>
<a href="history.html"><b>看历史与复盘闭环</b><span>结果验证和跨场积累</span></a>
</div>
</section>
<footer>问答助手只回答站内固定知识库中的问题，不开放生成式自由作答，不保存聊天记录。<br>资料仅供研究与信息参考，不构成投资或投注建议。</footer>
</main>
</body>
</html>
"""


ASSISTANT_CSS = """#di-assistant-root{position:fixed;inset:auto 0 0 auto;z-index:9998;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;color:#1d1d1f}
#di-assistant-root *{box-sizing:border-box}
.di-assistant-launcher{position:fixed;right:max(18px,env(safe-area-inset-right));bottom:max(18px,env(safe-area-inset-bottom));z-index:9998;display:flex;align-items:center;gap:8px;border:0;border-radius:999px;padding:12px 17px 12px 13px;background:#1d1d1f;color:#fff;box-shadow:0 12px 34px rgba(0,0,0,.2);font:700 13px/1 inherit;cursor:pointer}
.di-assistant-launcher:hover{background:#0071e3}
.di-assistant-panel{position:fixed;right:max(18px,env(safe-area-inset-right));bottom:max(78px,calc(env(safe-area-inset-bottom) + 70px));z-index:9999;display:flex;flex-direction:column;width:min(410px,calc(100vw - 28px));height:min(650px,calc(100dvh - 110px));background:#fff;border:1px solid #e5e5ea;border-radius:24px;box-shadow:0 22px 70px rgba(0,0,0,.2);overflow:hidden}
.di-assistant-panel[hidden]{display:none}
.di-assistant-head{display:flex;align-items:center;gap:11px;padding:13px 14px;border-bottom:1px solid #e5e5ea;background:rgba(255,255,255,.96)}
.di-assistant-mark{display:grid;place-items:center;width:38px;height:38px;border-radius:12px;background:#eaf3ff;color:#0071e3;font-size:17px;font-weight:800}
.di-assistant-title{min-width:0;flex:1}.di-assistant-title b{display:block;font-size:14px}.di-assistant-title span{display:block;margin-top:2px;color:#86868b;font-size:10px}
.di-assistant-close{border:0;border-radius:999px;background:#f2f2f4;color:#6e6e73;width:30px;height:30px;cursor:pointer}
.di-assistant-messages{flex:1;overflow-y:auto;overscroll-behavior:contain;padding:15px;background:#f7f8fa;display:flex;flex-direction:column;gap:10px}
.di-assistant-msg{max-width:91%;border-radius:17px;padding:11px 13px;font-size:12px;line-height:1.7;white-space:pre-wrap}
.di-assistant-msg.user{align-self:flex-end;background:#0071e3;color:#fff;border-bottom-right-radius:5px}
.di-assistant-msg.bot{align-self:flex-start;background:#fff;border:1px solid #e5e5ea;border-bottom-left-radius:5px}
.di-assistant-rich{max-width:95%;padding:14px;background:#fff;border:1px solid #e5e5ea;border-radius:17px;border-bottom-left-radius:5px}
.di-assistant-kicker{display:block;color:#0071e3;font-size:9px;letter-spacing:.08em;font-weight:800;text-transform:uppercase}
.di-assistant-rich h4{margin:5px 0 6px;font-size:14px;line-height:1.4}
.di-assistant-lead{margin:0;color:#515154;font-size:12px}
.di-assistant-points{display:grid;gap:7px;margin-top:10px}
.di-assistant-point{display:grid;grid-template-columns:88px 1fr;gap:7px;padding-top:7px;border-top:1px solid #f0f0f2;font-size:11px}
.di-assistant-point b{color:#1d1d1f}.di-assistant-point span{color:#6e6e73}
.di-assistant-footer{margin:11px 0 0;padding:9px 10px;border-radius:10px;background:#f2f7ff;color:#24537e;font-size:10.5px}
.di-assistant-cta{display:flex;flex-wrap:wrap;gap:7px;margin-top:11px}
.di-assistant-cta a{display:inline-flex;align-items:center;justify-content:center;min-height:31px;padding:0 11px;border-radius:999px;text-decoration:none;font-size:10.5px;font-weight:700;background:#0071e3;color:#fff}
.di-assistant-cta a.secondary{background:#fff;border:1px solid #d8d8dd;color:#3a3a3c}
.di-assistant-quick{display:flex;gap:6px;overflow-x:auto;padding:9px 11px 5px;background:#fff;border-top:1px solid #e5e5ea;scrollbar-width:none}
.di-assistant-quick::-webkit-scrollbar{display:none}
.di-assistant-quick button{flex:none;b:0;border:1px solid #d8d8dd;border-radius:999px;background:#fff;color:#6e6e73;padding:6px 9px;font:500 9.5px/1.2 inherit;cursor:pointer}
.di-assistant-compose{display:flex;gap:7px;padding:7px 10px 10px;background:#fff}
.di-assistant-compose input{min-width:0;flex:1;border:1px solid #d8d8dd;border-radius:12px;background:#f7f8fa;padding:9px 10px;font:12px/1.3 inherit;outline:none}
.di-assistant-compose input:focus{border-color:#0071e3;background:#fff}
.di-assistant-compose button{width:36px;height:36px;border:0;border-radius:11px;background:#0071e3;color:#fff;font-size:15px;cursor:pointer}
.di-assistant-disclaimer{text-align:center;padding:0 12px 8px;background:#fff;color:#a1a1a6;font-size:8.5px}
@media(max-width:640px){
 .di-assistant-launcher{right:12px;bottom:max(12px,env(safe-area-inset-bottom));padding:11px 15px 11px 12px}
 .di-assistant-panel{left:10px;right:10px;bottom:max(66px,calc(env(safe-area-inset-bottom) + 58px));width:auto;height:min(78dvh,680px);border-radius:20px}
 .di-assistant-point{grid-template-columns:76px 1fr}
}
@media(prefers-reduced-motion:reduce){.di-assistant-panel,.di-assistant-launcher{scroll-behavior:auto}}
"""


ASSISTANT_JS = """(() => {
  if (new URLSearchParams(location.search).get("embed") === "1") return;
  if (document.getElementById("di-assistant-root")) return;
  const FAQS = __FAQ_DATA__;
  const QUICK = __QUICK_DATA__;
  const inIntel = location.pathname.includes("/intel/");
  const helpHref = inIntel ? "intel_help.html" : "intel/intel_help.html";
  const root = document.createElement("div");
  root.id = "di-assistant-root";
  root.innerHTML = `
    <section class="di-assistant-panel" hidden aria-label="弹幕情报问答助手">
      <header class="di-assistant-head">
        <div class="di-assistant-mark">?</div>
        <div class="di-assistant-title"><b>弹幕情报助手</b><span>比赛数据 · 幻觉识别 · 使用答疑</span></div>
        <button class="di-assistant-close" type="button" aria-label="关闭问答助手">×</button>
      </header>
      <div class="di-assistant-messages" role="log" aria-live="polite"></div>
      <div class="di-assistant-quick"></div>
      <form class="di-assistant-compose">
        <input aria-label="输入问题" placeholder="问：这场比赛的阵容可靠吗？" maxlength="120" autocomplete="off">
        <button type="submit" aria-label="发送问题">↑</button>
      </form>
      <div class="di-assistant-disclaimer">固定知识库回答，不开放自由生成 · 不构成投注建议</div>
    </section>
    <button class="di-assistant-launcher" type="button" aria-label="打开问答助手"><span>?</span><span>问答助手</span></button>
  `;
  document.body.appendChild(root);
  const panel = root.querySelector(".di-assistant-panel");
  const launch = root.querySelector(".di-assistant-launcher");
  const close = root.querySelector(".di-assistant-close");
  const messages = root.querySelector(".di-assistant-messages");
  const quick = root.querySelector(".di-assistant-quick");
  const form = root.querySelector(".di-assistant-compose");
  const input = form.querySelector("input");

  const normal = (value) => String(value || "").normalize("NFKC").toLowerCase()
    .replace(/[\\s，。？！、,.!?;；:：()（）【】\\[\\]{}“”‘’"'`·\-_/]/g, "");
  const match = (text) => {
    const q = normal(text);
    let best = null;
    let bestScore = 0;
    for (const item of FAQS) {
      let score = normal(item.label).includes(q) || q.includes(normal(item.label)) ? 8 : 0;
      for (const word of item.keywords || []) {
        const w = normal(word);
        if (w && q.includes(w)) score += Math.max(1, Math.min(5, w.length));
      }
      if (score > bestScore) { best = item; bestScore = score; }
    }
    return bestScore > 0 ? best : {
      topic: "unknown",
      answer: {
        title: "这个问题还没有命中固定答案",
        lead: "换一种问法，或直接进入使用指南查看完整 FAQ。",
        points: [
          ["可以问", "比赛数据、状态更新、阵容与首发、市场概率、数据缺口。"],
          ["幻觉", "来源、时间、身份、因果、概率五类检查。"],
          ["联系", "个人号 @serene7mc，频道 @polymarket_ad。"],
        ],
        footer: "助手不会自由编造答案；未命中时会明确告诉你。",
        cta: true,
      },
    };
  };
  const addText = (text, role) => {
    const node = document.createElement("div");
    node.className = `di-assistant-msg ${role}`;
    node.textContent = text;
    messages.appendChild(node);
    messages.scrollTop = messages.scrollHeight;
  };
  const addAnswer = (item) => {
    const data = item.answer || {};
    const article = document.createElement("article");
    article.className = "di-assistant-rich";
    const kicker = document.createElement("span");
    kicker.className = "di-assistant-kicker";
    kicker.textContent = "INTEL GUIDE";
    const title = document.createElement("h4");
    title.textContent = data.title || item.label || "答案";
    const lead = document.createElement("p");
    lead.className = "di-assistant-lead";
    lead.textContent = data.lead || "";
    article.append(kicker, title, lead);
    if (data.points?.length) {
      const points = document.createElement("div");
      points.className = "di-assistant-points";
      for (const [label, value] of data.points) {
        const row = document.createElement("div");
        row.className = "di-assistant-point";
        const strong = document.createElement("b");
        strong.textContent = label;
        const span = document.createElement("span");
        span.textContent = value;
        row.append(strong, span);
        points.appendChild(row);
      }
      article.appendChild(points);
    }
    if (data.footer) {
      const footer = document.createElement("p");
      footer.className = "di-assistant-footer";
      footer.textContent = data.footer;
      article.appendChild(footer);
    }
    const actions = document.createElement("div");
    actions.className = "di-assistant-cta";
    const guide = document.createElement("a");
    guide.href = helpHref;
    guide.textContent = "查看完整指南";
    actions.appendChild(guide);
    if (data.cta) {
      const tg = document.createElement("a");
      tg.className = "secondary";
      tg.href = "https://t.me/serene7mc";
      tg.target = "_blank";
      tg.rel = "noopener noreferrer";
      tg.dataset.trackLink = "telegram";
      tg.textContent = "TG 个人号";
      const channel = document.createElement("a");
      channel.className = "secondary";
      channel.href = "https://t.me/polymarket_ad/";
      channel.target = "_blank";
      channel.rel = "noopener noreferrer";
      channel.dataset.trackLink = "telegram";
      channel.textContent = "TG 频道";
      actions.append(tg, channel);
    }
    article.appendChild(actions);
    messages.appendChild(article);
    messages.scrollTop = messages.scrollHeight;
  };
  const ask = (text) => {
    const q = String(text || "").trim();
    if (!q) return;
    addText(q, "user");
    addAnswer(match(q));
    input.value = "";
  };
  const open = () => {
    panel.hidden = false;
    launch.setAttribute("aria-expanded", "true");
    if (!messages.children.length) {
      addText("你好，我是弹幕情报助手。\\n\\n我可以解释比赛数据、状态更新、阵容口径、市场概率与幻觉识别。这里只使用固定知识库回答，不自由编造。", "bot");
    }
    setTimeout(() => input.focus({ preventScroll: true }), 30);
  };
  const shutdown = () => {
    panel.hidden = true;
    launch.setAttribute("aria-expanded", "false");
    launch.focus({ preventScroll: true });
  };
  launch.setAttribute("aria-expanded", "false");
  launch.addEventListener("click", open);
  close.addEventListener("click", shutdown);
  form.addEventListener("submit", (event) => { event.preventDefault(); ask(input.value); });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !panel.hidden) shutdown(); });
  document.querySelectorAll("[data-assistant-open]").forEach((button) => button.addEventListener("click", open));
  for (const q of QUICK) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = q;
    button.addEventListener("click", () => { open(); ask(q); });
    quick.appendChild(button);
  }
  if (location.hash === "#assistant" || new URLSearchParams(location.search).has("assistant")) open();
})();
"""


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    help_html = (
        HELP_HTML.replace("__TG_CONSULT__", TG_CONSULT)
        .replace("__TG_CHANNEL__", TG_CHANNEL)
        .replace("20261124a", VERSION)
    )
    assistant_js = (
        ASSISTANT_JS.replace("__FAQ_DATA__", json.dumps(FAQ_ITEMS, ensure_ascii=False))
        .replace("__QUICK_DATA__", json.dumps(QUICK_QUESTIONS, ensure_ascii=False))
    )
    (REPORTS / "intel_help.html").write_text(help_html, encoding="utf-8")
    (REPORTS / "assistant.css").write_text(ASSISTANT_CSS, encoding="utf-8")
    (REPORTS / "assistant.js").write_text(assistant_js, encoding="utf-8")
    print("wrote reports/intel_help.html, reports/assistant.css, reports/assistant.js")


if __name__ == "__main__":
    main()
