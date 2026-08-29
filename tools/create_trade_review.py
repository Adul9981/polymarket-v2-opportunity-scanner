#!/usr/bin/env python3
"""Create a standard post-trade review document from a grid state file."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path("/Users/ad/Documents/polymarket")
REPORTS = PROJECT_ROOT / "reports"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a grid trade review markdown file.")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    state_path = Path(args.state_file).expanduser().resolve()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    REPORTS.mkdir(parents=True, exist_ok=True)
    output = Path(args.output).expanduser().resolve() if args.output else _default_output(state)
    output.write_text(_render_review(state, state_path), encoding="utf-8")
    print(output)
    return 0


def _default_output(state: dict[str, Any]) -> Path:
    slug = str(state.get("market_slug") or "market").replace("/", "-")
    side = str(state.get("side") or "side").replace("/", "-")
    date = datetime.now().strftime("%Y-%m-%d")
    return REPORTS / f"trade_review_{date}_{slug}_{side}.md"


def _render_review(state: dict[str, Any], state_path: Path) -> str:
    layers = state.get("layers", [])
    sell_steps = state.get("sell_steps", [])
    buy_plan = "\n".join(
        f"- BUY {layer.get('shares')} @ {_fmt_price(layer.get('entry_price'))}，预算 {layer.get('usdc')} USDC，订单 `{layer.get('order_id', '')}`"
        for layer in layers
    ) or "- 无"
    sell_plan = "\n".join(
        f"- SELL @ {_fmt_price(step.get('price'))}，成本 {step.get('sell_cost_basis_usd')} USDC，订单 {', '.join(f'`{x}`' for x in step.get('order_ids', [])) or '未挂出'}"
        for step in sell_steps
    ) or "- 无"

    return f"""# 交易复盘：{state.get('market_title') or state.get('market_slug')}

日期：{datetime.now().strftime("%Y-%m-%d")}

## 基本信息

```text
市场：{state.get('market_title') or state.get('market_slug')}
策略：{state.get('strategy_name') or state.get('strategy_type')}
方向：{state.get('side')}
状态文件：{state_path}
```

## 计划

买入：

{buy_plan}

止盈：

{sell_plan}

彩票仓：

```text
保留成本：{state.get('lottery_cost_basis_usd', 0)} USDC
```

## 实际执行

```text
实际买入成交：
实际卖出成交：
当前剩余持仓：
最终结果：
```

## 判断复盘

```text
是否符合策略 A/B：
入场是否太早 / 太晚：
买入价格是否合理：
卖出价格是否合理：
彩票仓是否保留合理：
```

## 问题

```text
执行问题：
数据问题：
风控问题：
```

## 下一次调整

```text
价格区间：
档位金额：
止盈目标：
彩票仓比例：
是否纳入机会发现样本：
```
"""


def _fmt_price(value: Any) -> str:
    try:
        return f"{round(float(value) * 100):.0f}c"
    except (TypeError, ValueError):
        return "-"


if __name__ == "__main__":
    raise SystemExit(main())
