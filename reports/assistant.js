(() => {
  if (new URLSearchParams(location.search).get("embed") === "1") return;
  if (document.getElementById("di-assistant-root")) return;
  const FAQS = [{"topic": "start", "label": "第一次来应该先看哪里", "keywords": ["第一次", "怎么用", "入口", "开始", "先看", "导航", "网站", "使用"], "answer": {"title": "先看今日比赛，再进入赛前情报", "lead": "网站把赛程、队伍与选手数据、赛前市场共识和历史复盘放在同一套页面里。", "points": [["今日比赛", "查看今天已确认的场次、开赛时间和当前状态。"], ["赛前情报", "查看队伍近期表现、联赛排名、名单、伤停、地图或英雄池与市场数据。"], ["完整数据页", "每场可展开完整 JSON、CSV，并支持排序、打印和导出。"], ["历史情报库", "比赛结束后回看结果、验证结论和复盘闭环。"]], "footer": "推荐路径：今日比赛 → 对应赛前情报 → 完整数据页。"}}, {"topic": "match", "label": "比赛基本情况包含哪些内容", "keywords": ["比赛情况", "比赛数据", "基本信息", "队伍", "联赛", "排名", "近期", "h2h", "交手"], "answer": {"title": "先确认比赛对象、时间和赛制", "lead": "一场比赛的基础层包括比赛项目、联赛、对阵双方、开赛时间、赛制和当前状态。", "points": [["队伍层", "近期战绩、赛季排名、主客场或联盟记录、连胜连败和 H2H。"], ["赛事层", "联赛阶段、赛制、赛程、积分榜、射手榜或赛事队伍统计。"], ["电竞专项", "阵容名单、选手指标、地图池、英雄池、BP 与位置数据。"], ["足球与 NBA", "伤停、首发或近期首发、球队统计、球员统计和联赛排名。"]], "footer": "比赛页的价值不是堆字段，而是让你能在同一时间口径下做横向比较。"}}, {"topic": "status", "label": "比赛状态会自动更新吗", "keywords": ["状态", "更新时间", "自动更新", "进行中", "已结束", "未开始", "刷新"], "answer": {"title": "会更新，但事实状态优先于页面时间", "lead": "赛程与状态由自动发布流程持续刷新；页面同时参考官方状态、赛事源和已完成的小局/结算信号。", "points": [["状态口径", "未开始、进行中、已结束以结构和官方状态优先，弹幕不能单独决定比赛结果。"], ["跨时区", "页面按北京时间展示，底层事件时间可能使用 UTC。"], ["数据延迟", "外部源本身可能延迟；页面会保留抓取时间，不用旧数据伪装成实时。"], ["异常情况", "状态冲突或数据缺口会标注待确认，不会为了页面完整而硬写结论。"]], "footer": "如果你看到状态与官方比分离散，优先以官方结算和页面最新抓取时间为准。"}}, {"topic": "prematch", "label": "赛前情报里有什么", "keywords": ["赛前", "情报", "完整数据", "地图池", "英雄池", "伤停", "首发", "名单", "选手"], "answer": {"title": "赛前情报是一套结构化数据包", "lead": "它不是一张摘要卡，而是把一场比赛能用于分析的字段拆成可浏览、可导出的详情页。", "points": [["LoL / CS2 / Dota2", "队伍统计、全部选手数据、赛事名单、近期比赛、H2H、地图池或英雄池。"], ["足球 / NBA", "联赛排名、近期表现、伤停、名单或近期首发、球队与球员统计、H2H。"], ["市场层", "只展示赛前市场共识与去水概率，不把赔率当成确定胜率。"], ["缺口层", "没有样本、没有官方首发或 provider 未返回时会明确标缺口。"]], "footer": "详情页提供 JSON 与 CSV 下载，适合继续做自己的表和分析。"}}, {"topic": "lineup", "label": "阵容和首发是官方确认的吗", "keywords": ["阵容", "首发", "名单", "伤停", "替补", "换人", "official", "官方"], "answer": {"title": "必须区分赛事名单、近期首发和本场官方首发", "lead": "这三种数据的证明强度不同，不能混写。", "points": [["赛事名单", "只说明该队在该赛事登记过哪些人。"], ["近期首发", "说明过去比赛使用过什么阵容，不代表本场一定沿用。"], ["本场官方首发", "要等比赛方正式公布或官方阵容接口确认。"], ["伤停与缺阵", "有来源就展示，没有来源就标待确认，不根据旧名单猜。"]], "footer": "未确认时页面会明确写“首发待官方确认”。"}}, {"topic": "market", "label": "市场百分比是不是胜率", "keywords": ["百分比", "胜率", "赔率", "概率", "市场", "共识", "盘口", "热门"], "answer": {"title": "百分比是市场共识，不是真实概率", "lead": "页面会把赛前市场报价换算并去水，但它仍只是当时市场愿意交易出的价格。", "points": [["能说明什么", "市场参与者如何定价、哪一方更热门、价格是否快速变化。"], ["不能说明什么", "不能保证结果，也不能替代阵容、伤停、地图池和临场信息。"], ["强热门也会输", "高百分比不等于稳赢，低百分比也不等于没有机会。"], ["风险", "薄市场、临近开赛和突发消息都会让价格迅速失效。"]], "footer": "把市场共识当作一条证据，不要把它当作结论。"}}, {"topic": "hallucination", "label": "幻觉的核心识别方法", "keywords": ["幻觉", "识别", "真假", "假消息", "编造", "可靠", "可信", "验证", "错误"], "answer": {"title": "幻觉不是“看起来像真的”，而是表示与底层约束不一致", "lead": "识别情报幻觉，重点不是文字是否流畅，而是它有没有来源、时间、身份和可证伪条件。", "points": [["来源幻觉", "结论没有来源，或把单一转述写成事实。先问：证据在哪里？"], ["时间幻觉", "用旧阵容、旧排名或旧伤停冒充当前状态。先问：是什么时候的数据？"], ["身份幻觉", "队伍别名、选手昵称或位置被错误匹配。先问：对象是否唯一？"], ["因果幻觉", "观众情绪、盘口波动或单场样本被写成确定原因。先问：这只是相关还是因果？"], ["概率幻觉", "把市场价、模型值或历史命中率当成确定结果。先问：样本、误差和反例是什么？"]], "footer": "最有效的反幻觉动作：看来源、看时间、看缺口、找反例。"}}, {"topic": "evidence", "label": "事实、共识和推测怎么分开", "keywords": ["事实", "共识", "推测", "证据", "标签", "置信", "多源", "来源"], "answer": {"title": "把证据分层，结论才不会混在一起", "lead": "页面优先把事实、市场共识、观众信号和 AI 推断分开呈现。", "points": [["事实层", "官方赛程、比赛结果、阵容与可核验统计。"], ["市场层", "报价、去水概率、流动性和价格变化。"], ["共识层", "弹幕、评论或历史样本形成的群体倾向，只代表共识。"], ["推断层", "基于已有证据做出的可能解释，必须标为推测。"]], "footer": "没有证据的合理想象，不应出现在事实栏。"}}, {"topic": "missing", "label": "为什么有些比赛没有完整数据", "keywords": ["没有数据", "数据缺失", "缺口", "为空", "找不到", "样本不足", "provider"], "answer": {"title": "缺失不是把字段填满，而是明确告诉用户缺什么", "lead": "外部比赛组件并不总能提供完整字段，某些赛事阶段、球员或联赛本身就没有历史样本。", "points": [["名单可用但统计不足", "能看到人，但没有足够场次计算个人指标。"], ["赛事未返回", "外部结构源临时失败或尚未建立该场数据。"], ["本场未确认", "阵容、伤停或首发仍待官方信息。"], ["市场缺口", "比赛卡仍保留，但不展示伪造赔率。"]], "footer": "无样本不硬撑，是本站比“字段看起来很多”更重要的原则。"}}, {"topic": "personal", "label": "这个网站是谁做的", "keywords": ["个人", "作者", "站长", "是谁", "介绍", "coveym", "serene", "背景"], "answer": {"title": "coveym · 预测市场与赛事情报研究", "lead": "我长期记录预测市场、电竞赛事前情报、足球与 NBA 数据核验，以及交易与判断的复盘。", "points": [["关注方向", "数据可追溯、结论可证伪、过程可复盘。"], ["工具目标", "把分散的比赛信息整理成能快速比较和继续分析的结构化页面。"], ["内容原则", "不承诺收益，不把观众情绪当事实，不用旧数据冒充当前状态。"], ["公开入口", "YouTube @coveym，Telegram 个人号 @serene7mc，频道 @polymarket_ad。"]], "footer": "这个站点的核心不是“预测答案”，而是减少信息差和认知幻觉。"}}, {"topic": "contact", "label": "怎么联系或关注更新", "keywords": ["联系", "咨询", "客服", "tg", "telegram", "频道", "个人号", "合作", "关注"], "answer": {"title": "根据目的选择入口", "lead": "工具问题、合作和具体咨询走个人号；日常更新和公开观察走频道。", "points": [["个人咨询", "@serene7mc · 工具使用、数据问题、合作与具体交流。"], ["TG 频道", "@polymarket_ad · 网站更新、赛事观察和公开内容。"], ["网站内", "先看今日比赛、赛前情报和历史情报库，再针对具体比赛提问。"]], "footer": "涉及具体数据问题时，附上比赛名称、页面链接和截图会更快定位。", "cta": true}}, {"topic": "risk", "label": "会保证盈利吗", "keywords": ["保证", "赚钱", "盈利", "收益", "推荐", "下注", "稳赢", "风险"], "answer": {"title": "不保证收益，也不替你做交易决定", "lead": "本站提供比赛资料、结构化数据和识别幻觉的方法，不构成投资或投注建议。", "points": [["数据有误差", "来源延迟、样本不足和口径差异都可能影响判断。"], ["市场会变化", "阵容、伤停、临场信息和价格都可能快速改变。"], ["历史不等于未来", "过去命中不能保证下一次结果。"], ["先控制风险", "任何决策都应先确定能承受的最大损失。"]], "footer": "工具负责提供证据，最终决策和风险由使用者本人承担。"}}, {"topic": "mobile", "label": "手机和电脑都能用吗", "keywords": ["手机", "电脑", "移动端", "兼容", "平板", "浏览器", "页面"], "answer": {"title": "手机与桌面共用一套响应式页面", "lead": "导航、比赛列表、详情表格和问答助手会根据屏幕宽度重新排版。", "points": [["手机", "问答助手使用底部全宽面板；宽表格可横向滚动。"], ["桌面", "问答助手固定在右侧；详情页仍可排序、打印和导出。"], ["长内容", "FAQ 使用折叠项，默认只展开你正在看的问题。"], ["访问", "GitHub Pages 和服务器地址都可以打开同一套站点。"]], "footer": "如果手机上出现内容溢出，优先反馈具体页面与机型。"}}];
  const QUICK = ["第一次来应该先看哪里", "比赛基本情况包含哪些内容", "幻觉的核心识别方法", "阵容和首发是官方确认的吗", "市场百分比是不是胜率", "怎么联系或关注更新"];
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
    .replace(/[\s，。？！、,.!?;；:：()（）【】\[\]{}“”‘’"'`·\-_\/]/g, "");
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
      addText("你好，我是弹幕情报助手。\n\n我可以解释比赛数据、状态更新、阵容口径、市场概率与幻觉识别。这里只使用固定知识库回答，不自由编造。", "bot");
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
