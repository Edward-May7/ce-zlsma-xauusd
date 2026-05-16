#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$repo/src"
export PYTHONIOENCODING=utf-8

python -m ce_zlsma_xauusd \
  --csv "$repo/data/XAUUSD_M5_202505010100_202604302255.csv" \
  --csv-cn-offset-hours 5 \
  --report-dir "$repo/reports/baseline" \
  --replay-csv-name "trades_baseline.csv" 2>&1 | tee "$repo/reports/baseline/backtest_stdout.txt"
