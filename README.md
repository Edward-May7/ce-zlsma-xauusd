# CE + ZLSMA XAUUSD Strategy

Enterprise-ready open-source packaging for a CE + ZLSMA XAUUSD research strategy.

面向开源发布的 CE + ZLSMA XAUUSD 策略工程包，包含 Python 回测引擎、TradingView Pine 脚本、指定 M5 测试数据、自动化测试、基线报告和中英双语文档。

> Research software only. This project is not investment advice and does not guarantee live trading performance.
>
> 本项目仅用于研究和工程验证，不构成投资建议，也不保证实盘表现。

## What Is Included / 项目内容

| Area | Files |
| --- | --- |
| Core engine / 核心引擎 | `src/ce_zlsma_xauusd/engine.py` |
| Typed configuration / 类型化配置 | `src/ce_zlsma_xauusd/config.py` |
| Application runner / 应用层入口 | `src/ce_zlsma_xauusd/runner.py` |
| CLI / 命令行 | `python -m ce_zlsma_xauusd`, `ce-zlsma-xauusd` |
| TradingView / 图表端脚本 | `pine/TradingView_CE_ZLSMA_XAUUSD_Strategy.pine` |
| Baseline data / 基线数据 | `data/XAUUSD_M5_202505010100_202604302255.csv` |
| Usage guide / 使用指南 | `USAGE.md` |
| Test report / 测试报告 | `TEST_REPORT.md` |
| Architecture / 架构说明 | `docs/ARCHITECTURE.md` |
| GitHub publishing / GitHub 发布 | `GITHUB_PUBLISH.md` |
| CI / 持续集成 | `.github/workflows/ci.yml` |

## Quick Start / 快速开始

PowerShell:

```powershell
cd C:\Users\1\Desktop\量化回测\ce-zlsma-xauusd
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m unittest discover -s tests -v
.\scripts\run_baseline.ps1
```

Bash:

```bash
cd /path/to/ce-zlsma-xauusd
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m unittest discover -s tests -v
./scripts/run_baseline.sh
```

## Baseline Result / 基线结果

The included M5 CSV dataset is tested with MT5-style timezone-naive timestamps shifted by `+5` hours for Asia/Shanghai no-entry session checks.

内置 M5 CSV 按 MT5 风格无时区时间戳处理，并在禁开时段判断前加 `+5` 小时对齐 Asia/Shanghai。

| Metric / 指标 | Value / 数值 |
| --- | ---: |
| Dataset / 数据集 | `XAUUSD_M5_202505010100_202604302255.csv` |
| Bars / K 线数量 | 70,167 |
| Time range / 时间范围 | 2025-05-01 01:00:00 to 2026-04-30 22:55:00 |
| Initial cash / 初始资金 | 10,000.00 |
| Final equity / 期末权益 | 22,596.71 |
| Total return / 总收益率 | 125.97% |
| Max drawdown / 最大回撤 | 34.55% |
| Closed trades / 已平仓交易 | 1,540 |
| Win rate / 胜率 | 40.00% |
| Profit factor / 盈亏比 | 1.091 |

See `TEST_REPORT.md` for the complete bilingual report and `reports/baseline/` for generated artifacts.

完整中英双语测试报告见 `TEST_REPORT.md`，回测输出、权益回撤图和交易复盘 CSV 见 `reports/baseline/`。

## Python API / Python 调用

```python
from pathlib import Path

from ce_zlsma_xauusd import baseline_config, run_configured_backtest

config = baseline_config(Path("."))
run_configured_backtest(config)
```

## Open-Source Notes / 开源说明

- License / 许可证: MIT.
- The bundled broker-style CSV is included for reproducible research. Confirm redistribution rights before publishing a public fork.
- 内置券商风格 CSV 用于复现实验。公开发布或再分发前，请确认数据授权。
- Strategy behavior is kept close to the original single-file implementation. The packaging layer adds maintainability, tests, docs, and reproducible operations.
- 策略行为尽量保持原始单文件版本一致；工程层补充可维护结构、测试、文档和可复现运行流程。
