#!/bin/bash
set -euo pipefail

ROOT="/opt/danmu-intel/pattern-decision/live"
STATE="/opt/danmu-intel/pattern-decision/state"
SITE_JSON="/opt/danmu-intel/site_repo/intel/pattern_decision_live.json"
WEB_JSON="/var/www/danmu-pulse/intel/pattern_decision_live.json"
PYTHON="/opt/danmu-intel/.venv/bin/python"

cd "$ROOT"
mkdir -p "$STATE" runtime

"$PYTHON" tools/update_pattern_decision_live.py \
  --skip-html \
  --warm-clob-proxy \
  --base-data "$ROOT/reports/pattern_decision_data.json" \
  --watchlist "$ROOT/config/market_watchlist.json" \
  --price-cache "$ROOT/runtime/pattern_price_cache.json" \
  --live-json-out "$STATE/pattern_decision_live.json" \
  --max-events 64 \
  --pages 20 \
  --page-size 100 \
  --stake-days 3 \
  --max-stake-fixtures 64 \
  --workers 8

install_snapshot() {
  local dest="$1"
  local dir
  dir=$(dirname "$dest")
  mkdir -p "$dir"
  local tmp
  tmp=$(mktemp "$dir/.pattern_decision_live.XXXXXX")
  cp "$STATE/pattern_decision_live.json" "$tmp"
  chmod 644 "$tmp"
  mv -f "$tmp" "$dest"
}

install_snapshot "$SITE_JSON"
install_snapshot "$WEB_JSON"
