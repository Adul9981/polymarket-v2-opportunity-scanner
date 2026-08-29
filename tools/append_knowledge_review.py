#!/usr/bin/env python3
"""Append a completed grid trade review into the knowledge base and update the index."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path("/Users/ad/Documents/polymarket")
KNOWLEDGE = PROJECT_ROOT / "knowledge"
REVIEWS = KNOWLEDGE / "reviews"
INDEX = REVIEWS / "index.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Append a trade review to the knowledge base.")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--result", default="", help="最终结果简述，例如：T1 获胜，净赚 12 USDC")
    parser.add_argument("--lessons", default="", help="教训/复盘要点，多行用 ; 分隔")
    args = parser.parse_args()

    state_path = Path(args.state_file).expanduser().resolve()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    REVIEWS.mkdir(parents=True, exist_ok=True)

    review_path = _default_review_path(state)
    review_path.write_text(
        _render_review(state, state_path, args.result, args.lessons),
        encoding="utf-8",
    )
    _rebuild_index()
    print(f"复盘已写入：{review_path}")
    print(f"索引已更新：{INDEX}")
    return 0


def _default_review_path(state: dict[str, Any]) -> Path:
    slug = str(state.get("market_slug") or "market").replace("/", "-")
    side = str(state.get("side") or "side").replace("/", "-")
    date = datetime.now().strftime("%Y-%m-%d")
    name = re.sub(r"[^A-Za-z0-9_.-]+", "-", f"{slug}_{side}").strip("-").lower()
    return REVIEWS / f"{date}_{name}.md"


def _render_review(state: dict[str, Any], state_path: Path, result: str, lessons: str) -> str:
    layers = state.get("layers", [])
    sell_steps = state.get("sell_steps", [])
    buy_plan = "\n".join(
        f"- BUY {layer.get('shares')} @ {_fmt_price(layer.get('entry_price'))}，"
        f"预算 {layer.get('usdc')} USDC，订单 `{layer.get('order_id', '')}`"
        for layer in layers
    ) or "- 无"
    sell_plan = "\n".join(
        f"- SELL @ {_fmt_price(step.get('price'))}，成本 {step.get('sell_cost_basis_usd')} USDC，"
        f"订单 {', '.join(f'`{x}`' for x in step.get('order_ids', [])) or '未挂出'}"
        for step in sell_steps
    ) or "- 无"
    lesson_lines = "\n".join(f"- {line.strip()}" for line in lessons.split(";") if line.strip()) or "- 待补充"

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
最终结果：{result or "待补充"}
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

## 经验教训

{lesson_lines}
"""


def _rebuild_index() -> None:
    rows: list[list[str]] = []
    for review in sorted(REVIEWS.glob("*.md")):
        if review.name == "index.md":
            continue
        text = review.read_text(encoding="utf-8")
        title = _first_line(text).removeprefix("# ").strip()
        result = _extract_result(text)
        rows.append([review.stem[:10], title, result, f"[{review.name}]({review.name})"])

    if not rows:
        body = "暂无复盘。\n"
    else:
        lines = ["| 日期 | 交易 | 结果 | 文件 |", "| --- | --- | --- | --- |"]
        lines += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |" for r in rows]
        body = "\n".join(lines) + "\n"

    INDEX.write_text(f"# 复盘索引\n\n{body}", encoding="utf-8")


def _first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line
    return ""


def _extract_result(text: str) -> str:
    match = re.search(r"最终结果：(.+)", text)
    return match.group(1).strip() if match else ""


def _fmt_price(value: Any) -> str:
    try:
        return f"{round(float(value) * 100):.0f}c"
    except (TypeError, ValueError):
        return "-"


if __name__ == "__main__":
    raise SystemExit(main())
