#!/bin/zsh
set -euo pipefail

cd /Users/ad/Documents/polymarket

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
echo "Report: /Users/ad/Documents/polymarket/reports/opportunity_scan_live_task2_2026-08-04.md"
echo "Candidates: /Users/ad/Documents/polymarket/runtime/opportunity_candidates_live_task2.json"
echo "Events: /Users/ad/Documents/polymarket/runtime/watchlist_events_live_task2.json"
