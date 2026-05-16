"""CE + ZLSMA XAUUSD backtesting package."""

from .config import BacktestConfig, DataConfig, OutputConfig, RiskConfig, StrategyConfig, baseline_config
from .engine import run_backtest
from .runner import run_configured_backtest

__all__ = [
    "BacktestConfig",
    "DataConfig",
    "OutputConfig",
    "RiskConfig",
    "StrategyConfig",
    "baseline_config",
    "run_backtest",
    "run_configured_backtest",
]
__version__ = "0.1.0"
