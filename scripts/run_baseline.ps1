$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $repo "src"
$env:PYTHONIOENCODING = "utf-8"

python -m ce_zlsma_xauusd `
  --csv (Join-Path $repo "data/XAUUSD_M5_202505010100_202604302255.csv") `
  --csv-cn-offset-hours 5 `
  --report-dir (Join-Path $repo "reports/baseline") `
  --replay-csv-name "trades_baseline.csv" 2>&1 |
  Tee-Object -FilePath (Join-Path $repo "reports/baseline/backtest_stdout.txt")
