# Baseline Test Report / 基线测试报告

Test date / 测试日期: 2026-05-16  
Dataset / 数据集: `data/XAUUSD_M5_202505010100_202604302255.csv`

## Chinese / 中文

### 1. 测试目标

验证 CE + ZLSMA XAUUSD 策略在指定 M5 CSV 数据集上的可运行性、数据读取稳定性、指标构建、回测输出、图表生成和交易复盘生成能力。

### 2. 测试环境

| 项目 | 值 |
| --- | --- |
| 操作系统 | Windows |
| Python | 3.13.2 |
| 回测框架 | Backtrader |
| 数据处理 | pandas, numpy |
| 图表输出 | matplotlib |
| 测试框架 | Python `unittest` |

### 3. 数据集

| 项目 | 值 |
| --- | --- |
| 品种 | XAUUSD |
| 周期 | 5 分钟 |
| 格式 | MT5 风格制表符分隔 CSV |
| K 线数量 | 70,167 |
| 时间范围 | 2025-05-01 01:00:00 至 2026-04-30 22:55:00 |
| 标准 K Close 区间 | 3125.40 至 5589.10 |
| SHA256 | `2F00B71D9F8E6AE783E4AEA55E61FE323CD26DF6B667BD323A063492E368E0DC` |
| 禁开时段偏移 | `--csv-cn-offset-hours 5` |
| 可新开仓 K 线数量 | 45,220 |

说明：本次基线假设 CSV 时间戳为无时区 MT5 服务器时间，并在禁开时段判断前加 `5` 小时，以对齐 Asia/Shanghai。如果你的数据本身已经是上海时间，应改用 `--csv-cn-offset-hours 0` 并重新生成报告。

### 4. 精确命令

```powershell
python -m ce_zlsma_xauusd `
  --csv .\data\XAUUSD_M5_202505010100_202604302255.csv `
  --csv-cn-offset-hours 5 `
  --report-dir .\reports\baseline `
  --replay-csv-name trades_baseline.csv
```

### 5. 策略配置摘要

| 参数 | 值 |
| --- | ---: |
| 初始资金 | 10,000.00 |
| 单笔目标风险 | 2.00% |
| CE ATR 周期 | 1 |
| CE ATR 倍数 | 2.0 |
| CE 极值来源 | close |
| ZLSMA 公式 | veryfid |
| ZLSMA 长度 | 50 |
| ZLSMA linreg offset | 0 |
| HA 首根 open | `(O + C) / 2` |
| 初始止损回看 | 8 根 |
| 分批止盈 | 1.5R 平 50% |
| 手数步长 | 0.01 |
| 每标准手盎司 | 100 |

### 6. 回测结果

| 指标 | 结果 |
| --- | ---: |
| 期末权益 | 22,596.71 |
| 总盈亏 | 12,596.71 |
| 总收益率 | 125.97% |
| 年化收益率 | 126.14% |
| 最大回撤 | 34.55% |
| 夏普比率，近似 | 1.527 |
| 已平仓交易数 | 1,540 |
| 胜率 | 40.00% |
| 盈亏比 | 1.091 |
| 盈利总额 | 149,834.29 |
| 亏损总额 | 137,274.93 |
| 平均持仓时间 | 61.7 分钟 |
| 最大连续盈利 | 6 笔 |
| 最大连续亏损 | 12 笔 |
| 开仓风险占比，平均 | 1.909% |
| 开仓风险占比，最大 | 2.223% |

方向表现：

| 方向 | 胜率 | 笔数 |
| --- | ---: | ---: |
| 多单 | 42.47% | 313 / 737 |
| 空单 | 37.73% | 303 / 803 |

ATR14 三分位盈亏：

| 波动分组 | 盈亏 |
| --- | ---: |
| 低波动 | -74.21 |
| 中波动 | 13,756.55 |
| 高波动 | -1,122.98 |
| N/A | 0.00 |

按平仓时段统计：

| 时段 | 盈亏 |
| --- | ---: |
| 欧洲时段 | 14,212.71 |
| 纽约时段 | -12,804.83 |
| 欧纽重叠 | 2,822.53 |
| 其他时段 | 13,974.01 |

### 7. 生成物

- `reports/baseline/backtest_stdout.txt`
- `reports/baseline/ce_zlsma_equity_drawdown.png`
- `reports/baseline/trades_baseline.csv`

### 8. 自动化测试

```text
Ran 4 tests
OK
```

测试覆盖：

- M5 CSV 读取、字段规范化、行数和时间范围。
- HA、CE、ZLSMA、ATR 等核心字段生成。
- 离线合成数据路径。
- 类型化基线配置指向仓库内 M5 数据。
- Python 默认 `PARTIAL_TP_R` 与 Pine 默认 `1.5` 对齐。

### 9. 结论

本次 M5 基线回测可稳定完成，并成功生成交易复盘 CSV、权益回撤图和完整控制台输出。策略在该样本上取得 125.97% 总收益率，但最大回撤达到 34.55%，风险波动仍然较高。该结果适合作为工程基线和开源复现参考，不应直接视为实盘收益预期。

### 10. 局限性

- 本次仅使用单一历史样本，未进行样本外、walk-forward 或蒙特卡洛扰动。
- CSV 数据质量、时间戳假设和券商报价差异会显著影响结果。
- 未额外叠加真实交易滑点、手续费和流动性冲击。
- 历史结果不保证未来表现。

## English

### 1. Objective

Validate that the CE + ZLSMA XAUUSD strategy can load the specified M5 CSV dataset, build indicators, run a full backtest, and generate reproducible reporting artifacts.

### 2. Environment

| Item | Value |
| --- | --- |
| Operating system | Windows |
| Python | 3.13.2 |
| Backtest framework | Backtrader |
| Data stack | pandas, numpy |
| Charting | matplotlib |
| Test framework | Python `unittest` |

### 3. Dataset

| Item | Value |
| --- | --- |
| Symbol | XAUUSD |
| Timeframe | 5 minutes |
| Format | MT5-style tab-separated CSV |
| Bars | 70,167 |
| Time range | 2025-05-01 01:00:00 to 2026-04-30 22:55:00 |
| Standard close range | 3125.40 to 5589.10 |
| SHA256 | `2F00B71D9F8E6AE783E4AEA55E61FE323CD26DF6B667BD323A063492E368E0DC` |
| No-entry session offset | `--csv-cn-offset-hours 5` |
| Bars eligible for new entries | 45,220 |

This baseline treats CSV timestamps as timezone-naive MT5 server timestamps and adds `5` hours before Asia/Shanghai no-entry session checks. If your CSV is already in Shanghai time, rerun with `--csv-cn-offset-hours 0`.

### 4. Exact Command

```powershell
python -m ce_zlsma_xauusd `
  --csv .\data\XAUUSD_M5_202505010100_202604302255.csv `
  --csv-cn-offset-hours 5 `
  --report-dir .\reports\baseline `
  --replay-csv-name trades_baseline.csv
```

### 5. Strategy Configuration

| Parameter | Value |
| --- | ---: |
| Initial cash | 10,000.00 |
| Risk per trade | 2.00% |
| CE ATR period | 1 |
| CE ATR multiplier | 2.0 |
| CE extreme source | close |
| ZLSMA formula | veryfid |
| ZLSMA length | 50 |
| ZLSMA linreg offset | 0 |
| HA first open | `(O + C) / 2` |
| Initial stop lookback | 8 bars |
| Partial take profit | 1.5R closes 50% |
| Lot step | 0.01 |
| Ounces per full lot | 100 |

### 6. Backtest Results

| Metric | Result |
| --- | ---: |
| Final equity | 22,596.71 |
| Net profit | 12,596.71 |
| Total return | 125.97% |
| Annualized return | 126.14% |
| Max drawdown | 34.55% |
| Approximate Sharpe | 1.527 |
| Closed trades | 1,540 |
| Win rate | 40.00% |
| Profit factor | 1.091 |
| Gross profit | 149,834.29 |
| Gross loss | 137,274.93 |
| Average holding time | 61.7 minutes |
| Max winning streak | 6 trades |
| Max losing streak | 12 trades |
| Average open risk | 1.909% |
| Max open risk | 2.223% |

Direction breakdown:

| Direction | Win rate | Trades |
| --- | ---: | ---: |
| Long | 42.47% | 313 / 737 |
| Short | 37.73% | 303 / 803 |

ATR14 profit and loss buckets:

| Volatility bucket | PnL |
| --- | ---: |
| Low volatility | -74.21 |
| Medium volatility | 13,756.55 |
| High volatility | -1,122.98 |
| N/A | 0.00 |

Session profit and loss:

| Session | PnL |
| --- | ---: |
| Europe | 14,212.71 |
| New York | -12,804.83 |
| Europe/New York overlap | 2,822.53 |
| Other | 13,974.01 |

### 7. Generated Artifacts

- `reports/baseline/backtest_stdout.txt`
- `reports/baseline/ce_zlsma_equity_drawdown.png`
- `reports/baseline/trades_baseline.csv`

### 8. Automated Tests

```text
Ran 4 tests
OK
```

Coverage:

- M5 CSV loading, schema normalization, row count, and time range.
- Core HA, CE, ZLSMA, and ATR field generation.
- Offline synthetic-data smoke path.
- Typed baseline configuration pointing to the packaged M5 dataset.
- Python default `PARTIAL_TP_R` aligned with Pine default `1.5`.

### 9. Conclusion

The M5 baseline backtest completes reliably and generates a trade review CSV, equity/drawdown chart, and full console output. The sample produces a 125.97% total return with a 34.55% maximum drawdown, so the result is useful as an engineering baseline but should not be interpreted as a live performance expectation.

### 10. Limitations

- Only one historical sample was tested; no out-of-sample, walk-forward, or Monte Carlo validation was performed.
- CSV quality, timestamp assumptions, and broker quote differences can materially change the result.
- Realistic live slippage, commissions, and liquidity impact were not added beyond the current engine assumptions.
- Historical performance does not guarantee future performance.
