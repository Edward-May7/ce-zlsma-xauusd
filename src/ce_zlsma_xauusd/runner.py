"""Application-service layer for running configured backtests."""

from __future__ import annotations

from . import engine
from .config import BacktestConfig


def run_configured_backtest(config: BacktestConfig) -> None:
    """Run a backtest from immutable configuration objects."""

    data = config.data
    risk = config.risk
    strategy = config.strategy
    output = config.output

    engine.run_backtest(
        symbol=data.symbol,
        period=data.period,
        interval=data.interval,
        csv_path=str(data.csv_path) if data.csv_path else None,
        demo=data.demo,
        cash=risk.cash,
        margin_per_001_lot=risk.margin_per_001_lot,
        lot_step=risk.lot_step,
        oz_per_full_lot=risk.oz_per_full_lot,
        risk_per_trade=risk.risk_per_trade,
        csv_tz=data.csv_tz,
        csv_cn_offset_hours=data.csv_cn_offset_hours,
        csv_assume_wallclock_tz=data.csv_assume_wallclock_tz,
        no_entry_sessions=data.no_entry_sessions,
        max_lots=risk.max_lots,
        plot=output.plot,
        report_dir=output.report_dir,
        no_charts=output.no_charts,
        write_replay_csv=output.write_replay_csv,
        replay_symbol=output.replay_symbol,
        replay_csv_name=output.replay_csv_name,
        zlsma_formula=strategy.zlsma_formula,
        ce_use_close_for_extremes=strategy.ce_use_close_for_extremes,
        zlsma_linreg_offset=max(0, strategy.zlsma_linreg_offset),
        ha_first_open_mode=strategy.ha_first_open_mode,
        partial_tp_r=risk.partial_tp_r,
        partial_tp_pct=risk.partial_tp_pct,
    )
