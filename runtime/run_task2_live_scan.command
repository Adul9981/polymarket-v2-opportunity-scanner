#!/usr/bin/env zsh
set -euo pipefail

# 跨平台定位项目根目录（脚本在 runtime/ 下，.. 即项目根），不写死用户名/路径
cd "$(dirname "$0")/.."

echo "Running Task 2 live scan..."
python3 tools/market_scanner.py \
  --live \
  --live-limit 100 \
  --live-pages 8 \
  --skip-book \
  --output-json runtime/opportunity_candidates_live_task2.json \
  --output-events runtime/watchlist_events_live_task2.json \
  --output-report reports/opportunity_scan_live_task2_2026-08-04.md

echo ""
python3 tools/summarize_scan_diagnostics.py \
  --candidates runtime/opportunity_candidates_live_task2.json \
  --events runtime/watchlist_events_live_task2.json

echo ""
echo "Report: $(pwd)/reports/opportunity_scan_live_task2_2026-08-04.md"
echo "Candidates: $(pwd)/runtime/opportunity_candidates_live_task2.json"
echo "Events: $(pwd)/runtime/watchlist_events_live_task2.json"
