# Baseline Artifacts / 基线生成物

This folder contains generated artifacts from the M5 baseline run described in `../../TEST_REPORT.md`.

本目录包含 `../../TEST_REPORT.md` 中 M5 基线回测生成的文件。

- `backtest_stdout.txt`: exact console output.
- `ce_zlsma_equity_drawdown.png`: equity and drawdown chart.
- `trades_baseline.csv`: closed-trade review CSV.

Exact command:

完整命令：

```powershell
python -m ce_zlsma_xauusd `
  --csv .\data\XAUUSD_M5_202505010100_202604302255.csv `
  --csv-cn-offset-hours 5 `
  --report-dir .\reports\baseline `
  --replay-csv-name trades_baseline.csv
```
