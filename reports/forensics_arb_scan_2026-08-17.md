# S-F1 扫描 2026-08-17（48h 内结算市场）

- 事件数 12，负风险组 12，粗筛候选 5
- 阈值：|Σp−1|>0.02；摩擦 0.02；安全垫 0.01；目标 $100

| 状态 | 组 | Σp | 侧 | 腿 | 结算剩余h | ask成本$ | 净估$ | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fail | Highest temperature in Milan on Augu | 1.0715 | NO | 11 | 0.1 | 40.319 | - | best_subset_k=4/11 |
| fail | Highest temperature in Amsterdam on  | 1.0565 | NO | 11 | 0.1 | 39.3064 | - | best_subset_k=4/11 |
| fail | Highest temperature in NYC on August | 1.0505 | NO | 11 | 0.1 | 39.552 | - | best_subset_k=4/11 |
| fail | Highest temperature in Madrid on Aug | 1.0355 | NO | 11 | 0.1 | 38.5688 | - | best_subset_k=4/11 |
| depth_insufficient | Lowest temperature in Hong Kong on A | 1.0205 | NO | 11 | 0.1 | 25.728 | - | legs_available=3/11 (need 4) |

纪律：标记价只做粗筛；pass 仅表示可成交成本达标，真实执行需走成熟度与风控。
