import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const W = 1280;
const H = 720;
const BG = "#f5f5f7";
const INK = "#1d1d1f";
const INK2 = "#6e6e73";
const ACCENT = "#0071e3";
const ACCENT_SOFT = "#eaf2fd";
const CARD = "#ffffff";
const LINE = "#e8e8ed";
const FONT = "PingFang SC";

const p = Presentation.create({ slideSize: { width: W, height: H } });
let pageNo = 0;

function addText(slide, left, top, width, height, text, style = {}) {
  const box = slide.shapes.add({
    geometry: "textbox",
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  box.text = text;
  box.text.style = { typeface: FONT, color: INK, ...style };
  return box;
}

function addCard(slide, left, top, width, height, opts = {}) {
  return slide.shapes.add({
    geometry: "roundRect",
    position: { left, top, width, height },
    fill: opts.fill || CARD,
    line: { style: "solid", fill: opts.line || LINE, width: 1 },
    borderRadius: opts.radius || "rounded-2xl",
    ...(opts.shadow ? { shadow: opts.shadow } : {}),
  });
}

function addRule(slide, left, top, width, height, color = ACCENT) {
  slide.shapes.add({
    geometry: "rect",
    position: { left, top, width, height },
    fill: color,
    line: { style: "solid", fill: "none", width: 0 },
  });
}

function addBullets(slide, left, top, width, items, opts = {}) {
  const box = addText(slide, left, top, width, opts.height || items.length * 40, items, {
    fontSize: 17,
    color: INK,
    lineSpacing: 1.25,
    ...opts.style,
  });
  return box;
}

function chrome(slide, section) {
  pageNo += 1;
  addText(slide, 72, H - 44, 520, 20, section, { fontSize: 13, color: INK2 });
  addText(slide, W - 130, H - 44, 58, 20, String(pageNo).padStart(2, "0"), {
    fontSize: 13,
    color: INK2,
    alignment: "right",
  });
}

function header(slide, eyebrow, title, titleStyle = {}) {
  addText(slide, 72, 52, 700, 26, eyebrow, {
    fontSize: 15,
    bold: true,
    color: ACCENT,
  });
  addText(slide, 72, 84, W - 144, 78, title, {
    fontSize: 36,
    bold: true,
    color: INK,
    lineSpacing: 1.05,
    ...titleStyle,
  });
}

function notes(slide, lines) {
  slide.speakerNotes.textFrame.setText(lines);
  slide.speakerNotes.setVisible(true);
}

/* ------------------------------------------------------------------ */
/* Slide 1 — cover                                                     */
/* ------------------------------------------------------------------ */
{
  const s = p.slides.add();
  s.background.fill = BG;
  addText(s, 72, 208, 720, 30, "分享讨论 · 基于 Polymarket 公开数据", {
    fontSize: 17,
    bold: true,
    color: ACCENT,
  });
  addRule(s, 72, 256, 96, 4);
  addText(s, 72, 286, 1136, 150, "预测市场，到底是不是赌博？", {
    fontSize: 56,
    bold: true,
    color: INK,
    lineSpacing: 1.05,
  });
  addText(s, 72, 452, 1000, 44, "以及——没有优势的人，该怎么参与", {
    fontSize: 26,
    color: INK2,
  });
  addText(s, 72, 528, 900, 30, "用真实数据拆解：结构优势 / 信息优势 / 资金与分散 · 2026-08", {
    fontSize: 16,
    color: INK2,
  });
  notes(s, [
    "开场（约 30 秒）：今天想和大家认真聊一个问题——预测市场到底是不是赌博？这个问题的答案，决定你该不该进场、以及进场后怎么活下来。",
    "我不是来给结论的，我是带着数据来的：过去两周我们拆了四组 Polymarket 上的真实案例，今天的分享就是这些数据的解读。",
    "",
    "[Sources] 内容基于本项目拆解：docs/forensics/KNOWLEDGE_BASE.md、docs/forensics/STRATEGY_LIBRARY.md、docs/forensics/cases/README.md",
  ]);
}

/* ------------------------------------------------------------------ */
/* Slide 2 — agenda                                                    */
/* ------------------------------------------------------------------ */
{
  const s = p.slides.add();
  s.background.fill = BG;
  header(s, "今天的路线", "三个问题，一条主线");
  const rows = [
    ["01", "预测市场是赌博吗？", "先给一个会被质疑的结论，再用期望值拆开看。"],
    ["02", "长期盈利的人，到底靠什么？", "三种能从数据里看见的优势：结构、信息、资金与分散。"],
    ["03", "没有优势的人，该怎么参与？", "三个可执行的起点——以及一条现在就该走的路。"],
  ];
  rows.forEach((r, i) => {
    const y = 200 + i * 142;
    addCard(s, 72, y, 1136, 118, { shadow: "shadow-sm" });
    addText(s, 104, y + 32, 76, 54, r[0], {
      fontSize: 36,
      bold: true,
      color: ACCENT,
      alignment: "center",
    });
    addText(s, 210, y + 24, 420, 34, r[1], { fontSize: 22, bold: true });
    addText(s, 210, y + 62, 950, 30, r[2], { fontSize: 16, color: INK2 });
  });
  chrome(s, "预测市场 · 是不是赌博");
  notes(s, [
    "先告诉大家今天要讲什么：三个问题。第一个问题帮我们摆正心态，第二个问题用数据回答'赢家凭什么赢'，第三个问题落到你自己身上——没有优势，怎么参与。",
    "全程大约 XX 分钟，中间留几次讨论。",
  ]);
}

/* ------------------------------------------------------------------ */
/* Slide 3 — conclusion first                                          */
/* ------------------------------------------------------------------ */
{
  const s = p.slides.add();
  s.background.fill = BG;
  addText(s, 72, 150, 600, 30, "先说结论", {
    fontSize: 16,
    bold: true,
    color: ACCENT,
  });
  addText(s, 72, 210, 1136, 130, "预测市场不是赌博——它是零和的交易市场。", {
    fontSize: 42,
    bold: true,
    color: INK,
    lineSpacing: 1.15,
  });
  addText(s, 72, 360, 1136, 130, "但对“没有优势的人”来说，进去之后的结果，和赌博没有区别。", {
    fontSize: 42,
    bold: true,
    color: ACCENT,
    lineSpacing: 1.15,
  });
  addText(s, 72, 530, 1136, 40, "那些地址能长期盈利，不是因为他们运气好，是因为他们带着优势进来。", {
    fontSize: 18,
    color: INK2,
  });
  chrome(s, "预测市场 · 是不是赌博");
  notes(s, [
    "先给结论，再拆逻辑：预测市场本身不是赌博，它是零和的交易市场。",
    "但这句话有个残酷的尾巴——对没有优势的人，进去之后的结果和赌博没有区别。",
    "后面我会用四组真实数据证明：长期盈利的地址，靠的不是运气，是三种看得见的优势。",
  ]);
}

/* ------------------------------------------------------------------ */
/* Slide 4 — casino vs prediction market                               */
/* ------------------------------------------------------------------ */
{
  const s = p.slides.add();
  s.background.fill = BG;
  header(s, "先分清两件事", "赌场游戏和预测市场，输赢的决定因素完全不同");

  addCard(s, 72, 196, 550, 330, { shadow: "shadow-sm" });
  addText(s, 100, 220, 180, 28, "赌场游戏", {
    fontSize: 15,
    bold: true,
    color: INK2,
  });
  addText(s, 100, 254, 480, 40, "轮盘 / 老虎机", { fontSize: 26, bold: true });
  addBullets(s, 100, 316, 500, [
    "庄家固定抽水，期望值永远是负的",
    "你玩得越久，越确定亏光",
    "输赢和“你是谁”无关",
  ]);

  addCard(s, 658, 196, 550, 330, { shadow: "shadow-sm" });
  addText(s, 686, 220, 180, 28, "预测市场", {
    fontSize: 15,
    bold: true,
    color: ACCENT,
  });
  addText(s, 686, 254, 480, 40, "Polymarket", { fontSize: 26, bold: true });
  addBullets(s, 686, 316, 500, [
    "零和：每一块钱的盈利，都来自另一个人的亏损",
    "没有庄家固定抽水（暂不计手续费与返佣）",
    "输赢取决于：你和对手相比，有没有优势",
  ]);

  addText(s, 72, 566, 1136, 44, "所以决定结果的是“相对优势”，不是运气。", {
    fontSize: 22,
    bold: true,
    color: INK,
    alignment: "center",
  });
  chrome(s, "预测市场 · 是不是赌博");
  notes(s, [
    "赌场游戏：庄家固定抽水，期望值恒为负，玩得越久越确定亏光，而且和你是谁无关。",
    "预测市场：近似零和，没有庄家固定抽水。每一块钱的盈利都来自另一个人的亏损。所以能不能赢，取决于你相对于对手有没有优势。",
    "注意两个限定：第一，这里说的零和暂不计平台手续费与返佣，返佣是平台给做市和流动性的激励，不是庄家抽水；第二，结论是“和没有优势的人相比”，不是绝对说法。",
    "",
    "[Sources] 对比框架与限定说明：docs/forensics/prediction_market_vs_gambling.html",
  ]);
}

/* ------------------------------------------------------------------ */
/* Slide 5 — implication                                                */
/* ------------------------------------------------------------------ */
{
  const s = p.slides.add();
  s.background.fill = BG;
  addText(s, 72, 218, 1136, 80, "市场不是赌场；", {
    fontSize: 48,
    bold: true,
    color: INK,
    alignment: "center",
  });
  addText(s, 72, 312, 1136, 80, "但如果你没有优势，", {
    fontSize: 48,
    bold: true,
    color: INK,
    alignment: "center",
  });
  addText(s, 72, 406, 1136, 80, "你就成了别人优势的燃料。", {
    fontSize: 48,
    bold: true,
    color: ACCENT,
    alignment: "center",
  });
  addText(s, 72, 540, 1136, 36, "这不是吓唬人——下一页开始，我们用数据看赢家到底带什么进场。", {
    fontSize: 17,
    color: INK2,
    alignment: "center",
  });
  chrome(s, "预测市场 · 是不是赌博");
  notes(s, [
    "把上一页推到结论：市场不是赌场，但如果你没有优势，你就是别人优势的燃料。",
    "这句话听着刺耳，但它可以被数据检验。接下来四组案例，就是检验过程。",
  ]);
}

/* ------------------------------------------------------------------ */
/* Slide 6 — datasets                                                   */
/* ------------------------------------------------------------------ */
{
  const s = p.slides.add();
  s.background.fill = BG;
  header(s, "我们手里的数据", "四组真实案例，覆盖三种优势");

  const cards = [
    ["e46m3 · 吉达温度组", "结构套利", "11 档完整集，Σp 长期偏离 $1", "单轮毛利 4.7%~6.4%"],
    ["fkigedgjdgwbg · EDG vs LGD", "信息优势", "LGD 盘口 20 分钟 0.57 → 0.99", "追买 $277,608"],
    ["深水机器人簇 · GX vs VIT G2", "资金 + 分散", "深水（≤0.15）买家逐一画像", "145 人 / 86k 份"],
    ["赢家账户对照 · 两场同日比赛", "5.4 倍差距", "889 个跨场共同赢家", "场均 $3,559 vs $658"],
  ];
  const pos = [
    [72, 196],
    [658, 196],
    [72, 396],
    [658, 396],
  ];
  cards.forEach((c, i) => {
    const [x, y] = pos[i];
    addCard(s, x, y, 550, 172, { shadow: "shadow-sm" });
    addText(s, x + 28, y + 22, 300, 30, c[1], {
      fontSize: 14,
      bold: true,
      color: ACCENT,
    });
    addText(s, x + 28, y + 52, 500, 32, c[0], { fontSize: 21, bold: true });
    addText(s, x + 28, y + 94, 500, 30, c[2], { fontSize: 16, color: INK2 });
    addText(s, x + 28, y + 128, 500, 30, c[3], {
      fontSize: 18,
      bold: true,
      color: INK,
    });
  });
  addText(s, 72, 596, 1136, 30, "数据全部来自公开行情与链上记录，每一组都能溯源到原始文件。", {
    fontSize: 15,
    color: INK2,
    alignment: "center",
  });
  chrome(s, "预测市场 · 是不是赌博");
  notes(s, [
    "先交代数据：我们拆了四组案例——吉达温度组的完整集套利、EDG vs LGD 的盘口异动、GX vs VIT 的深水买家画像、以及两场同日比赛的赢家对照。",
    "这些全部来自 Polymarket 公开行情和链上记录，不是推测，是可溯源的原始数据。",
    "",
    "[Sources] docs/forensics/cases/2026-08-12_jeddah_temperature/、docs/forensics/data/fkigedgjdgwbg/、docs/forensics/cases/2026-08-15_lol-gx-vit-game2-address/、docs/forensics/cases/2026-08-18_lol-winner-accounts-t1gen-drxbro/",
  ]);
}

/* ------------------------------------------------------------------ */
/* Slide 7 — three edges overview                                       */
/* ------------------------------------------------------------------ */
{
  const s = p.slides.add();
  s.background.fill = BG;
  header(s, "赢家们带什么进场", "三种优势，每一种都能从数据里看到");

  const cols = [
    {
      n: "01",
      name: "结构优势",
      what: "利润与预测结果无关，由数学规则保证",
      why: "检测 Σp 偏离 $1，买低估侧，Convert 兑现",
      copy: "复制门槛：工具 + 返佣",
    },
    {
      n: "02",
      name: "信息优势",
      what: "知道别人不知道的（甚至是不该知道的）",
      why: "价格被打到位后，确认信息再下大注",
      copy: "复制门槛：不可复制，且有边界",
    },
    {
      n: "03",
      name: "资金 + 分散",
      what: "大数法则把波动变成确定性",
      why: "几百笔小额深水，少数赢家覆盖多数输家",
      copy: "复制门槛：本金 + 纪律",
    },
  ];
  cols.forEach((c, i) => {
    const x = 72 + i * 392;
    addCard(s, x, 196, 352, 372, { shadow: "shadow-sm" });
    addText(s, x + 28, 224, 120, 54, c.n, {
      fontSize: 40,
      bold: true,
      color: ACCENT,
    });
    addText(s, x + 28, 292, 300, 36, c.name, { fontSize: 24, bold: true });
    addText(s, x + 28, 336, 300, 60, c.what, {
      fontSize: 16,
      color: INK2,
      lineSpacing: 1.25,
    });
    addText(s, x + 28, 404, 300, 60, c.why, {
      fontSize: 16,
      color: INK,
      lineSpacing: 1.25,
    });
    addText(s, x + 28, 500, 300, 34, c.copy, {
      fontSize: 15,
      bold: true,
      color: ACCENT,
    });
  });
  addText(s, 72, 606, 1136, 36, "长期盈利的账户，至少带着其中一种；你看到的动作，只是优势的外表。", {
    fontSize: 18,
    bold: true,
    color: INK,
    alignment: "center",
  });
  chrome(s, "三种优势");
  notes(s, [
    "三种优势的总览。第一种是结构优势——利润和预测结果无关，是数学规则保证的。第二种是信息优势——知道别人不知道的。第三种是资金加分散——用大数法则把波动变成确定性。",
    "注意每种优势的复制门槛：结构需要工具和返佣，信息几乎不可复制而且有边界，资金分散需要本金和纪律。",
  ]);
}

/* ------------------------------------------------------------------ */
/* Slide 8 — structural edge: e46m3                                    */
/* ------------------------------------------------------------------ */
{
  const s = p.slides.add();
  s.background.fill = BG;
  header(s, "优势 01 · 结构", "e46m3：不猜比赛，做完整集套利");

  addCard(s, 72, 196, 520, 400, { shadow: "shadow-sm" });
  addText(s, 100, 220, 300, 30, "它怎么运作", {
    fontSize: 16,
    bold: true,
    color: ACCENT,
  });
  const steps = [
    ["1", "检测", "同一组结果的 YES 价格之和 Σp 偏离 $1"],
    ["2", "买入", "买被低估的一侧（例如全套 NO）"],
    ["3", "兑现", "Convert / Merge 立刻换成现金，不等结算"],
  ];
  steps.forEach((st, i) => {
    const y = 266 + i * 96;
    addText(s, 100, y, 52, 40, st[0], {
      fontSize: 22,
      bold: true,
      color: ACCENT,
    });
    addText(s, 166, y - 2, 150, 34, st[1], { fontSize: 19, bold: true });
    addText(s, 166, y + 30, 400, 34, st[2], { fontSize: 16, color: INK2 });
  });
  addText(s, 100, 548, 460, 36, "结论：与预测结果完全无关——它不是赌徒，是套利机器。", {
    fontSize: 16,
    bold: true,
    color: INK,
  });

  addCard(s, 628, 196, 580, 400, { shadow: "shadow-sm" });
  addText(s, 656, 220, 300, 30, "吉达温度组 · 实测数据", {
    fontSize: 16,
    bold: true,
    color: ACCENT,
  });
  const stats = [
    ["Σp = 1.0475 ~ 1.0640", "完整集定价偏离，全套 NO 被低估"],
    ["单轮毛利 4.7% ~ 6.4%", "约 30 秒一轮，循环兑现"],
    ["12 天 5,000 次 Convert", "单笔中位 $0.70，24×7 自动化"],
  ];
  stats.forEach((st, i) => {
    const y = 270 + i * 100;
    addText(s, 656, y, 530, 44, st[0], {
      fontSize: 28,
      bold: true,
      color: INK,
    });
    addText(s, 656, y + 48, 530, 30, st[1], { fontSize: 15, color: INK2 });
  });
  chrome(s, "三种优势");
  notes(s, [
    "先看结构优势，主角是 e46m3。它的运作只有三步：检测 Σp 偏离 1 美元、买入被低估的一侧、用 Convert 和 Merge 立刻兑现价差，不等结算。",
    "吉达温度组的实测数据：Σp 在 1.0475 到 1.0640 之间，单轮毛利 4.7% 到 6.4%，约 30 秒一轮；过去 12 天做了 5000 次 Convert，单笔中位 0.7 美元，24 小时不间断。",
    "重点：它的利润和预测结果完全无关——这是数学规则保证的。它不是赌徒，是套利机器。",
    "",
    "[Sources] docs/forensics/KNOWLEDGE_BASE.md §2、docs/forensics/cases/2026-08-12_jeddah_temperature/README.md、docs/forensics/data/e46m3/stats.json",
  ]);
}

/* ------------------------------------------------------------------ */
/* Slide 9 — information edge: fkigedgjdgwbg                           */
/* ------------------------------------------------------------------ */
{
  const s = p.slides.add();
  s.background.fill = BG;
  header(s, "优势 02 · 信息", "fkigedgjdgwbg：确认信息后，才下大注");

  addCard(s, 72, 196, 520, 400, { shadow: "shadow-sm" });
  addText(s, 100, 220, 320, 30, "EDG vs LGD · LGD 盘口时间线（UTC）", {
    fontSize: 16,
    bold: true,
    color: ACCENT,
  });
  const tl = [
    ["07:00", "0.57", "赛前，LGD 只是小热门"],
    ["07:20", "0.645", "开始异动"],
    ["07:40", "0.994", "20 分钟内拉到 0.99"],
    ["07:44 起", "0.95~0.999", "该地址开始大额追买"],
  ];
  tl.forEach((t, i) => {
    const y = 266 + i * 78;
    addText(s, 100, y, 110, 32, t[0], { fontSize: 16, bold: true, color: INK2 });
    addText(s, 218, y, 130, 32, t[1], {
      fontSize: 18,
      bold: true,
      color: ACCENT,
    });
    addText(s, 356, y, 210, 32, t[2], { fontSize: 15, color: INK2 });
  });

  addCard(s, 628, 196, 580, 400, { shadow: "shadow-sm" });
  addText(s, 656, 220, 320, 30, "8 月 14 日 · 账户行为", {
    fontSize: 16,
    bold: true,
    color: ACCENT,
  });
  const stats = [
    ["$277,608", "追买 LGD，成交价 0.95~0.999（三块盘合计）"],
    ["794 笔 / 单日", "全部为买入，合计约 $531,992，无任何卖出"],
    ["$81,676", "单笔最大赢利，历史累计 3,139 笔"],
  ];
  stats.forEach((st, i) => {
    const y = 270 + i * 100;
    addText(s, 656, y, 530, 44, st[0], {
      fontSize: 28,
      bold: true,
      color: INK,
    });
    addText(s, 656, y + 48, 530, 30, st[1], { fontSize: 15, color: INK2 });
  });

  addText(s, 72, 624, 1136, 40, "它是在信息确认后才下注；散户买在同一价位，就是在给它接盘。", {
    fontSize: 19,
    bold: true,
    color: INK,
    alignment: "center",
  });
  chrome(s, "三种优势");
  notes(s, [
    "第二种优势是信息优势。8 月 14 日 EDG 对 LGD，LGD 的盘口在 20 分钟里从 0.57 被拉到 0.99，而这个地址在价格打到位之后，以 0.95 到 0.999 的价格追买了 27.7 万美元。",
    "当天它 794 笔全部是买入、合计约 53 万美元，没有任何卖出；历史单笔最大赢利 8.1 万美元。",
    "这里要说明：假赛性质来自案例标注的外部推测，我们确认的是行为模式——它在信息确认后才下注。散户没有这个信息，买在同一价位，就是给它接盘。",
    "",
    "[Sources] docs/forensics/data/fkigedgjdgwbg/README.md、docs/forensics/cases/README.md（2026-08-14 EDG vs LGD 行）",
  ]);
}

/* ------------------------------------------------------------------ */
/* Slide 10 — capital + diversification                                 */
/* ------------------------------------------------------------------ */
{
  const s = p.slides.add();
  s.background.fill = BG;
  header(s, "优势 03 · 资金 + 分散", "深水机器人簇：用几百笔小注换确定性");

  addCard(s, 72, 196, 520, 400, { shadow: "shadow-sm" });
  addText(s, 100, 220, 300, 30, "它们的行为特征", {
    fontSize: 16,
    bold: true,
    color: ACCENT,
  });
  addBullets(s, 100, 272, 470, [
    "每天几十场，每场几百股",
    "只买 ≤ $0.15 的大劣势方（深水）",
    "GX vs VIT G2：深水共 145 人 / $8.5k / 86k 份",
    "大额买家几乎全是系统性深水机器",
  ]);

  addCard(s, 628, 196, 580, 400, { shadow: "shadow-sm" });
  addText(s, 656, 220, 300, 30, "为什么这样能赢", {
    fontSize: 16,
    bold: true,
    color: ACCENT,
  });
  addBullets(s, 656, 272, 530, [
    "单个深水单大概率归零——没关系",
    "几百笔里，赢的少数覆盖输的多数",
    "大数法则把波动变成了确定性",
    "这是资金规模和纪律的组合，不是判断力",
  ]);

  addText(s, 72, 624, 1136, 40, "你想学的不是“买深水”，是它背后的分散结构。", {
    fontSize: 19,
    bold: true,
    color: INK,
    alignment: "center",
  });
  chrome(s, "三种优势");
  notes(s, [
    "第三种优势是资金加分散。深水机器人每天几十场、每场几百股、只买 15 美分以下的大劣势方。GX 对 VIT 那场，深水买家共 145 人、8 万 6 千份，大额买家几乎全是系统性机器。",
    "它为什么能赢：单个深水单大概率归零，但几百笔里赢的少数覆盖输的多数——大数法则把波动变成了确定性。这是资金规模和纪律的组合，不是判断力。",
    "所以真正值得学的是分散结构，不是“买深水”这个动作。",
    "",
    "[Sources] docs/forensics/KNOWLEDGE_BASE.md 关键发现 10/11、docs/forensics/cases/2026-08-15_lol-gx-vit-game2-address/SITUATION_REPORT.md",
  ]);
}

/* ------------------------------------------------------------------ */
/* Slide 11 — 5.4x                                                      */
/* ------------------------------------------------------------------ */
{
  const s = p.slides.add();
  s.background.fill = BG;
  header(s, "一个反直觉的数字", "跨场赢家 vs 单场赢家：5.4 倍");

  addText(s, 72, 210, 1136, 130, "5.4×", {
    fontSize: 96,
    bold: true,
    color: ACCENT,
    alignment: "center",
  });
  addText(s, 72, 348, 1136, 40, "两场同日比赛（Gen.G vs T1 & DRX vs BRO）· 889 个共同赢家", {
    fontSize: 18,
    color: INK2,
    alignment: "center",
  });

  addCard(s, 190, 416, 430, 110, { shadow: "shadow-sm" });
  addText(s, 218, 436, 380, 40, "$3,559", {
    fontSize: 32,
    bold: true,
    color: INK,
    alignment: "center",
  });
  addText(s, 218, 478, 380, 30, "跨场赢家 · 场均盈利", {
    fontSize: 16,
    color: INK2,
    alignment: "center",
  });

  addCard(s, 660, 416, 430, 110, { shadow: "shadow-sm" });
  addText(s, 688, 436, 380, 40, "$658", {
    fontSize: 32,
    bold: true,
    color: INK,
    alignment: "center",
  });
  addText(s, 688, 478, 380, 30, "单场赢家 · 场均盈利", {
    fontSize: 16,
    color: INK2,
    alignment: "center",
  });

  addText(s, 72, 566, 1136, 50, "逻辑：长期盈利者都在用三种优势之一在玩；“买深水 / 买高位 / 买好比赛”只是优势的外表。", {
    fontSize: 18,
    bold: true,
    color: INK,
    alignment: "center",
  });
  chrome(s, "三种优势");
  notes(s, [
    "这个数字很反直觉：我们把两场同日比赛放在一起，889 个在两场都赢钱的账户，场均盈利 3559 美元，是单场赢家 658 美元的 5.4 倍。",
    "注意样本：这是两场具体比赛的对照，不是一个长期统计，但它指向同一件事——长期盈利的账户在用三种优势之一在玩。你看到的买深水、买高位、买好比赛，只是优势的外表。",
    "",
    "[Sources] docs/forensics/cases/2026-08-18_lol-winner-accounts-t1gen-drxbro/README.md",
  ]);
}

/* ------------------------------------------------------------------ */
/* Slide 12 — backtest                                                  */
/* ------------------------------------------------------------------ */
{
  const s = p.slides.add();
  s.background.fill = BG;
  header(s, "我们亲自验证 · 结构套利回测", "机会是真的，但门槛在执行质量，不是发现错价");

  addCard(s, 72, 196, 460, 400, { shadow: "shadow-sm" });
  addText(s, 100, 220, 300, 30, "回测结论（保守口径）", {
    fontSize: 16,
    bold: true,
    color: ACCENT,
  });
  addBullets(s, 100, 270, 410, [
    "结构机会真实且高频：吉达 24 小时出现 31 个错价窗口",
    "但边很薄：毛利约 0.3% / 轮，1% 滑点就吃掉大半",
    "taker 全收费、无返佣口径：净期望为负",
    "敏感性：只有“零滑点 + 100% 返佣”才转正（+$6.77）",
    "e46m3 只在 Σp≥1.0475 动手、挑腿买、叠返佣",
  ]);

  const rows = [
    ["指标", "吉达温度组", "Villarreal 比分"],
    ["Σp 范围", "0.989 ~ 1.0835", "0.957 ~ 1.0765"],
    ["错价窗口（≥2%）", "31 个 / 24h", "1 个 / 1.3h"],
    ["毛利（X=$10）", "$8.32", "$0.77"],
    ["摩擦（滑点+费+gas）", "$27.18", "$2.06"],
    ["保守口径净利", "−$18.86", "−$1.29"],
  ];
  const table = s.tables.add({
    rows: 6,
    columns: 3,
    left: 572,
    top: 216,
    width: 636,
    height: 300,
    columnWidths: [210, 213, 213],
    values: rows,
  });
  table.styleOptions = {
    headerRow: false,
    totalRow: false,
    firstColumn: false,
    lastColumn: false,
    bandedRows: false,
    bandedColumns: false,
  };
  table.borders.assign({ style: "solid", fill: LINE, width: 1 });
  for (let c = 0; c < 3; c += 1) {
    const cell = table.getCell(0, c);
    cell.fill = "#1d1d1f";
    cell.text.style = { typeface: FONT, fontSize: 15, bold: true, color: "#ffffff", alignment: "left" };
  }
  for (let r = 1; r < 6; r += 1) {
    for (let c = 0; c < 3; c += 1) {
      const cell = table.getCell(r, c);
      cell.fill = "#ffffff";
      cell.text.style = {
        typeface: FONT,
        fontSize: 15,
        color: r === 5 ? ACCENT : INK,
        bold: r === 5,
        alignment: "left",
      };
    }
  }

  addText(s, 72, 630, 1136, 36, "结论：结构套利不是“能不能发现”，而是“有没有工具和返佣把它做出来”。", {
    fontSize: 18,
    bold: true,
    color: INK,
    alignment: "center",
  });
  chrome(s, "我们自己的验证");
  notes(s, [
    "这是我们自己做的验证：把吉达和 Villarreal 的价格历史重放，模拟“买全套 NO → Convert → 拿现金”的完整流程，计入滑点、手续费和 gas。",
    "结论：结构机会是真的，而且高频——吉达 24 小时出现 31 个错价窗口。但边很薄：毛利只有投入的约 0.3%，1% 滑点就吃掉大半。保守口径（taker 全收费、无返佣）净期望为负；敏感性表里只有“零滑点加 100% 返佣”才转正。",
    "e46m3 的现实行为也印证了这一点：它只在 Σp 达到 4.7% 以上才动手、只挑部分腿买、还叠加返佣。所以门槛不在发现错价，在执行质量。",
    "",
    "[Sources] reports/forensics_arb_backtest_jeddah_prices_20260817-095544.md、reports/forensics_arb_backtest_e46m3_villarreal_exact_2026-08-12_20260817-095543.md、tools/forensics_arb_backtester.py",
  ]);
}

/* ------------------------------------------------------------------ */
/* Slide 13 — what it means for you                                     */
/* ------------------------------------------------------------------ */
{
  const s = p.slides.add();
  s.background.fill = BG;
  header(s, "那对你意味着什么", "诚实版本");

  addCard(s, 72, 196, 1136, 150, { shadow: "shadow-sm" });
  addText(s, 104, 222, 1080, 100, "你现在没有这三种优势——没有套利引擎、没有内幕信息、没有大资金分散。所以对你来说，当前方式下进入预测市场 ≈ 赌博。", {
    fontSize: 24,
    bold: true,
    color: INK,
    lineSpacing: 1.3,
  });

  addCard(s, 72, 372, 1136, 170, { shadow: "shadow-sm" });
  addText(s, 104, 398, 1080, 60, "你是在和带着优势的人玩零和游戏，长期期望是负的。", {
    fontSize: 22,
    bold: true,
    color: ACCENT,
  });
  addText(s, 104, 458, 1080, 60, "这不是侮辱你的判断力——判断力单独不构成优势：你的对手也有判断力，而且他们还有你没有的仓位结构。", {
    fontSize: 18,
    color: INK2,
    lineSpacing: 1.3,
  });

  addText(s, 72, 580, 1136, 50, "所以问题不是“该不该玩”，而是“以什么身份进场”。", {
    fontSize: 22,
    bold: true,
    color: INK,
    alignment: "center",
  });
  chrome(s, "怎么参与");
  notes(s, [
    "现在说点扎心的：这三种优势，你现在都没有。所以对你来说，当前方式下进入预测市场，和赌博没有区别——你是在和带优势的人玩零和游戏，长期期望为负。",
    "注意，这不是说你的判断力不行。判断力单独不构成优势，因为对手也有判断力，而且还有你没有的仓位结构。",
    "所以问题不是该不该玩，而是以什么身份进场。下一页开始讲怎么参与。",
  ]);
}

/* ------------------------------------------------------------------ */
/* Slide 14 — how to participate ①                                      */
/* ------------------------------------------------------------------ */
{
  const s = p.slides.add();
  s.background.fill = BG;
  header(s, "怎么参与 ①", "先停止“无优势的下注”");

  const cols = [
    ["30–50u 小账户", "先学会输得起", "用一笔归零也不影响生活的钱进场"],
    ["单笔 ≤ 30% 账户", "固定金额制", "不按比例加仓，不做“回本式”下注"],
    ["规则止损 + 先 dry-run", "实盘前先模拟", "所有动作先在模拟环境里过一遍"],
  ];
  cols.forEach((c, i) => {
    const x = 72 + i * 392;
    addCard(s, x, 210, 352, 300, { shadow: "shadow-sm" });
    addText(s, x + 28, 238, 300, 66, c[0], {
      fontSize: 25,
      bold: true,
      color: INK,
      lineSpacing: 1.15,
    });
    addText(s, x + 28, 316, 300, 34, c[1], {
      fontSize: 17,
      bold: true,
      color: ACCENT,
    });
    addText(s, x + 28, 356, 300, 90, c[2], {
      fontSize: 16,
      color: INK2,
      lineSpacing: 1.3,
    });
  });

  addText(s, 72, 556, 1136, 60, "这一步的意义：把劣势降到最低，把学费控制在可承受的范围。", {
    fontSize: 22,
    bold: true,
    color: INK,
    alignment: "center",
  });
  chrome(s, "怎么参与");
  notes(s, [
    "参与的第一步不是找机会，是止损自己的行为：30 到 50u 的小账户，先学会输得起；单笔不超过账户 30%，固定金额制，不按比例加仓；规则止损，实盘前先模拟。",
    "这些都是项目风控里的现成纪律，不是新发明。它们的意义只有一句话：把劣势降到最低，把学费控制在可承受范围。",
    "",
    "[Sources] config/risk_limits.json、AGENTS.md（固定金额制、先 dry-run）",
  ]);
}

/* ------------------------------------------------------------------ */
/* Slide 15 — how to participate ②                                      */
/* ------------------------------------------------------------------ */
{
  const s = p.slides.add();
  s.background.fill = BG;
  header(s, "怎么参与 ②", "用“彩票预算”学分散");

  addCard(s, 72, 210, 700, 320, { shadow: "shadow-sm" });
  addText(s, 104, 236, 600, 40, "深水小仓 = 深水机器人的“分散”结构", {
    fontSize: 24,
    bold: true,
    color: INK,
  });
  addBullets(s, 104, 296, 640, [
    "只买 ≤ 15¢ 价位的大劣势方",
    "单笔金额小到“归零也不心疼”",
    "用一批小注，而不是一把大注，去理解胜率结构",
  ]);
  addText(s, 104, 452, 640, 44, "目标：先学结构（怎么分配、怎么止损），再学动作。", {
    fontSize: 18,
    bold: true,
    color: ACCENT,
  });

  addCard(s, 808, 210, 400, 320, { fill: ACCENT_SOFT, line: "none" });
  addText(s, 836, 240, 344, 60, "一个提醒", {
    fontSize: 21,
    bold: true,
    color: ACCENT,
  });
  addText(s, 836, 306, 344, 150, "这不是“抄底致富”的捷径，是付学费买认知。\n深水机器人的钱来自几百笔的分散，不是单笔的命中。", {
    fontSize: 17,
    color: INK,
    lineSpacing: 1.35,
  });

  addText(s, 72, 566, 1136, 60, "彩票预算 = 你能承受的“学费上限”，不是仓位建议。", {
    fontSize: 20,
    bold: true,
    color: INK,
    alignment: "center",
  });
  chrome(s, "怎么参与");
  notes(s, [
    "第二步：用彩票预算学分散。深水小仓学的是深水机器人的分散结构——只买 15 美分以下的大劣势方，单笔金额小到归零也不心疼。",
    "提醒一下：这不是抄底致富的捷径，是付学费买认知。深水机器人的钱来自几百笔的分散，不是单笔的命中。",
  ]);
}

/* ------------------------------------------------------------------ */
/* Slide 16 — how to participate ③                                      */
/* ------------------------------------------------------------------ */
{
  const s = p.slides.add();
  s.background.fill = BG;
  header(s, "怎么参与 ③", "长期三条路，选一条认真走");

  const cols = [
    ["01", "结构", "套利 / 做市", "需要工具与返佣门槛——扫描与回测我们已经在建"],
    ["02", "信息", "情报库", "用公开数据建立可溯源的信息优势——进行中"],
    ["03", "纪律 + 时间", "资金分散", "慢，但每一分钱都在长本事"],
  ];
  cols.forEach((c, i) => {
    const x = 72 + i * 392;
    addCard(s, x, 210, 352, 310, { shadow: "shadow-sm" });
    addText(s, x + 28, 238, 120, 50, c[0], {
      fontSize: 34,
      bold: true,
      color: ACCENT,
    });
    addText(s, x + 28, 296, 300, 40, c[1], { fontSize: 24, bold: true });
    addText(s, x + 28, 340, 300, 34, c[2], {
      fontSize: 17,
      bold: true,
      color: ACCENT,
    });
    addText(s, x + 28, 384, 300, 100, c[3], {
      fontSize: 16,
      color: INK2,
      lineSpacing: 1.3,
    });
  });

  addText(s, 72, 556, 1136, 60, "三条都不急，但第一条路——停止无优势下注——现在就该走。", {
    fontSize: 22,
    bold: true,
    color: INK,
    alignment: "center",
  });
  chrome(s, "怎么参与");
  notes(s, [
    "长期只有三条路：结构，需要工具和返佣门槛，扫描与回测我们已经在建；信息，用公开数据建立可溯源的情报库，正在进行；纪律加时间，慢慢积累资金分散，慢但每一分都在长本事。",
    "三条都不急，但第一条路——停止无优势下注——现在就该走。",
  ]);
}

/* ------------------------------------------------------------------ */
/* Slide 17 — close                                                     */
/* ------------------------------------------------------------------ */
{
  const s = p.slides.add();
  s.background.fill = BG;
  addText(s, 72, 128, 1136, 90, "预测市场不是赌博，但“没有优势的人预测”就是赌博。", {
    fontSize: 38,
    bold: true,
    color: INK,
    alignment: "center",
    lineSpacing: 1.15,
  });
  addText(s, 72, 244, 1136, 40, "那些地址能赢，是因为他们从赌博，变成了套利 / 信息 / 分散。", {
    fontSize: 19,
    color: INK2,
    alignment: "center",
  });

  addCard(s, 190, 330, 900, 250, { shadow: "shadow-sm" });
  addText(s, 230, 356, 830, 36, "留给讨论的三个问题", {
    fontSize: 20,
    bold: true,
    color: ACCENT,
  });
  addBullets(s, 230, 408, 830, [
    "你进预测市场，是为了赚钱，还是为了参与感？",
    "你能接受“我暂时没有优势”吗？如果不能，凭什么？",
    "结构、信息、纪律——你愿意为哪一条花半年？",
  ]);

  addText(s, 72, 622, 1136, 40, "谢谢 · 欢迎讨论", {
    fontSize: 20,
    bold: true,
    color: INK,
    alignment: "center",
  });
  chrome(s, "结束");
  notes(s, [
    "收尾一句话：预测市场不是赌博，但没有优势的人预测就是赌博。那些地址能赢，是因为他们从赌博变成了套利、信息、分散。",
    "最后留三个问题给大家讨论：你进来是为了赚钱还是参与感？你能接受自己暂时没有优势吗？结构、信息、纪律，你愿意为哪一条花半年？",
    "谢谢，欢迎讨论。",
  ]);
}

/* ------------------------------------------------------------------ */
/* export                                                               */
/* ------------------------------------------------------------------ */
const TMP = "/Users/ad/Documents/polymarket/.build/prediction_market_deck";
const FINAL_PPTX = "/Users/ad/Documents/polymarket/reports/预测市场到底是不是赌博-分享讲解.pptx";

await fs.mkdir(path.join(TMP, "render"), { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });

const items = p.slides.items;
for (let i = 0; i < items.length; i += 1) {
  const slide = items[i];
  const stem = `slide-${String(i + 1).padStart(2, "0")}`;
  const png = await p.export({ slide, format: "png", scale: 1 });
  await fs.writeFile(
    path.join(TMP, "render", `${stem}.png`),
    new Uint8Array(await png.arrayBuffer()),
  );
}

const montage = await p.export({ format: "webp", montage: true, scale: 1 });
await fs.writeFile(
  path.join(TMP, "render", "deck-montage.webp"),
  new Uint8Array(await montage.arrayBuffer()),
);

const pptx = await PresentationFile.exportPptx(p);
await pptx.save(FINAL_PPTX);
console.log("slides:", items.length);
console.log("pptx:", FINAL_PPTX);
