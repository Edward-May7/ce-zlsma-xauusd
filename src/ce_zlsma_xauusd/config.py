"""Typed configuration objects for CE + ZLSMA backtests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


ZlsmaFormula = Literal["veryfid", "gamma"]
HaFirstOpenMode = Literal["tv", "legacy_open0"]


@dataclass(frozen=True)
class DataConfig:
    """Market data source and timestamp interpretation."""

    symbol: str = "XAUUSD=X"
    period: str = "60d"
    interval: str = "5m"
    csv_path: Path | None = None
    demo: bool = False
    csv_tz: str | None = None
    csv_cn_offset_hours: float = 0.0
    csv_assume_wallclock_tz: str | None = None
    no_entry_sessions: bool = True


@dataclass(frozen=True)
class RiskConfig:
    """Position sizing and broker-style margin assumptions."""

    cash: float = 10_000.0
    margin_per_001_lot: float = 200.0
    lot_step: float = 0.01
    oz_per_full_lot: float = 100.0
    risk_per_trade: float = 0.02
    max_lots: float = 0.0
    partial_tp_r: float = 1.5
    partial_tp_pct: float = 50.0


@dataclass(frozen=True)
class StrategyConfig:
    """Indicator and execution-alignment parameters."""

    zlsma_formula: ZlsmaFormula = "veryfid"
    ce_use_close_for_extremes: bool = True
    zlsma_linreg_offset: int = 0
    ha_first_open_mode: HaFirstOpenMode = "tv"


@dataclass(frozen=True)
class OutputConfig:
    """Reporting destinations and artifact toggles."""

    report_dir: Path = Path("reports/baseline")
    no_charts: bool = False
    plot: bool = False
    write_replay_csv: bool = True
    replay_symbol: str = "XAU/USD"
    replay_csv_name: str = "trades_baseline.csv"


@dataclass(frozen=True)
class BacktestConfig:
    """Top-level immutable job configuration."""

    data: DataConfig = DataConfig()
    risk: RiskConfig = RiskConfig()
    strategy: StrategyConfig = StrategyConfig()
    output: OutputConfig = OutputConfig()


def baseline_config(repo_root: Path | None = None) -> BacktestConfig:
    """Return the repository's reproducible M5 baseline configuration."""

    root = repo_root or Path(__file__).resolve().parents[2]
    return BacktestConfig(
        data=DataConfig(
            csv_path=root / "data" / "XAUUSD_M5_202505010100_202604302255.csv",
            csv_cn_offset_hours=5,
        ),
        output=OutputConfig(report_dir=root / "reports" / "baseline"),
    )
