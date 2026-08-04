# Polymarket Prediction Market Grid Research

This repository contains the V2 validation build for a prediction-market opportunity scanner.

## Current Status

```text
V2: pending validation
```

V2 is read-only. It scans public Polymarket markets, produces watchlist events, candidate opportunities, diagnostics, and reports. It does not place orders.

## Run V2 Validation

From the project root:

```bash
./runtime/run_task2_live_scan.command
```

Outputs:

```text
runtime/opportunity_candidates_live_task2.json
runtime/watchlist_events_live_task2.json
reports/opportunity_scan_live_task2_2026-08-04.md
```

Read the handoff note first:

```text
V2_VALIDATION_HANDOFF.md
```

## Safety

This V2 validation flow:

```text
does not read private keys
does not create orders
does not call live trade execution
only reads public market data
```

## Core Files

```text
tools/market_scanner.py
tools/summarize_scan_diagnostics.py
config/market_watchlist.json
config/discovery_patterns.json
schemas/opportunity_candidate.schema.json
PHENOMENON_STRATEGY_FRAMEWORK.md
PROJECT_PROGRESS.md
V2_VALIDATION_HANDOFF.md
```

