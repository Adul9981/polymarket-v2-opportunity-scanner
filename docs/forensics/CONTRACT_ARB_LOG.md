# 合约规则套利研究日志

最后更新：2026-08-15（会话启动包清单第 1~4 项完成）

本日志记录"合约规则套利研究窗口"的只读研究成果：合约地址核对、Σp 粗筛/精筛、
源码规则边界、疑似缺陷清单。纪律：只做市场侧规则套利观察与白帽上报，不下单、不碰私钥。

## 1. 合约地址核对（2026-08-15，链上 eth_getCode 实证）

| 合约 | 地址 | 字节码 | 备注 |
| --- | --- | --- | --- |
| CTF Exchange V2（撮合+托管） | 0xE111180000d2663C0091e4f400237545B87B996B | 存在 | brief 与官方文档一致 |
| Neg Risk CTF Exchange | 0xe2222d279d744050d28e00520010520000310F59 | 存在（21KB） | **brief 清单遗漏**；官方文档 V2 负风险交易所 |
| Neg Risk Adapter（Convert 引擎） | 0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296 | 存在 | 官方标"CLOB v1 deprecated"，但链上实证是 V2 适配器实际调用的 NEG_RISK_ADAPTER |
| NegRiskCtfCollateralAdapter | 0xadA2005600Dec949baf300f4C6120000bDB6eAab | 存在 | brief 误标为"NegRiskAdapter"；官方名称是抵押品适配器 |
| 条件代币 CTF | 0x4D97DCd97eC945f40cF65F87097ACe5EA0476045 | 存在 | — |
| USDC.e | 0x2791bca1f2de4661ed88a30c99a7a9449aa84174 | 存在 | V1 抵押品 |
| pUSD | 0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB | 存在（EIP-1167 代理） | V2 内部抵押品 |
| 负风险抵押凭证 wcol | 0x3a3bd7bb9528e159577f7c2e685cc81a765002e2 | 存在 | — |
| V2 执行实现 / NegRiskModule 实现 | 0x7345C684... / 0xA61e7ca3... | 存在 | 官方文档补充核对 |

链上调用实证（publicnode RPC）：

```text
NegRiskCtfCollateralAdapter(0xada2).NEG_RISK_ADAPTER() = 0xd91e80cf...（Convert 引擎）
getFeeBips：NFL/NBA/MLB/EPL/UCL 组全部 = 0 bps（2026-08-15）
```

结论：7 个启动清单地址全部有效；补充 2 个官方文档地址；修正 brief 中
"0xada2 = NegRiskAdapter" 的名称标注（实际为 NegRiskCtfCollateralAdapter，
Convert 逻辑在 0xd91e 的 NegRiskAdapter）。

## 2. Σp 粗筛复跑（2026-08-15 07:00Z 对比 06:52Z 快照）

```text
37 个白名单组复跑：20 组命中（|Σp−1|>2%）
绝大部分组 8 分钟内无变化；漂移较大的：
  Maxx Crosby 去向  1.097 -> 1.0835（−1.35pp）
  Largest IPO      1.266 -> 1.2550（−1.10pp）
  Fed 年末利率     1.0135 -> 1.0075（−0.60pp）
  Ballon d'Or      1.0250 -> 1.0285（+0.35pp）
```

新过滤规则（只统计 lastTradePrice+bestBid 双非空腿）后 3 个组被剔除
（IPO/加州州长/洛杉矶市长——腿级无真实双边报价）。

## 3. 订单簿二级精筛（2026-08-15 07:01~07:14Z，X=1）

费率模型修正（2026-08-15 09:52）：早期使用"固定 2% 摩擦"过于保守，已改为
Polymarket 官方手续费公式 fee = C × feeRate × p × (1−p)（天气/体育 0.05、
政治/金融 0.04、地缘 0），gas 默认 $0.05/轮。真实费用约占 NO 名义金额
0.5%~0.6%。改用真实费率后 NFL 冠军盘净利从 −0.29/份收窄至 −0.073/份
（X=1，仍为负）；马德里天气 09:52 实测 NO 成本 6.07（毛边 −1.1%），
各档 X 净回报 −2.5%~−4.2%，仍不成立。

| 组 | mark Σp | 标记边 | 可执行边 | NO 可成交腿 | 判定 |
| --- | --- | --- | --- | --- | --- |
| NFL 2027 冠军 | 1.0555 | +0.0555/份 | +0.0260/份 | 32/32 | fail（净 −0.29/份） |
| NBA 2027 冠军 | 1.0480 | +0.0480/份 | +0.0150/份 | 30/30 | fail（净 −0.28/份） |
| MLB 2026 冠军 | 1.0300 | +0.0300/份 | 不可成交 | 23/30（7 腿 NO 空盘口） | fail |
| Ballon d'Or 2026 | 1.0200 | +0.0200/份 | +0.0080/份 | 14/14 | fail（净 −0.13/份） |
| 共和党 2028 提名 | 0.9295 | −0.0705/份 | −0.0920/份（YES 侧） | 41/41 | pass_long_dated（YES 净 +0.035/份，但无 field 腿 + 2028 年结算，属残差概率/久期，非即时套利） |

核心结论（与 e46m3 拆解一致）：

```text
1. 冠军未来盘标记边严重高估：NFL 标记边 5.5 分，订单簿可执行边只剩 2.6 分
   （约 47%），扣摩擦后为负——"未来盘低价值"判断成立。
2. 当前时点无活跃短窗口机会：分页扫描 2000+ 事件，243 个关键词负风险事件中
   仅 4 个有真实双边报价，0 个流动性 ≥$25（死盘全部排除）。
3. e46m3 型高效机会集中在比赛/天气窗口（比分组 Σp 1.02~1.07、天气组 1.04~1.07），
   扫描器已具备在窗口出现时抓取的能力（--discover + 精筛）。
```

## 4. 源码通读结论（ctf-exchange-v2 + neg-risk-ctf-adapter，只读）

### 4.1 撮合与结算（exchange/mixins/Trading.sol）

```text
- maker 订单批量结算：先汇总 MINT/MERGE 总量，一次 CTF mint/merge，再逐单分发
  （Phase1 准备 -> Phase2 批量链上操作 -> Phase3 分发）。
- SELL 手续费从 proceeds 扣（require fee<=takingAmount 防下溢）；BUY 从 maker 直接收。
- POL-EX-4 复核：calculateTakingAmount = makingAmount*takerAmount/makerAmount，
  0.8.34 编译（checked 算术）下溢出直接 revert，不产生错误结算金额；
  要溢出需 ~1e77 量级，现实不可达 => 维持 Informational，无利用路径。
- 未发现撮合/结算路径的规则套利或白帽可报缺陷（结论分级：源码阅读）。
```

### 4.2 Convert/Merge/Split/Redeem 边界（src/NegRiskAdapter.sol）

```text
Convert 公式（实测源码）：
  feeAmount = X * feeBips / 10000；amountOut = X - feeAmount
  k=|S| 条 NO 交出 -> 现金 (k-1)*amountOut（k>1 时）+ 补集 (n-k) 条 YES*amountOut
  V2 适配器再把现金包成 pUSD。feeBips 按市场配置，当前主流组 = 0。
边界/状态机：
  - questionCount<=1 -> revert NoConvertiblePositions（n=1 组不可 Convert）
  - _indexSet=0 或越界 -> revert；X=0 直接 return（无粉尘卡死）
  - 现金乘数 (k-1)：单腿 Convert（k=1）只给补集 YES、无现金，与公式一致
  - 全部舍入向下取整，无向上取整套利面；checked 算术防溢出
  - NO 一律转入 NO_TOKEN_BURN_ADDRESS（"must never be redeemed"），
    结算中窗口 Convert 未做结算状态检查——由调用方自行判断（无漏洞）
Merge：交全套 YES+NO -> 1:1 返回 wcol；Split：1 抵押 -> 全套 YES+NO（无舍入面）
Redeem：按结算结果兑付，赢家 YES 1:1
结论：Convert 公式本身公平（利润来自 Σp 定价错误，与知识库结论一致）；
  feeBips 机制是 V2 新增规则边界，扫描器已参数化。
```

### 4.3 疑似缺陷清单（截至 2026-08-15）

```text
无新发现可报级缺陷。维护中的候选线索：
  [观察] POL-EX-4（calculateTakingAmount 溢出）——0.8.x checked 算术下仅 DoS 面，
         维持 Informational，无上报价值。
  [观察] Convert feeBips 若被市场启用会改变单边收益结构——不是缺陷，是参数。
  [待查] pUSD 包装/解包路径（CollateralToken.wrap/unwrap）未逐行复核，
         列入下一轮（P1）。
```

## 5. 结论与下一步

```text
已完成启动清单 1~4：地址核对、粗筛复跑、冠军盘二级精筛、源码通读。
当前无即时可执行的高效机会（冠军盘边负、短窗口盘未开）；扫描器具备窗口抓取能力。
下一步（P1）：
  1. 扫描器接入定时循环（每 15-30 分钟粗筛 + 命中即精筛），连续 3 天快照，
     统计错价频率/幅度/可成交性分布（回测模块）。
  2. 对首个真实比分/天气窗口完整跑通"粗筛->精筛->候选记录"闭环。
  3. 复核 pUSD wrap/unwrap 与 AutoRedeemer 路径（P1）。
  4. 候选需走项目成熟度与风控后才能进入执行开发（S-F1 仍为 L1）。
```

## 6. Σp>1.05 专项筛选构建（2026-08-15 09:19Z）

按需求"只筛所有 YES 相加 > 1.05 的完整集场景"，扫描器新增单边模式：

```text
tools/forensics_sigma_scan.py --snapshot <快照> --direction gt --threshold 0.05
tools/forensics_sigma_scan.py --discover --direction gt --threshold 0.05   # 发现模式
产出：reports/sigma_p_gt105_candidates_2026-08-15.json（79 个候选）
```

结果（09:12~09:19Z）：

```text
白名单命中 2 组：NFL 2027 冠军（Σp=1.0555）、Maxx Crosby 去向（1.0510）
全量发现命中 79 组，含今日结算的天气盘：
  马德里最高温（Σp=1.0745，7 腿，今日结算）
  巴黎最高温（1.0610，7 腿，今日结算）
  阿姆斯特丹最高温（1.0655，7 腿，今日结算）
  以及 MLB 本垒打王（1.1530）、NFL 2026 MVP（1.0795）、MLS 金靴（2.315）等
```

二级订单簿验证（15 组）——**全部不达标**：

```text
规律极一致：gamma 标记价系统性高于订单簿可成交价。
天气盘：马德里可执行边 +0.0012/份（标记 +0.075）、巴黎 −0.021、阿姆斯特丹 −0.039
大盘：MLB 本垒打王 −0.114、NFL MVP 0.0000、阿拉斯加 −0.029、MLS 金靴 −0.302、
      MLB 二垒打王 −0.687、民主党副总统提名 −0.040
盘口缺口：MLB 冠军 7 腿、辛克菲尔德杯 3 腿无 NO 盘口 -> 整套不可成交
唯一非 fail：共和党 2028 提名 YES 侧 pass_long_dated（久期/残差，非即时套利）
```

结论：Σp>1.05 的标记筛选可稳定产出候选，但当前市场订单簿层面没有可成交的
完整集套利；真实窗口（e46m3 型）出现在盘中比分/天气盘错价的短暂窗口。
下一步：把 --direction gt 接入定时循环（15-30 分钟粗筛 + 命中即精筛），
连续采样评估"标记边 >5% 且订单簿边 >0"的窗口出现频率。

## 7. 三天 0 机会的交叉验证与根因（2026-08-18）

外部扫描器（朋友部署，daily cron）连续运行 8-16~8-18：粗筛 36524 条/244 组、
精筛 908 条、pass=0。按项目防错规则"先怀疑工具"，做了三层核实：

```text
1. 同组交叉验证（08-18 我们的工具重扫日报同批组）：
   mls-chi-vwh 比分盘 NO 成本 14.69 vs 理论 14（毛边 −4.71%）fail；
   precipitation-seattle 无真实成交腿（死盘）；Busan 今日天气盘 NO 盘口
   至少一腿为空（infeasible）；NFL 抄截榜盘口 0 深度。
   => 吃单口径下"无机会"成立。
2. 历史窗口回放（tools/forensics_arb_backtester.py）：
   吉达 8/12 窗口 31 个 Σp≥1.03 时点，公平价+滑点回放净利全部 −0.53~−0.65%；
   比利亚雷亚尔比分盘 −1.29。注意：该回测用合成成交价（(1−标记)×(1+滑点)），
   非真实 ask 历史，结论偏保守但方向一致。
3. 朋友日报本身的三处工具问题：
   a. 部分组 Σp 高达 2.9 仍在精筛 -> 部署版本缺 sanity(1.3) 与"真实成交腿"过滤，
      粗筛命中率 71% 是死盘/默认价噪音；
   b. "ask Σp" 17.456/31.138 是退化盘口 0.99 墙求和，非可成交口径；
   c. 摩擦 2%+安全垫 1% 过严（真实费用 ≈ 名义金额 0.5%~0.6% + gas $0.05），
      会漏掉 0.7%~1.5% 的真实窗口；
   d. 10 分钟轮询 + 扫描池缺盘中比分盘，可能错过 e46m3 型分钟级窗口。
环境问题（本机）：Python urllib 默认 SSL 上下文被自签名证书拦截（curl 正常），
扫描器可能静默漏抓；tools/forensics_sigma_scan.py 已加证书降级容错。
```

结论：S-F1 吃单模式在近期市场结构下无可成交机会（三天交叉验证一致）；
e46m3 的利润大概率来自做市/返佣与极小单高频，吃单价差路径尚未被任何
回测/扫描复现为正。下一步：扫描器对齐仓库最新口径 + 回测改用真实 ask
历史 + 盘中 1-5 分钟粒度盯盘。
