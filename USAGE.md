# Usage Guide / 使用指南

This guide explains how to install, test, run, and extend the CE + ZLSMA XAUUSD strategy package.

本文说明如何安装、测试、运行和扩展 CE + ZLSMA XAUUSD 策略工程包。

## 1. Overview / 概览

The project packages the original strategy into a maintainable open-source layout:

本项目把原始策略包装为可维护的开源工程结构：

- `src/ce_zlsma_xauusd/engine.py`: strategy engine, indicators, Backtrader strategy, reporting, and CLI.
- `src/ce_zlsma_xauusd/config.py`: immutable typed configuration objects.
- `src/ce_zlsma_xauusd/runner.py`: application-service wrapper for configured runs.
- `pine/`: TradingView Pine strategy for chart-side comparison.
- `data/`: reproducible M5 CSV dataset used by tests and the baseline report.
- `reports/baseline/`: generated baseline output.
- `tests/`: regression and smoke tests.

核心逻辑包括：

- Heikin Ashi 序列用于信号计算。
- Chandelier Exit 判断多空翻转。
- ZLSMA 过滤入场方向。
- 标准 OHLC 用于成交价和止损触发判断，对齐 TradingView `fill_orders_on_standard_ohlc=true`。
- 仓位按权益、初始止损距离、手数步长和保证金约束计算。

## 2. Installation / 安装

PowerShell:

```powershell
cd C:\Users\1\Desktop\量化回测\ce-zlsma-xauusd
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Bash:

```bash
cd /path/to/ce-zlsma-xauusd
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Python 3.10 or newer is required.

需要 Python 3.10 或更高版本。

## 3. Run Tests / 运行测试

```powershell
python -m unittest discover -s tests -v
```

The tests validate CSV loading, schema normalization, indicator construction, synthetic offline data, and the packaged baseline configuration.

测试会验证 CSV 读取、字段规范化、指标构建、离线合成数据路径，以及打包后的基线配置。

## 4. Run The Baseline / 运行基线回测

PowerShell:

```powershell
.\scripts\run_baseline.ps1
```

Bash:

```bash
./scripts/run_baseline.sh
```

Equivalent explicit command:

等价完整命令：

```powershell
python -m ce_zlsma_xauusd `
  --csv .\data\XAUUSD_M5_202505010100_202604302255.csv `
  --csv-cn-offset-hours 5 `
  --report-dir .\reports\baseline `
  --replay-csv-name trades_baseline.csv
```

The helper scripts also save console output to `reports/baseline/backtest_stdout.txt`.

脚本会同时把控制台输出保存到 `reports/baseline/backtest_stdout.txt`。

## 5. Python API / Python API

Use the typed configuration layer when integrating this project into notebooks, pipelines, or internal research services.

如需集成到 Notebook、流水线或内部研究服务，建议使用类型化配置层。

```python
from pathlib import Path

from ce_zlsma_xauusd import baseline_config, run_configured_backtest

config = baseline_config(Path("."))
run_configured_backtest(config)
```

For custom jobs:

自定义任务示例：

```python
from pathlib import Path

from ce_zlsma_xauusd import BacktestConfig, DataConfig, OutputConfig, RiskConfig, run_configured_backtest

config = BacktestConfig(
    data=DataConfig(
        csv_path=Path("data/XAUUSD_M5_202505010100_202604302255.csv"),
        csv_cn_offset_hours=5,
    ),
    risk=RiskConfig(cash=10_000, risk_per_trade=0.02, max_lots=0),
    output=OutputConfig(report_dir=Path("reports/custom")),
)
run_configured_backtest(config)
```

## 6. Data Format / 数据格式

The baseline dataset is an MT5-style tab-separated CSV:

基线数据是 MT5 风格制表符分隔 CSV：

```text
<DATE>      <TIME>      <OPEN>  <HIGH>  <LOW>   <CLOSE> <TICKVOL> <VOL> <SPREAD>
2025.05.12  01:00:00    3286.10 3317.43 3278.94 3281.86 1998      0     6
```

Supported input columns:

支持的输入列：

- `date` + `time`, or `datetime`, or a single compact `time` column.
- `open`, `high`, `low`, `close`.
- `tickvol`, `volume`, or `vol`.
- `spread`, optional.

Timestamp guidance:

时间戳建议：

- Use `--csv-cn-offset-hours 5` when the broker server timestamp needs a fixed `+5h` alignment before Shanghai session checks.
- Use `--csv-cn-offset-hours 0` if the CSV timestamp is already Asia/Shanghai wall-clock time.
- Use `--csv-assume-timezone IANA` only when the naive timestamp should be localized to a real timezone before conversion.

## 7. Key CLI Parameters / 主要命令行参数

| Parameter / 参数 | Default / 默认值 | Meaning / 含义 |
| --- | ---: | --- |
| `--csv` | none | Local OHLCV CSV path. 本地 OHLCV CSV 路径。 |
| `--demo` | false | Use synthetic offline data. 使用内置合成数据自检。 |
| `--cash` | `10000` | Initial capital. 初始资金。 |
| `--risk-pct` | `2.0` | Target risk per trade as equity percent. 单笔目标风险占权益百分比。 |
| `--csv-cn-offset-hours` | `0` | Fixed hour offset before Shanghai no-entry checks. 禁开时段判断前的固定小时偏移。 |
| `--disable-no-entry-sessions` | false | Disable the two no-entry windows. 关闭两段禁开时段。 |
| `--max-lots` | `0` | Max lots per new entry; `0` means unlimited. 单笔最大手数，`0` 表示不限。 |
| `--partial-tp-r` | `1.5` | Partial take-profit trigger in initial-risk multiples. 分批止盈触发倍数。 |
| `--partial-tp-pct` | `50` | Partial close percentage. 分批平仓比例。 |
| `--report-dir` | `.` | Output folder for reports and charts. 报告和图表输出目录。 |
| `--no-charts` | false | Disable PNG chart generation. 不生成 PNG 图。 |
| `--no-replay-csv` | false | Disable trade-review CSV generation. 不生成交易复盘 CSV。 |

Run `python -m ce_zlsma_xauusd --help` for the full list.

完整参数请运行 `python -m ce_zlsma_xauusd --help`。

## 8. Outputs / 输出文件

A baseline run writes:

基线运行会生成：

- `reports/baseline/backtest_stdout.txt`: full console output.
- `reports/baseline/ce_zlsma_equity_drawdown.png`: equity and drawdown chart.
- `reports/baseline/trades_baseline.csv`: closed-trade review table.

## 9. TradingView / TradingView 使用

Open `pine/TradingView_CE_ZLSMA_XAUUSD_Strategy.pine` in the TradingView Pine Editor, add it to an XAUUSD chart, and align the chart timeframe with the data you want to compare. The packaged Python baseline uses M5 data.

在 TradingView Pine Editor 打开 `pine/TradingView_CE_ZLSMA_XAUUSD_Strategy.pine`，添加到 XAUUSD 图表，并把图表周期与需要对比的数据周期对齐。本工程的 Python 基线使用 M5 数据。

## 10. Reproducibility / 复现建议

Record these items with every report:

每份报告建议保留以下信息：

- Exact command / 完整命令。
- Dataset filename and SHA256 / 数据文件名和 SHA256。
- Python version and dependency versions / Python 与依赖版本。
- Timezone assumption / 时间戳假设。
- Strategy parameters / 策略参数。
- Generated artifacts / 生成物。

## 11. Disclaimer / 免责声明

This project is research software. Historical backtests are sensitive to data quality, broker timestamps, execution assumptions, spread, slippage, and market regime. Validate independently before any live use.

本项目是研究软件。历史回测会受到数据质量、券商时间戳、成交假设、点差、滑点和市场状态影响。任何实盘使用前都必须独立验证。
