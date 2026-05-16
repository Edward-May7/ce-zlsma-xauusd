"""
XAUUSD 回测：Heikin Ashi + Chandelier Exit + ZLSMA

与 TradingView 典型挂法（XAUUSD：内置 **Heikin Ashi** + **@everget Chandelier Exit** ATR1×2 + **@veryfid ZLSMA** 长50/偏移0/源 close）在**指标、入场时序与规则价**上对齐；并与 Pine `fill_orders_on_standard_ohlc=true` 一致：**Backtrader 主序列 OHLC 为标准 K**，HA 仅作 `ha_*` 列参与 CE/ZLSMA/三连/与 ZLSMA 的过滤；**止损触价、follow-up 平仓价、市价开仓成交**均按标准 K 的 OHLC（对应 Pine `std*` / `execH`/`execL`）。

说明
----
- **Heikin Ashi** 在 `build_signal_frame` 中单独算成 `ha_Open`…`ha_Close`，**不**替换主线的 `Open`…`Close`（主线为标的真实 K 线，与 MT5/CSV/yfinance 一致）。
- CE：与 **everget** `Chandelier Exit`（Pine v6，如本机 `d:\\chandelier_exit.pine` 或 everget 仓库 `chandelier_exit.pine`）逐行对齐：`atr = mult * ta.atr(length)` **当根** Wilder ATR；极值默认 `highest(close,n)` / `lowest(close,n)`（`useClose=true`），可选 `highest(high,n)` / `lowest(low,n)`（`useClose=false`，见 `--ce-extremes-from-high-low`）；ratchet 与 `dir`/买卖信号与 Pine 第 22–31、39–44 行一致。默认 ATR 周期 1、乘数 2。
- ZLSMA：默认与 TV **@veryfid「ZLSMA - Zero Lag LSMA」** 一致：`lsma=linreg(src,len,0)`，`lsma2=linreg(lsma,len,0)`，`eq=lsma-lsma2`，`zlsma=lsma+eq`（即 `2*lsma-lsma2`）；`linreg` 取值按 Pine 公式 `intercept+slope*(length-1-offset)`。原版指标默认 **length=32**，本仓库默认 **50**（`ZLSMA_LEN`）仅为参数；可用 `--zlsma-linreg-offset` 对齐图表上的 offset。旧版仓库曾用 `lsma+(src-lsma)*2/(len+1)`（类 EMA），可用 `--zlsma-formula gamma` 复现。
- Heikin Ashi：默认 **TradingView / MT5 共识**（与 TV 内置平均K线一致）：``haClose=(O+H+L+C)/4``；首根 ``haOpen=(O+C)/2``；之后 ``haOpen=(haOpen[-1]+haClose[-1])/2``；``haHigh=max(H,haOpen,haClose)``；``haLow=min(L,haOpen,haClose)``。另可选 ``--ha-first-open legacy_open0``，首根 ``haOpen=Open[0]``，与 ``d:\\Heikin-Ashi backtest.py`` 第48–61行一致（该写法**不是** TV 默认）。`d:\\heikin-ashi-chart.md` 仅为 Avalonia 控件说明，无 K 线公式。
- 成交：严格按 TV 规则价模拟，不额外叠加点差/滑点；`spread` 列仍会读入保留，但默认不参与成交。
- 手数：**按初始止损定仓**：目标风险 = 当前权益 × `risk_per_trade`（默认 2%），
  数量（盎司）≈ `目标风险金额 / |入场价 - 初始止损价|`，再按 `lot_step` 手向下取整；若超过可用保证金则缩仓；可选 **`--max-lots`** 限制开仓单手数上限（如 `1` 表示最多 1.00 手）。
- 初始止损（回望 **HA** low/high，不含当根）：**多** = 过去 `risk_lookback` 根 `ha_Low` 最低；**空** = 过去 `risk_lookback` 根 `ha_High` 最高（默认根数见 `STRATEGY_RISK_LOOKBACK`，与 Pine `nearLowSignalBar`/`nearHighSignalBar` 一致）。
- 保证金：经纪商 **CFD 式** 每盎司冻结 `margin_per_001_lot / (lot_step×每手盎司)`（与 `--margin-per-001-lot` 一致），用于缩仓上限与拒单判断，**不再**用手数=权益/保证金那种满仓算法。
  若误用默认「股票式全额占用」，做多会全部被 **Margin** 拒单，而做空在 `shortcash` 下仍可能成交，造成「只有空单」的假现象。
- 入场：**上一根**收盘已确认 `ce_buy`/`ce_sell` 且该根 **HA 收盘**与 **ZLSMA** 满足上下关系后，在**当前根标准 K 开盘价**成交（`next_open` + `cheat_on_open`）；手数用 Pine 同款参考价 `oLongLot`/`oShortLot`（`stdC` 与「下一根 HA 开」的择大/择小）计算 `risk`。
- **反手**：持多/持空时若上一根同样满足**反向** CE+ZLSMA，且上一根标准 K **未触及**当前止损线，则本根开盘单笔加减仓反手（与 Pine `revShort`/`revLong` 一致）；禁开时段与空仓新开相同。
- 移动止损（与 Pine 一致）：
  - 持多/持空时，只要 **最近三根 HA 均为阴/阳**（含当根），每根收盘都把止损抬/压到这三根上 min(HA 极值, 标准 K 极值) 外侧，并置 `*_followup_pending`（连阴/连阳延续时每根更新，**不是**仅「首次」三连那一根才更新）。
  - **不是**「三连的下一根必定平仓」：仅在 **pending 为真** 时先判是否触移动止损，再按标准开盘与 ZLSMA 及连续 HA 阴/阳处理 TRIP_ZLS 或结束 pending；若已变阳/阴则 **不清仓**，清除 pending 后**继续持有**，直至再次出现「最近三根全阴/全阳」再重新进入该流程。
- **分批止盈（不调止损）**：冻结开仓时的初始风险价距 `self.risk`；当标准 K **最高/最低**价达到「成交价 ± `partial_tp_r`×risk」有利方向时，按 `partial_tp_pct`% 减仓（盎司数按 `lot_step` 向下取整）；**不**修改 `long_stop`/`short_stop`。每向仅触发一次。
- 禁开时段（默认开启）：上海时间每日 **04:00–06:30**、**15:00–21:45** 内禁止**空仓新开与反手**（与 Pine 禁开 session 对齐）；`--disable-no-entry-sessions` 可关闭。

数据。
----
- 默认 `yfinance`：`--symbol` 及备选 `XAUUSD=X`、`GC=F`（演示）。
- 限流或离线：`--csv your.csv` 或 `--demo` 合成数据自检。
- 若 MT5 导出 **无时区**（常见 `DATE`+`TIME`）：**默认不加小时偏移**；判禁开时段时，若服务器钟点与北京差固定值，请在命令行显式加 **`--csv-cn-offset-hours 5`**（全年固定 +H，常见 MT5 日界对齐上海用 5）。若时间戳 **已是北京时间**，保持默认 **0** 即可。
  - 可选 **`--csv-assume-timezone IANA`**：把无时区戳先 localize 到某时区再转上海（与 **`--csv-cn-offset-hours`** 互斥）；一般 MT5 用固定 +H 即可。
  - 索引 **已带时区**（如 yfinance）时：**忽略** 固定偏移，直接用 `→ Asia/Shanghai` 取钟点。

用法示例
--------
    python ce_zlsma_xauusd.py --symbol XAUUSD=X --period 60d --interval 5m
    python ce_zlsma_xauusd.py --csv "XAUUSD_M5_....csv" --csv-cn-offset-hours 5
    python ce_zlsma_xauusd.py --csv xau_m5.csv --csv-cn-offset-hours 5
    python ce_zlsma_xauusd.py --csv mt5.csv --csv-tz UTC --csv-cn-offset-hours 0
    python ce_zlsma_xauusd.py --demo
    python ce_zlsma_xauusd.py --csv xau.csv --report-dir ./out

说明：回测应使用 **全日连续 K 线序列**（HA/CE/ZLSMA 用全日 K，勿先裁切再喂数）；
默认启用 **两段禁开**（上海 04:00–06:30、15:00–21:45）；`--disable-no-entry-sessions` 可关闭。
**禁开「上海钟」与 CSV 对齐**：无时区 CSV 默认 **不加偏移**；需固定 +H 时在命令行传 **`--csv-cn-offset-hours`**（如 MT5 常用 **5**）。与 **`--csv-assume-timezone`** 互斥。若用 **`--csv-tz`** 先 localize 无时区戳，请设 **`--csv-cn-offset-hours 0`**，否则仍以偏移优先。
勿先删行再喂给 Backtrader，否则 `[-1]` 会跳过休市段，信号与 MT5/连续时间轴不一致。

复盘 CSV
--------
回测结束后在 `--report-dir` 下自动生成 `交易复盘_YYYY_M_D.csv`（在手工复盘表列基础上增加「平仓后权益」），
可用 `--no-replay-csv` 关闭；`--replay-symbol` 指定「品种」列显示名（默认 XAU/USD）。
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
import time
import types
from pathlib import Path

import backtrader as bt
import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    from yfinance.exceptions import YFRateLimitError
except ImportError:

    class YFRateLimitError(Exception):
        """旧版 yfinance 可能无此类；占位避免 import 失败。"""


# yfinance 限流时：单代码重试与代码之间间隔（秒）
YF_RETRIES_PER_SYMBOL = 4
YF_RETRY_BASE_SLEEP = 12.0
YF_SLEEP_BETWEEN_SYMBOLS = 6.0
POINT = 0.01  # XAUUSD 常见 1 point = 0.01
# 三连抬/压止损外侧偏移：与 Pine `POINT_TRIPLE`、MT5 EA `InpPointTriple` 默认一致；抬线取同三根上 min(HA低,标准低)（压对称）以免标准触价与仅 HA 抬线不一致
POINT_TRIPLE = 0.01
# 达 partial_tp_r×初始风险价距后部分平仓（不调止损）；与 Pine / EA 默认一致
PARTIAL_TP_R = 1.5
PARTIAL_TP_PCT = 50.0
SPREAD_POINTS = 10
SPREAD_PRICE = SPREAD_POINTS * POINT  # round-trip 总点差（价格）
HALF_SPREAD = SPREAD_PRICE / 2.0
SLIPPAGE_PERC = 0.001  # 千分之一

CE_ATR_PERIOD = 1
CE_MULT = 2.0
# 与 everget Pine `useClose` 默认一致：true=极值在 close 上，false=在 high/low 上
CE_USE_CLOSE_FOR_EXTREMES = True
ZLSMA_LEN = 50
ATR14_PERIOD = 14
STRATEGY_RISK_LOOKBACK = 8

# Heikin Ashi 首根 haOpen：与 TradingView 对齐用 tv；与 d:\Heikin-Ashi backtest.py 第52行对齐用 legacy_open0
HA_FIRST_OPEN_TV = "tv"
HA_FIRST_OPEN_LEGACY_OPEN0 = "legacy_open0"
HA_FIRST_OPEN_MODE = HA_FIRST_OPEN_TV

# 按 K 线时间戳的「小时」划分（与 MT5 CSV 服务器时间一致；若时区不同请改区间）
EUROPE_SESSION_HOURS = tuple(range(7, 16))  # 07–15
NEWYORK_SESSION_HOURS = tuple(range(12, 22))  # 12–21


def wilder_atr_series(h: pd.Series, l: pd.Series, c: pd.Series, period: int = ATR14_PERIOD) -> pd.Series:
    """Wilder ATR，用于分桶波动（与 CE 所用 ATR 无关）。"""
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    trv = tr.to_numpy(dtype=float)
    n = len(trv)
    atr = np.full(n, np.nan, dtype=float)
    if n < period:
        return pd.Series(atr, index=h.index)
    atr[period - 1] = float(np.nanmean(trv[:period]))
    for i in range(period, n):
        atr[i] = (atr[i - 1] * (period - 1) + trv[i]) / period
    return pd.Series(atr, index=h.index)


def heikin_ashi_ohlc_only(
    df: pd.DataFrame,
    first_open_mode: str = HA_FIRST_OPEN_MODE,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """由标准 OHLC 计算四条 HA 序列（不修改 df 的 Open/High/Low/Close）。

    递推式与 ``heikin_ashi`` 相同，输出 ``(ha_open, ha_high, ha_low, ha_close)``。
    """
    if first_open_mode not in (HA_FIRST_OPEN_TV, HA_FIRST_OPEN_LEGACY_OPEN0):
        raise ValueError(
            f"first_open_mode 须为 {HA_FIRST_OPEN_TV!r} 或 {HA_FIRST_OPEN_LEGACY_OPEN0!r}，收到: {first_open_mode!r}"
        )
    o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]
    ha_close = (o + h + l + c) / 4.0
    ha_open = pd.Series(index=df.index, dtype=float)
    if first_open_mode == HA_FIRST_OPEN_LEGACY_OPEN0:
        ha_open.iloc[0] = float(o.iloc[0])
    else:
        ha_open.iloc[0] = (o.iloc[0] + c.iloc[0]) / 2.0
    for i in range(1, len(df)):
        ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2.0
    ha_high = pd.concat([h, ha_open, ha_close], axis=1).max(axis=1)
    ha_low = pd.concat([l, ha_open, ha_close], axis=1).min(axis=1)
    return ha_open, ha_high, ha_low, ha_close


def heikin_ashi(
    df: pd.DataFrame,
    first_open_mode: str = HA_FIRST_OPEN_MODE,
) -> pd.DataFrame:
    """将普通 OHLC 转为 Heikin Ashi（**整表** Open/High/Low/Close 替换为 HA）。

    递推式（当前根普通价为 ``O,H,L,C``）：

    - ``haClose = (O + H + L + C) / 4``
    - 首根 ``haOpen[0]``：``first_open_mode=="tv"`` 时为 ``(O[0]+C[0])/2``（TradingView）；
      ``"legacy_open0"`` 时为 ``O[0]``（与 ``d:\\Heikin-Ashi backtest.py`` 第52行一致）。
    - ``i>0``：``haOpen[i] = (haOpen[i-1] + haClose[i-1]) / 2``
    - ``haHigh[i] = max(H[i], haOpen[i], haClose[i])``；``haLow[i] = min(L[i], haOpen[i], haClose[i])``
    """
    ha_open, ha_high, ha_low, ha_close = heikin_ashi_ohlc_only(df, first_open_mode)
    out = df.copy()
    out["Open"] = ha_open
    out["High"] = ha_high
    out["Low"] = ha_low
    out["Close"] = ha_close
    return out


def linreg_endpoint(y: np.ndarray, offset: int = 0) -> float:
    """TradingView `linreg` / `ta.linreg` 在窗口内的取值（与 @veryfid ZLSMA 所用 LSMA 一致）。

    Pine：`linreg(source, length, offset) -> intercept + slope * (length - 1 - offset)`，
    其中 `slope`/`intercept` 为对窗口内 `length` 个点、横坐标 ``0..length-1``（**最旧→最新**）
    的最小二乘直线。本函数中 ``y[0]`` 最旧、``y[-1]`` 最新，与 ``pandas.rolling`` 传入顺序一致。

    - ``offset == 0``：右端点 LSMA（与 veryfid 默认「偏移 0」一致）。
    """
    n = len(y)
    if n < 2:
        return float(y[-1])
    o = int(offset)
    if o < 0:
        o = 0
    if o > n - 1:
        o = n - 1
    x = np.arange(n, dtype=float)
    sum_x = x.sum()
    sum_y = y.sum()
    sum_x2 = (x * x).sum()
    sum_xy = (x * y).sum()
    denom = n * sum_x2 - sum_x**2
    if abs(denom) < 1e-18:
        return float(y[-1])
    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    x_at = float((n - 1) - o)
    return float(slope * x_at + intercept)


def rolling_lsma(series: pd.Series, length: int, offset: int = 0) -> pd.Series:
    return series.rolling(length).apply(
        lambda w: linreg_endpoint(np.asarray(w, dtype=float), offset), raw=False
    )


def add_zlsma(
    df: pd.DataFrame,
    length: int = ZLSMA_LEN,
    formula: str = "veryfid",
    linreg_offset: int = 0,
) -> pd.Series:
    """ZLSMA 两种常见定义（均用 HA 序列的 Close 作 src，与指标挂在 HA 图上一致）。

    - **veryfid**：与 veryfid 原版 Pine（如「ZLSMA - Zero Lag LSMA」）一致：
      ``lsma = linreg(src, length, offset)``，``lsma2 = linreg(lsma, length, offset)``，
      ``eq = lsma - lsma2``，``zlsma = lsma + eq``（即 ``2*lsma - lsma2``）。默认 ``offset=0``；
      指标里默认 ``length=32``，本策略顶层用 ``ZLSMA_LEN``（默认 50）仅为参数选择，非公式差异。
    - **gamma**：旧版/部分脚本写法 `lsma + (src - lsma) * 2/(length+1)`，与 veryfid **不是同一曲线**。
    """
    src = df["Close"]
    if formula == "gamma":
        lsma = rolling_lsma(src, length, 0)
        gamma = 2.0 / (length + 1.0)
        return lsma + (src - lsma) * gamma
    if formula == "veryfid":
        lo = max(0, int(linreg_offset))
        if length > 1 and lo > length - 1:
            lo = length - 1
        lsma = rolling_lsma(src, length, lo)
        lsma2 = rolling_lsma(lsma, length, lo)
        return 2.0 * lsma - lsma2
    raise ValueError(f"zlsma formula 须为 'veryfid' 或 'gamma'，收到: {formula!r}")


def true_range_row(high: float, low: float, prev_close: float) -> float:
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def chandelier_exit(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr_period: int,
    mult: float,
    use_close_for_extremes: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """everget「Chandelier Exit」Pine v6 逻辑（与 `d:\\chandelier_exit.pine` 第 20–44 行等价）。

    - `atr = mult * ta.atr(length)`：Wilder ATR 再乘 mult；**当根** ATR，无 `ta.atr(...)[1]`。
    - 极值：`use_close_for_extremes=True` → `ta.highest(close,n)` / `ta.lowest(close,n)`；
      `False` → Pine `ta.highest(length)` / `ta.lowest(length)`（即 **high** / **low** 源上的 rolling 极值）。
    - `longStop`/`shortStop` ratchet：`close[1] > longStopPrev` 等 ↔ 本循环 `close[i-1]` 与 `long_stop[i-1]`。
    - `dir` ↔ `trend`：`close > shortStopPrev` / `close < longStopPrev` ↔ `close[i]` 与 `short_stop[i-1]`/`long_stop[i-1]`。
    - `buySignal`/`sellSignal` ↔ `buy`/`sell`：`dir==1 && dir[1]==-1` 等。
    """
    n = len(close)
    h_s = pd.Series(high, dtype=float)
    l_s = pd.Series(low, dtype=float)
    c_s = pd.Series(close, dtype=float)
    prev_c = c_s.shift(1)
    tr_s = pd.concat([h_s - l_s, (h_s - prev_c).abs(), (l_s - prev_c).abs()], axis=1).max(axis=1)
    trv = tr_s.to_numpy(dtype=float)
    p = max(1, atr_period)
    atr_arr = wilder_atr_series(h_s, l_s, c_s, p).to_numpy(dtype=float)
    atr_arr = np.where(np.isnan(atr_arr), trv, atr_arr)
    atr_band = mult * atr_arr

    long_stop = np.zeros(n, dtype=float)
    short_stop = np.zeros(n, dtype=float)
    trend = np.ones(n, dtype=np.int8)
    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)

    for i in range(n):
        lb = max(0, i - p + 1)
        if use_close_for_extremes:
            hh = float(close[lb : i + 1].max())
            ll = float(close[lb : i + 1].min())
        else:
            hh = float(high[lb : i + 1].max())
            ll = float(low[lb : i + 1].min())

        ls_raw = hh - atr_band[i]
        ss_raw = ll + atr_band[i]

        if i > 0 and close[i - 1] > long_stop[i - 1]:
            ls = max(ls_raw, long_stop[i - 1])
        else:
            ls = ls_raw

        if i > 0 and close[i - 1] < short_stop[i - 1]:
            ss = min(ss_raw, short_stop[i - 1])
        else:
            ss = ss_raw

        long_stop[i] = ls
        short_stop[i] = ss

        if i == 0:
            trend[i] = 1 if close[i] > ss else (-1 if close[i] < ls else 1)
        else:
            l_prev = long_stop[i - 1]
            s_prev = short_stop[i - 1]
            if close[i] > s_prev:
                trend[i] = 1
            elif close[i] < l_prev:
                trend[i] = -1
            else:
                trend[i] = trend[i - 1]

        if i > 0:
            buy[i] = trend[i] == 1 and trend[i - 1] == -1
            sell[i] = trend[i] == -1 and trend[i - 1] == 1

    return long_stop, short_stop, trend, buy, sell


def _normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """将 MT5 风格 `<OPEN>` 或大小写混杂列名转为小写标识。"""
    out = df.copy()
    out.columns = [str(c).strip().strip("<>").strip().lower() for c in out.columns]
    return out


def _index_to_shanghai(idx: pd.DatetimeIndex, csv_tz: str | None) -> pd.DatetimeIndex:
    """将索引转为 Asia/Shanghai 墙上时钟（用于时段判断）。"""
    if idx.tz is None:
        if csv_tz:
            return idx.tz_localize(
                csv_tz, ambiguous="infer", nonexistent="shift_forward"
            ).tz_convert("Asia/Shanghai")
        return idx.tz_localize("Asia/Shanghai")
    return idx.tz_convert("Asia/Shanghai")


def session_rule_shanghai_hour_minute(
    index: pd.DatetimeIndex,
    csv_tz: str | None,
    csv_cn_offset_hours: float,
    csv_assume_wallclock_tz: str | None,
) -> tuple[np.ndarray, np.ndarray]:
    """返回用于禁开时段判断的「上海」小时与分钟（整索引逐根）。

    优先级：
    1. ``csv_assume_wallclock_tz``：无时区索引先 ``tz_localize(该 IANA)`` 再 ``tz_convert(Asia/Shanghai)``。
    2. ``csv_cn_offset_hours != 0`` 且索引 **无时区**：``index + Timedelta(hours=...)`` 后取 ``.hour/.minute``（全年固定偏移，MT5 无时区 CSV 常用 +5）。
    3. 否则：``_index_to_shanghai(index, csv_tz)``（索引已带时区时走此路径，**不**再叠加固定偏移）。
    """
    if len(index) == 0:
        return np.array([], dtype=np.int32), np.array([], dtype=np.int32)
    if csv_assume_wallclock_tz:
        wz = str(csv_assume_wallclock_tz).strip()
        if not wz:
            raise ValueError("csv_assume_wallclock_tz 为空")
        if index.tz is not None:
            raise ValueError(
                "使用 --csv-assume-timezone 时需要无时区 DatetimeIndex（CSV 读入默认无时区）。"
            )
        loc = index.tz_localize(
            wz,
            ambiguous="infer",
            nonexistent="shift_forward",
        )
        sh = loc.tz_convert("Asia/Shanghai")
        return np.asarray(sh.hour, dtype=np.int32), np.asarray(sh.minute, dtype=np.int32)
    if csv_cn_offset_hours != 0 and index.tz is None:
        t = index + pd.Timedelta(hours=float(csv_cn_offset_hours))
        return np.asarray(t.hour, dtype=np.int32), np.asarray(t.minute, dtype=np.int32)
    ts = _index_to_shanghai(index, csv_tz)
    return np.asarray(ts.hour, dtype=np.int32), np.asarray(ts.minute, dtype=np.int32)


def no_entry_sessions_mask_bool(
    index: pd.DatetimeIndex,
    csv_tz: str | None,
    csv_cn_offset_hours: float = 0.0,
    csv_assume_wallclock_tz: str | None = None,
) -> np.ndarray:
    """上海时间（经 assume/偏移/转上海 后的墙上时钟）落在两段禁开内为 True。

    与 Pine `NO_ENTRY_SESSION` / `NO_ENTRY_SESSION2`（Asia/Shanghai）一致：
    - [04:00, 06:30)
    - [15:00, 21:45)
    仅用于禁止新开仓；钟点换算与 ``session_rule_shanghai_hour_minute`` 一致。
    """
    if len(index) == 0:
        return np.array([], dtype=bool)
    h, mi = session_rule_shanghai_hour_minute(
        index, csv_tz, csv_cn_offset_hours, csv_assume_wallclock_tz
    )
    mins = h * 60 + mi
    b1 = (mins >= 4 * 60) & (mins < 6 * 60 + 30)
    b2 = (mins >= 15 * 60) & (mins < 21 * 60 + 45)
    return (b1 | b2).astype(bool)


def _apply_session_masks(
    full: pd.DataFrame,
    *,
    no_entry_sessions: bool,
    csv_tz: str | None,
    csv_cn_offset_hours: float,
    csv_assume_wallclock_tz: str | None,
    source: str,
) -> pd.DataFrame:
    """写入 `in_entry_window_ok`（1=允许新开仓）并打印说明。与 Pine 一致：仅两段禁开，无额外「中国时段」白名单。"""
    if csv_cn_offset_hours and csv_assume_wallclock_tz:
        raise SystemExit(
            "勿同时使用 --csv-cn-offset-hours 与 --csv-assume-timezone，请二选一。"
        )
    if csv_assume_wallclock_tz and csv_tz:
        raise SystemExit(
            "勿同时使用 --csv-assume-timezone 与 --csv-tz；使用 assume 时不要设 --csv-tz。"
        )
    out = full.copy()
    if no_entry_sessions:
        blocked = no_entry_sessions_mask_bool(
            out.index, csv_tz, csv_cn_offset_hours, csv_assume_wallclock_tz
        )
        out["in_entry_window_ok"] = (~blocked).astype(np.float64)
        n_ok = int((~blocked).sum())
        src = {"CSV": "CSV", "yfinance": "yfinance", "demo": "合成数据"}.get(
            source, source
        )
        if csv_assume_wallclock_tz:
            off_h = (
                f" 时间判据：无时区戳视为 {csv_assume_wallclock_tz} 墙钟→Asia/Shanghai。"
            )
        elif csv_cn_offset_hours and out.index.tz is None:
            off_h = (
                f" 时间判据：无时区戳 +{csv_cn_offset_hours:g}h 为上海钟（全年固定）。"
            )
        else:
            off_h = (
                " 时间判据：无时区索引按上海/转上海。"
                if source == "CSV" and out.index.tz is None
                else ""
            )
        print(
            f"[禁开时段] 上海时间 04:00–06:30、15:00–21:45 内禁止新开仓（与 Pine 对齐）；"
            f"{src} 全日 K={len(out)}，不在禁开窗内可新开仓 K={n_ok}。"
            + off_h
        )
    else:
        out["in_entry_window_ok"] = 1.0
    return out


def read_ohlcv_csv(path: str | Path) -> pd.DataFrame:
    """
    读取 CSV：支持 MT5「历史中心导出」（DATE+TIME+OHLC+TICKVOL）与常见英文列名。
    返回带 DatetimeIndex 的 DataFrame，列名为 Open, High, Low, Close, Volume。
    """
    p = Path(path)
    raw = pd.read_csv(p, sep="\t")
    if raw.shape[1] == 1:
        raw = pd.read_csv(p)

    df = _normalize_column_names(raw)

    if "date" in df.columns and "time" in df.columns:
        ts = (
            df["date"].astype(str).str.strip()
            + " "
            + df["time"].astype(str).str.strip()
        )
        idx = pd.to_datetime(ts, format="%Y.%m.%d %H:%M:%S", errors="coerce")
        if idx.isna().all():
            idx = pd.to_datetime(ts, errors="coerce")
        df = df.set_index(idx)
    elif "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        df = df.set_index("datetime")
    elif "time" in df.columns and len(df.columns) <= 6:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        df = df.set_index("time")
    else:
        raise ValueError(
            "无法解析时间列：需要 MT5 的 date+time，或 datetime 列，或 time 索引列。"
        )

    name_map = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
    }
    for a, b in name_map.items():
        if a not in df.columns:
            raise ValueError(f"缺少列: {a}（原始 CSV 列名可能不同）")
        df[b] = pd.to_numeric(df[a], errors="coerce")

    if "tickvol" in df.columns:
        df["Volume"] = pd.to_numeric(df["tickvol"], errors="coerce").fillna(0)
    elif "volume" in df.columns:
        df["Volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
    elif "vol" in df.columns:
        df["Volume"] = pd.to_numeric(df["vol"], errors="coerce").fillna(0)
    else:
        df["Volume"] = 0.0

    if "spread" in df.columns:
        sp = pd.to_numeric(df["spread"], errors="coerce").fillna(float(SPREAD_POINTS))
    else:
        sp = pd.Series(float(SPREAD_POINTS), index=df.index)
    out = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    out["SpreadPoints"] = sp.reindex(out.index).astype(float)
    out = out[~out.index.duplicated(keep="first")]
    out = out.sort_index()
    out = out.dropna(how="any")
    return out


def build_signal_frame(
    raw: pd.DataFrame,
    zlsma_formula: str = "veryfid",
    ce_use_close_for_extremes: bool = CE_USE_CLOSE_FOR_EXTREMES,
    zlsma_linreg_offset: int = 0,
    ha_first_open_mode: str = HA_FIRST_OPEN_MODE,
) -> pd.DataFrame:
    """原始标准 OHLCV + 并行 HA → ZLSMA + CE 信号（索引对齐）。

    **主 OHLC 保持为标准 K**（与 Pine ``ticker.standard`` / ``fill_orders_on_standard_ohlc`` 一致）；
    ``ha_Open``…``ha_Close`` 为 Heikin Ashi，用于 CE、ZLSMA、三连与相对 ZLSMA 的过滤。
    """
    df = raw.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        if "Datetime" in df.columns:
            df["Datetime"] = pd.to_datetime(df["Datetime"])
            df = df.set_index("Datetime")
        elif "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")
    df = df.sort_index()
    for col in ("Open", "High", "Low", "Close"):
        if col not in df.columns:
            raise ValueError(f"缺少列: {col}")
    if "Volume" not in df.columns:
        df["Volume"] = 0.0

    if "SpreadPoints" not in df.columns:
        df["SpreadPoints"] = float(SPREAD_POINTS)

    ohlcv = df[["Open", "High", "Low", "Close", "Volume"]]
    ha_open, ha_high, ha_low, ha_close = heikin_ashi_ohlc_only(
        ohlcv,
        first_open_mode=ha_first_open_mode,
    )
    ha_sig = pd.DataFrame(
        {
            "Open": ha_open,
            "High": ha_high,
            "Low": ha_low,
            "Close": ha_close,
        },
        index=df.index,
    )
    ha_sig["SpreadPoints"] = (
        df["SpreadPoints"].reindex(ha_sig.index).ffill().bfill().astype(float).clip(lower=0.1)
    )
    ha_sig["half_spread_price"] = ha_sig["SpreadPoints"] * POINT / 2.0

    ha_sig["zlsma"] = add_zlsma(
        ha_sig, ZLSMA_LEN, formula=zlsma_formula, linreg_offset=zlsma_linreg_offset
    )

    h = ha_sig["High"].to_numpy(dtype=float)
    l = ha_sig["Low"].to_numpy(dtype=float)
    c = ha_sig["Close"].to_numpy(dtype=float)
    ls, ss, tr, bu, se = chandelier_exit(
        h, l, c, CE_ATR_PERIOD, CE_MULT, use_close_for_extremes=ce_use_close_for_extremes
    )

    out = df.copy()
    out["half_spread_price"] = out["SpreadPoints"] * POINT / 2.0
    out["ha_Open"] = ha_open
    out["ha_High"] = ha_high
    out["ha_Low"] = ha_low
    out["ha_Close"] = ha_close
    out["zlsma"] = ha_sig["zlsma"]
    out["ce_long_stop"] = ls
    out["ce_short_stop"] = ss
    out["ce_trend"] = tr.astype(int)
    out["ce_buy"] = bu.astype(bool)
    out["ce_sell"] = se.astype(bool)
    out["atr14"] = wilder_atr_series(ha_sig["High"], ha_sig["Low"], ha_sig["Close"], ATR14_PERIOD)
    if "in_entry_window_ok" not in out.columns:
        out["in_entry_window_ok"] = 1.0
    return out


def _normalize_yf_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns={"Adj Close": "Close"})
    if "Volume" not in df.columns:
        df["Volume"] = 0.0
    if "SpreadPoints" not in df.columns:
        df["SpreadPoints"] = float(SPREAD_POINTS)
    cols = ["Open", "High", "Low", "Close", "Volume", "SpreadPoints"]
    return df[cols].dropna(how="any")


def download_yf(
    symbol: str,
    period: str,
    interval: str,
    retries: int = YF_RETRIES_PER_SYMBOL,
    base_sleep: float = YF_RETRY_BASE_SLEEP,
) -> pd.DataFrame:
    if yf is None:
        raise RuntimeError("未安装 yfinance，请 pip install yfinance 或使用 --csv")
    last_exc: BaseException | None = None
    for attempt in range(retries):
        if attempt > 0:
            wait = base_sleep * attempt
            print(f"[yfinance] {symbol} 第 {attempt + 1}/{retries} 次尝试，等待 {wait:.0f}s …", file=sys.stderr)
            time.sleep(wait)
        try:
            df = yf.download(
                symbol,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=False,
            )
        except YFRateLimitError as e:
            last_exc = e
            print(f"[yfinance] {symbol} 限流: {e}", file=sys.stderr)
            continue
        except Exception as e:
            last_exc = e
            print(f"[yfinance] {symbol} 下载异常: {e}", file=sys.stderr)
            return pd.DataFrame()

        if not df.empty:
            return _normalize_yf_df(df)

        print(f"[yfinance] {symbol} 返回空表（可能限流或无数据）", file=sys.stderr)

    if last_exc is not None:
        print(f"[yfinance] {symbol} 放弃: {last_exc}", file=sys.stderr)
    return pd.DataFrame()


def synthetic_ohlcv(n: int = 800, freq: str = "5min", seed: int = 42) -> pd.DataFrame:
    """离线自检用随机游走 OHLCV（非真实行情）。"""
    rng = pd.date_range("2025-01-01", periods=n, freq=freq, tz="UTC")
    rs = np.random.default_rng(seed)
    close = 2600.0 + np.cumsum(rs.normal(0, 1.2, n))
    high = close + rs.uniform(0.5, 3.0, n)
    low = close - rs.uniform(0.5, 3.0, n)
    open_ = np.r_[close[0], close[:-1]] + rs.normal(0, 0.3, n)
    open_[0] = close[0]
    vol = rs.integers(100, 1000, n)
    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": vol,
            "SpreadPoints": np.full(n, float(SPREAD_POINTS), dtype=float),
        },
        index=rng,
    )


def load_price_data(
    symbol: str,
    period: str,
    interval: str,
    csv_path: str | None,
    demo: bool = False,
    csv_tz: str | None = None,
    csv_cn_offset_hours: float = 0.0,
    csv_assume_wallclock_tz: str | None = None,
    zlsma_formula: str = "veryfid",
    ce_use_close_for_extremes: bool = CE_USE_CLOSE_FOR_EXTREMES,
    zlsma_linreg_offset: int = 0,
    ha_first_open_mode: str = HA_FIRST_OPEN_MODE,
    no_entry_sessions: bool = True,
) -> pd.DataFrame:
    if demo and csv_assume_wallclock_tz:
        raise SystemExit(
            "--csv-assume-timezone 与 --demo 不兼容（合成数据索引为 UTC 带时区）。"
        )
    if demo:
        print("[提示] 使用 --demo 合成数据做自检（非真实 XAUUSD）。", file=sys.stderr)
        full = build_signal_frame(
            synthetic_ohlcv(),
            zlsma_formula=zlsma_formula,
            ce_use_close_for_extremes=ce_use_close_for_extremes,
            zlsma_linreg_offset=zlsma_linreg_offset,
            ha_first_open_mode=ha_first_open_mode,
        )
        return _apply_session_masks(
            full,
            no_entry_sessions=no_entry_sessions,
            csv_tz=csv_tz,
            csv_cn_offset_hours=csv_cn_offset_hours,
            csv_assume_wallclock_tz=csv_assume_wallclock_tz,
            source="demo",
        )

    if csv_path:
        p = Path(csv_path)
        if not p.exists():
            raise FileNotFoundError(csv_path)
        raw = read_ohlcv_csv(p)
        full = build_signal_frame(
            raw,
            zlsma_formula=zlsma_formula,
            ce_use_close_for_extremes=ce_use_close_for_extremes,
            zlsma_linreg_offset=zlsma_linreg_offset,
            ha_first_open_mode=ha_first_open_mode,
        )
        return _apply_session_masks(
            full,
            no_entry_sessions=no_entry_sessions,
            csv_tz=csv_tz,
            csv_cn_offset_hours=csv_cn_offset_hours,
            csv_assume_wallclock_tz=csv_assume_wallclock_tz,
            source="CSV",
        )

    if yf is None:
        raise RuntimeError("未安装 yfinance，请 pip install yfinance 或使用 --csv")

    candidates = []
    for sym in (symbol, "XAUUSD=X", "GC=F", "SI=F"):
        if sym not in candidates:
            candidates.append(sym)
    tried = []
    for i, sym in enumerate(candidates):
        tried.append(sym)
        if i > 0:
            print(
                f"[yfinance] 切换代码前等待 {YF_SLEEP_BETWEEN_SYMBOLS:.0f}s，减轻限流…",
                file=sys.stderr,
            )
            time.sleep(YF_SLEEP_BETWEEN_SYMBOLS)
        raw = download_yf(sym, period=period, interval=interval)
        if not raw.empty:
            if sym != symbol:
                print(f"[提示] 符号 {symbol} 无数据或失败，已改用 {sym} 下载。", file=sys.stderr)
            full = build_signal_frame(
                raw,
                zlsma_formula=zlsma_formula,
                ce_use_close_for_extremes=ce_use_close_for_extremes,
                zlsma_linreg_offset=zlsma_linreg_offset,
                ha_first_open_mode=ha_first_open_mode,
            )
            return _apply_session_masks(
                full,
                no_entry_sessions=no_entry_sessions,
                csv_tz=csv_tz,
                csv_cn_offset_hours=csv_cn_offset_hours,
                csv_assume_wallclock_tz=csv_assume_wallclock_tz,
                source="yfinance",
            )
    raise RuntimeError(
        "未能从 Yahoo Finance 获取数据。\n"
        "最常见原因：Yahoo 对匿名请求 **限流**（HTTP 429 / YFRateLimitError: Too Many Requests）。"
        "连续请求多个代码、短时间内多次运行脚本，都容易触发。\n\n"
        "**可行方案：**\n"
        "  1) 等待 15～60 分钟后再运行；同一时段只拉一个代码、减少 `period` 长度也可降低触发概率。\n"
        "  2) 使用本地数据：`python ce_zlsma_xauusd.py --csv 你的文件.csv`\n"
        "  3) 先跑通逻辑：`python ce_zlsma_xauusd.py --demo`\n"
        "  4) 从 MT4/MT5/券商导出 XAUUSD OHLCV，不依赖 Yahoo。\n\n"
        f"已尝试代码: {tried}\n"
        "脚本已对单代码做多次重试、并在切换代码前等待；若仍失败，请优先用 CSV 或稍后再试。"
    )


class HABTData(bt.feeds.PandasData):
    lines = (
        "ha_open",
        "ha_high",
        "ha_low",
        "ha_close",
        "zlsma",
        "ce_buy",
        "ce_sell",
        "ce_long_stop",
        "ce_short_stop",
        "atr14",
        "half_spread_price",
        "in_entry_window_ok",
    )
    params = (
        ("datetime", None),
        ("open", "Open"),
        ("high", "High"),
        ("low", "Low"),
        ("close", "Close"),
        ("volume", "Volume"),
        ("openinterest", None),
        ("ha_open", "ha_Open"),
        ("ha_high", "ha_High"),
        ("ha_low", "ha_Low"),
        ("ha_close", "ha_Close"),
        ("zlsma", "zlsma"),
        ("ce_buy", "ce_buy"),
        ("ce_sell", "ce_sell"),
        ("ce_long_stop", "ce_long_stop"),
        ("ce_short_stop", "ce_short_stop"),
        ("atr14", "atr14"),
        ("half_spread_price", "half_spread_price"),
        ("in_entry_window_ok", "in_entry_window_ok"),
    )


class EquityCurveAnalyzer(bt.Analyzer):
    """记录每根 K 线收盘后权益，用于曲线与回撤。"""

    def __init__(self):
        self.equity: list[float] = []
        self.bar_idx: list[int] = []
        self.dates: list = []

    def next(self):
        self.equity.append(float(self.strategy.broker.getvalue()))
        self.bar_idx.append(len(self.strategy))
        self.dates.append(self.strategy.datetime.datetime())


class CEZLSMAStrategy(bt.Strategy):
    """交易规则与 Pine 一致：CE/ZLSMA/三连/过滤用 **HA**（`ha_*` 线）；触价与市价成交用 **标准 K**（主 OHLC）。

    多仓 `_manage_long`：**最近三根 HA 均为阴** 时滚动抬止损 → **达 R 倍数分批止盈（不调止损）** → follow-up → 标准 K low 触止损等。
    反手：持多/持空时上一根收盘出现反向 CE+ZLSMA 且未触止损，则本根标准 K 开盘平仓并反手（`next_open`）。
    与 MT5 EA `OnTick` 对齐：本根 `next_open` 末尾在无挂单、无持仓时仍会评估空仓新开；反向 CE **仅平仓**且在同一回调内已清空持仓时，在 `return` 前亦尝试一次（`_try_flat_entry_next_open`）。
    """

    params = dict(
        risk_lookback=STRATEGY_RISK_LOOKBACK,
        printlog=False,
        margin_per_001_lot=200.0,
        lot_step=0.01,
        oz_per_full_lot=100.0,
        risk_per_trade=0.02,
        max_lots=0.0,
        atr_q33=0.0,
        atr_q66=0.0,
        partial_tp_r=PARTIAL_TP_R,
        partial_tp_pct=PARTIAL_TP_PCT,
    )

    def __init__(self):
        self.order = None
        self.entry_price = 0.0
        self.risk = 0.0
        self.direction = 0
        self.long_stop = 0.0
        self.short_stop = 0.0
        self.long_followup_pending = False
        self.short_followup_pending = False
        self.partial_tp_done = False
        self._last_open_risk_cash = 0.0
        self._last_open_equity = 1.0
        self._last_open_atr = float("nan")
        self._last_entry_is_long = False
        self.closed_trades: list[dict] = []
        self.equity_on_trade_close: list[tuple[int, float]] = []
        # 交易复盘 CSV（与 notify_trade 同步）
        self._csv_exit_reason: str = ""
        self._csv_entry_reason: str = ""
        self._csv_entry_units: float = 0.0
        self._csv_entry_dt = None
        self._csv_entry_px: float = 0.0
        self.rule_events: list[dict] = []

    def log(self, txt):
        if self.p.printlog:
            print(self.datetime.date(), txt)

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        pnl = float(trade.pnlcomm)
        barlen = int(getattr(trade, "barlen", 0) or 0)
        is_long = self._last_entry_is_long
        risk_pct = (
            (self._last_open_risk_cash / self._last_open_equity * 100.0)
            if self._last_open_equity > 0
            else 0.0
        )
        hour = 0
        try:
            from matplotlib.dates import num2date

            hour = num2date(trade.dtclose).hour
        except Exception:
            try:
                hour = bt.num2date(trade.dtclose).hour
            except Exception:
                hour = 0

        atr = float(self._last_open_atr)
        atr_bucket = self._atr_bucket(atr)
        in_eu = hour in EUROPE_SESSION_HOURS
        in_ny = hour in NEWYORK_SESSION_HOURS
        try:
            exit_dt = bt.num2date(trade.dtclose)
        except Exception:
            exit_dt = self.datetime.datetime()
        entry_px = float(self._csv_entry_px)
        units = float(self._csv_entry_units)
        if units > 1e-12:
            if is_long:
                exit_px = entry_px + pnl / units
            else:
                exit_px = entry_px - pnl / units
        else:
            exit_px = float(getattr(trade, "price", 0.0) or 0.0)
        lots = units / float(self.p.oz_per_full_lot) if units > 1e-12 else 0.0
        exit_reason = self._csv_exit_reason.strip() or "其他"
        if exit_reason == "止损" and pnl > 1e-6:
            exit_reason = "移动止盈"
        equity_after = float(self.broker.getvalue())
        self.closed_trades.append(
            dict(
                pnl=pnl,
                bars=barlen,
                is_long=is_long,
                risk_pct=risk_pct,
                hour=hour,
                atr=atr,
                atr_bucket=atr_bucket,
                in_europe=in_eu,
                in_newyork=in_ny,
                exit_reason=exit_reason,
                entry_reason=self._csv_entry_reason,
                entry_dt=self._csv_entry_dt,
                entry_px=entry_px,
                exit_dt=exit_dt,
                exit_px=exit_px,
                lots=lots,
                equity_after_trade=equity_after,
            )
        )
        self.equity_on_trade_close.append(
            (len(self.equity_on_trade_close) + 1, equity_after)
        )

    def _atr_bucket(self, atr: float) -> str:
        if math.isnan(atr) or self.p.atr_q33 <= 0 or self.p.atr_q66 <= self.p.atr_q33:
            return "N/A"
        if atr < self.p.atr_q33:
            return "低波动"
        if atr < self.p.atr_q66:
            return "中波动"
        return "高波动"

    def _margin_cash_per_oz(self) -> float:
        return self.p.margin_per_001_lot / (self.p.lot_step * self.p.oz_per_full_lot)

    def _size_units_for_stop_distance(self, risk_price: float) -> float:
        """按「权益×risk_per_trade / 每盎司止损距离」算盎司数，再按手数步长向下取整；受保证金上限约束。"""
        if risk_price <= 1e-12:
            return 0.0
        eq = max(float(self.broker.getvalue()), 0.0)
        risk_cash = eq * float(self.p.risk_per_trade)
        raw_units = risk_cash / risk_price
        step = self.p.lot_step
        oz = self.p.oz_per_full_lot
        lots = raw_units / oz
        lots = math.floor(lots / step + 1e-12) * step
        if lots < step - 1e-12:
            return 0.0
        units = lots * oz
        m_oz = self._margin_cash_per_oz()
        if m_oz > 1e-12:
            max_u = (eq * (1.0 - 1e-9)) / m_oz
            if units > max_u:
                lots = math.floor(max_u / oz / step + 1e-12) * step
                if lots < step - 1e-12:
                    return 0.0
                units = lots * oz
        ml = float(self.p.max_lots)
        if ml > 0 and math.isfinite(ml):
            cap_lots = math.floor(float(ml) / step + 1e-12) * step
            cap_u = cap_lots * oz
            if units > cap_u + 1e-9:
                units = cap_u
        return float(units)

    def notify_order(self, order):
        if order.status in (order.Submitted, order.Accepted):
            return
        if order.status in (order.Completed,):
            self.log(f"成交 {'买' if order.isbuy() else '卖'} 价={order.executed.price:.5f} 数量={order.executed.size}")
        if order.status in (
            order.Completed,
            order.Canceled,
            order.Margin,
            order.Rejected,
        ):
            self.order = None

    def _near_low_prior(self) -> float:
        """开仓用：回望 **HA** low（不含当根），与 Pine `nearLowSignalBar` 一致。"""
        lb = self.p.risk_lookback
        return min(float(self.data.ha_low[-1 - i]) for i in range(lb))

    def _near_high_prior(self) -> float:
        lb = self.p.risk_lookback
        return max(float(self.data.ha_high[-1 - i]) for i in range(lb))

    def _is_bearish(self) -> bool:
        return float(self.data.ha_close[0]) < float(self.data.ha_open[0])

    def _is_bullish(self) -> bool:
        return float(self.data.ha_close[0]) > float(self.data.ha_open[0])

    def _three_bearish(self) -> bool:
        """最近三根 HA（含当根）均为阴；用于每根收盘滚动抬多仓止损。"""
        return self._is_bearish() and float(self.data.ha_close[-1]) < float(
            self.data.ha_open[-1]
        ) and float(self.data.ha_close[-2]) < float(self.data.ha_open[-2])

    def _three_bullish(self) -> bool:
        """最近三根 HA（含当根）均为阳；用于每根收盘滚动压空仓止损。"""
        return self._is_bullish() and float(self.data.ha_close[-1]) > float(
            self.data.ha_open[-1]
        ) and float(self.data.ha_close[-2]) > float(self.data.ha_open[-2])

    def _min_low3(self) -> float:
        """三连阴对应三根：取 HA 与标准 K 的较低低（与 Pine minLow3 一致，避免触价用 stdL 抬线仅用 haL）。"""
        ha_m = min(
            float(self.data.ha_low[0]),
            float(self.data.ha_low[-1]),
            float(self.data.ha_low[-2]),
        )
        std_m = min(
            float(self.data.low[0]),
            float(self.data.low[-1]),
            float(self.data.low[-2]),
        )
        return min(ha_m, std_m)

    def _max_high3(self) -> float:
        """三连阳对应三根：取 HA 与标准 K 的较高高（对称 min_low3）。"""
        ha_m = max(
            float(self.data.ha_high[0]),
            float(self.data.ha_high[-1]),
            float(self.data.ha_high[-2]),
        )
        std_m = max(
            float(self.data.high[0]),
            float(self.data.high[-1]),
            float(self.data.high[-2]),
        )
        return max(ha_m, std_m)

    def _allow_new_entry_now(self) -> bool:
        try:
            return float(self.data.in_entry_window_ok[0]) > 0.5
        except Exception:
            return True

    def _record_rule_event(
        self,
        event: str,
        direction: str,
        size_units: float,
        rule_price: float,
        actual_price: float = 0.0,
    ) -> None:
        self.rule_events.append(
            dict(
                time=self.datetime.datetime(),
                event=event,
                direction=direction,
                lots=abs(float(size_units)) / float(self.p.oz_per_full_lot),
                rule_price=float(rule_price),
                actual_price=float(actual_price),
                ha_open=float(self.data.ha_open[0]),
                ha_high=float(self.data.ha_high[0]),
                ha_low=float(self.data.ha_low[0]),
                ha_close=float(self.data.ha_close[0]),
                stop=float(self.long_stop if direction == "BUY" else self.short_stop),
                tp=0.0,
                risk=float(self.risk),
            )
        )

    def _reset_flat_state(self) -> None:
        self.direction = 0
        self.entry_price = 0.0
        self.risk = 0.0
        self.long_stop = 0.0
        self.short_stop = 0.0
        self.long_followup_pending = False
        self.short_followup_pending = False
        self.partial_tp_done = False

    def _partial_close_units(self, pos_units: float, pct: float) -> float:
        """当前持仓盎司数 × pct%，再按 lot_step 手向下取整为盎司。"""
        step = float(self.p.lot_step)
        oz = float(self.p.oz_per_full_lot)
        raw = abs(float(pos_units)) * (float(pct) / 100.0)
        lots = raw / oz
        lots = math.floor(lots / step + 1e-12) * step
        if lots < step - 1e-12:
            return 0.0
        return float(lots * oz)

    def _maybe_partial_tp_after_r(self, *, is_long: bool) -> bool:
        """标准 K 极值达 partial_tp_r×初始 risk 后按比例减仓，不调止损；每笔仅一次。若已下出单则返回 True（调用方应 return）。"""
        if self.partial_tp_done or self.order or self.risk <= 1e-12:
            return False
        ep = float(self._csv_entry_px)
        if ep <= 0:
            return False
        r_mult = float(self.p.partial_tp_r)
        pct = max(1.0, min(100.0, float(self.p.partial_tp_pct)))
        px = float(self.data.close[0])
        if is_long:
            thr = ep + r_mult * float(self.risk)
            if float(self.data.high[0]) < thr:
                return False
            pos = float(self.position.size)
            if pos <= 1e-12:
                return False
            units = self._partial_close_units(pos, pct)
            self.partial_tp_done = True
            if units < float(self.p.lot_step) * float(self.p.oz_per_full_lot) - 1e-9:
                self._record_rule_event("PART_TP", "BUY", pos, thr, px)
                return False
            if units >= pos - 1e-9:
                self._csv_exit_reason = "分批止盈"
                self._record_rule_event("PART_TP", "BUY", pos, thr, px)
                self.order = self.close(coc=False)
            else:
                self._record_rule_event("PART_TP", "BUY", units, thr, px)
                self.order = self.sell(size=units, coc=False, tv_fill_price=px)
            return True
        thr = ep - r_mult * float(self.risk)
        if float(self.data.low[0]) > thr:
            return False
        pos = float(self.position.size)
        if pos >= -1e-12:
            return False
        apos = abs(pos)
        units = self._partial_close_units(apos, pct)
        self.partial_tp_done = True
        if units < float(self.p.lot_step) * float(self.p.oz_per_full_lot) - 1e-9:
            self._record_rule_event("PART_TP", "SELL", apos, thr, px)
            return False
        if units >= apos - 1e-9:
            self._csv_exit_reason = "分批止盈"
            self._record_rule_event("PART_TP", "SELL", apos, thr, px)
            self.order = self.close(coc=False)
        else:
            self._record_rule_event("PART_TP", "SELL", units, thr, px)
            self.order = self.buy(size=units, coc=False, tv_fill_price=px)
        return True

    def _try_flat_entry_next_open(self) -> None:
        """空仓：上一根收盘 CE+ZLSMA 条件满足则在本根标准 K 开盘价开仓（与 Pine / MT5 TryOpenOnNewBar 一致）。

        若上一段已下 full close，且回测器在同一节拍内已清空 `self.position`，可立刻评估新开；
        对应 MT5 EA 在 Manage/反手之后「只要无持仓就 TryOpen」的意图。
        """
        if self.order:
            return
        if self.position:
            return
        if len(self) < max(2 * ZLSMA_LEN, ZLSMA_LEN + 5, 22):
            return
        if not self._allow_new_entry_now():
            return

        c_prev = float(self.data.ha_close[-1])
        z_prev_raw = self.data.zlsma[-1]
        if np.isnan(z_prev_raw):
            return
        z_prev = float(z_prev_raw)
        sig_buy = bool(self.data.ce_buy[-1]) and c_prev > z_prev
        sig_sell = bool(self.data.ce_sell[-1]) and c_prev < z_prev

        std_o = float(self.data.open[0])
        std_c_prev = float(self.data.close[-1])
        next_ha_open_sig = (
            float(self.data.ha_open[-1]) + float(self.data.ha_close[-1])
        ) / 2.0

        self._reset_flat_state()

        if sig_buy:
            stop = self._near_low_prior()
            o_long_lot = (
                std_c_prev if std_c_prev > stop else next_ha_open_sig
            )
            if stop >= o_long_lot:
                return
            risk = o_long_lot - stop
            if risk <= 0:
                return
            units = self._size_units_for_stop_distance(risk)
            if units <= 0:
                return
            self.short_stop = 0.0
            self.long_followup_pending = False
            self.short_followup_pending = False
            self._csv_entry_reason = "CE买入+ZLSMA"
            self._csv_entry_units = float(units)
            self._csv_entry_dt = self.datetime.datetime()
            self._csv_entry_px = float(std_o)
            self._csv_exit_reason = ""
            self.direction = 1
            self.long_stop = stop
            self.risk = risk
            self.partial_tp_done = False
            eq = float(self.broker.getvalue())
            self._last_open_risk_cash = abs(std_o - stop) * units
            self._last_open_equity = max(eq, 1e-9)
            try:
                self._last_open_atr = float(self.data.atr14[0])
            except Exception:
                self._last_open_atr = float("nan")
            self._last_entry_is_long = True
            self._record_rule_event("ENTRY", "BUY", units, std_o, std_o)
            self.order = self.buy(
                size=units, coc=False, tv_fill_price=float(std_o)
            )
            return

        if sig_sell:
            stop = self._near_high_prior()
            o_short_lot = (
                std_c_prev if std_c_prev < stop else next_ha_open_sig
            )
            if stop <= o_short_lot:
                return
            risk = stop - o_short_lot
            if risk <= 0:
                return
            units = self._size_units_for_stop_distance(risk)
            if units <= 0:
                return
            self.long_stop = 0.0
            self.long_followup_pending = False
            self.short_followup_pending = False
            self._csv_entry_reason = "CE卖出+ZLSMA"
            self._csv_entry_units = float(units)
            self._csv_entry_dt = self.datetime.datetime()
            self._csv_entry_px = float(std_o)
            self._csv_exit_reason = ""
            self.direction = -1
            self.short_stop = stop
            self.risk = risk
            self.partial_tp_done = False
            eq = float(self.broker.getvalue())
            self._last_open_risk_cash = abs(stop - std_o) * units
            self._last_open_equity = max(eq, 1e-9)
            try:
                self._last_open_atr = float(self.data.atr14[0])
            except Exception:
                self._last_open_atr = float("nan")
            self._last_entry_is_long = False
            self._record_rule_event("ENTRY", "SELL", units, std_o, std_o)
            self.order = self.sell(
                size=units, coc=False, tv_fill_price=float(std_o)
            )

    def next_open(self):
        """上一根收盘确认信号；本根以 **标准 K 开盘价** 成交（Pine fill_orders_on_standard_ohlc）。

        反向 CE：仅 ceSell/ceBuy（不要求 ZLSMA）则本根开盘全平；若另满足 ZLSMA 与禁开则反手。
        """
        if self.order:
            return

        if len(self) < max(2 * ZLSMA_LEN, ZLSMA_LEN + 5, 22):
            return

        c_prev = float(self.data.ha_close[-1])
        z_prev_raw = self.data.zlsma[-1]
        ce_sell_only = bool(self.data.ce_sell[-1])
        ce_buy_only = bool(self.data.ce_buy[-1])

        std_o = float(self.data.open[0])
        std_c_prev = float(self.data.close[-1])
        next_ha_open_sig = (
            float(self.data.ha_open[-1]) + float(self.data.ha_close[-1])
        ) / 2.0

        if self.position:
            if self.position.size > 0 and ce_sell_only:
                if float(self.data.low[-1]) <= float(self.long_stop):
                    return
                zr = float(z_prev_raw)
                do_rev = (not np.isnan(zr)) and (c_prev < zr) and self._allow_new_entry_now()
                if do_rev:
                    stop = self._near_high_prior()
                    o_short_lot = (
                        std_c_prev if std_c_prev < stop else next_ha_open_sig
                    )
                    if stop <= o_short_lot:
                        self._csv_exit_reason = "CE反向离场"
                        self._record_rule_event(
                            "CE_EXIT", "BUY", abs(self.position.size), std_o, std_o
                        )
                        self.order = self.close(coc=False)
                        self._try_flat_entry_next_open()
                        return
                    risk = stop - o_short_lot
                    if risk <= 0:
                        self._csv_exit_reason = "CE反向离场"
                        self._record_rule_event(
                            "CE_EXIT", "BUY", abs(self.position.size), std_o, std_o
                        )
                        self.order = self.close(coc=False)
                        self._try_flat_entry_next_open()
                        return
                    units = self._size_units_for_stop_distance(risk)
                    if units <= 0:
                        self._csv_exit_reason = "CE反向离场"
                        self._record_rule_event(
                            "CE_EXIT", "BUY", abs(self.position.size), std_o, std_o
                        )
                        self.order = self.close(coc=False)
                        self._try_flat_entry_next_open()
                        return
                    close_sz = float(self.position.size)
                    self._csv_entry_reason = "反手空"
                    self._csv_entry_units = float(units)
                    self._csv_entry_dt = self.datetime.datetime()
                    self._csv_entry_px = float(std_o)
                    self._csv_exit_reason = ""
                    self.direction = -1
                    self.short_stop = stop
                    self.long_stop = 0.0
                    self.risk = risk
                    self.partial_tp_done = False
                    self.long_followup_pending = False
                    self.short_followup_pending = False
                    eq = float(self.broker.getvalue())
                    self._last_open_risk_cash = abs(stop - std_o) * units
                    self._last_open_equity = max(eq, 1e-9)
                    try:
                        self._last_open_atr = float(self.data.atr14[0])
                    except Exception:
                        self._last_open_atr = float("nan")
                    self._last_entry_is_long = False
                    self._record_rule_event("REV", "SELL", units, std_o, std_o)
                    self.order = self.sell(
                        size=close_sz + units, coc=False, tv_fill_price=float(std_o)
                    )
                    return
                self._csv_exit_reason = "CE反向离场"
                self._record_rule_event(
                    "CE_EXIT", "BUY", abs(self.position.size), std_o, std_o
                )
                self.order = self.close(coc=False)
                self._try_flat_entry_next_open()
                return

            if self.position.size < 0 and ce_buy_only:
                if float(self.data.high[-1]) >= float(self.short_stop):
                    return
                zr = float(z_prev_raw)
                do_rev = (not np.isnan(zr)) and (c_prev > zr) and self._allow_new_entry_now()
                if do_rev:
                    stop = self._near_low_prior()
                    o_long_lot = (
                        std_c_prev if std_c_prev > stop else next_ha_open_sig
                    )
                    if stop >= o_long_lot:
                        self._csv_exit_reason = "CE反向离场"
                        self._record_rule_event(
                            "CE_EXIT", "SELL", abs(self.position.size), std_o, std_o
                        )
                        self.order = self.close(coc=False)
                        self._try_flat_entry_next_open()
                        return
                    risk = o_long_lot - stop
                    if risk <= 0:
                        self._csv_exit_reason = "CE反向离场"
                        self._record_rule_event(
                            "CE_EXIT", "SELL", abs(self.position.size), std_o, std_o
                        )
                        self.order = self.close(coc=False)
                        self._try_flat_entry_next_open()
                        return
                    units = self._size_units_for_stop_distance(risk)
                    if units <= 0:
                        self._csv_exit_reason = "CE反向离场"
                        self._record_rule_event(
                            "CE_EXIT", "SELL", abs(self.position.size), std_o, std_o
                        )
                        self.order = self.close(coc=False)
                        self._try_flat_entry_next_open()
                        return
                    close_sz = float(abs(self.position.size))
                    self._csv_entry_reason = "反手多"
                    self._csv_entry_units = float(units)
                    self._csv_entry_dt = self.datetime.datetime()
                    self._csv_entry_px = float(std_o)
                    self._csv_exit_reason = ""
                    self.direction = 1
                    self.long_stop = stop
                    self.short_stop = 0.0
                    self.risk = risk
                    self.partial_tp_done = False
                    self.long_followup_pending = False
                    self.short_followup_pending = False
                    eq = float(self.broker.getvalue())
                    self._last_open_risk_cash = abs(std_o - stop) * units
                    self._last_open_equity = max(eq, 1e-9)
                    try:
                        self._last_open_atr = float(self.data.atr14[0])
                    except Exception:
                        self._last_open_atr = float("nan")
                    self._last_entry_is_long = True
                    self._record_rule_event("REV", "BUY", units, std_o, std_o)
                    self.order = self.buy(
                        size=close_sz + units, coc=False, tv_fill_price=float(std_o)
                    )
                    return
                self._csv_exit_reason = "CE反向离场"
                self._record_rule_event(
                    "CE_EXIT", "SELL", abs(self.position.size), std_o, std_o
                )
                self.order = self.close(coc=False)
                self._try_flat_entry_next_open()
                return

        self._try_flat_entry_next_open()

    def next(self):
        if self.order:
            return

        if not self.position:
            self._reset_flat_state()
            return

        if self.position.size > 0:
            self._manage_long()
        elif self.position.size < 0:
            self._manage_short()

    def _csv_exit_reason_for_long_stop(self) -> str:
        """触及 long_stop：初始止损或移动后的止损线。"""
        return "止损"

    def _csv_exit_reason_for_short_stop(self) -> str:
        return "止损"

    def _ha_two_bar_bear_run(self) -> bool:
        """当前与上一根 HA 均为阴（连续收阴）。"""
        return self._is_bearish() and float(self.data.ha_close[-1]) < float(
            self.data.ha_open[-1]
        )

    def _ha_two_bar_bull_run(self) -> bool:
        return self._is_bullish() and float(self.data.ha_close[-1]) > float(
            self.data.ha_open[-1]
        )

    def _manage_long(self):
        if self.entry_price <= 0:
            self.entry_price = self.position.price

        if self._three_bearish():
            cand = self._min_low3() - POINT_TRIPLE
            prev_stop = float(self.long_stop)
            self.long_stop = max(self.long_stop, cand)
            self.long_followup_pending = True
            if self.long_stop > prev_stop + 1e-12:
                self._record_rule_event(
                    "TRIPLE_STOP_SET", "BUY", self.position.size, self.long_stop, 0.0
                )

        if self._maybe_partial_tp_after_r(is_long=True):
            return

        if self.long_followup_pending:
            if self.data.low[0] <= self.long_stop:
                self.long_followup_pending = False
                self._csv_exit_reason = self._csv_exit_reason_for_long_stop()
                self._record_rule_event("STOP", "BUY", self.position.size, self.long_stop, self.long_stop)
                self.order = self.close(coc=False)
                return
            z_prev = float(self.data.zlsma[-1])
            z_cur = float(self.data.zlsma[0])
            z_ref = z_prev if not np.isnan(z_prev) else z_cur
            if np.isnan(z_ref):
                self.long_followup_pending = True
                return
            std_o = float(self.data.open[0])
            if std_o > z_ref:
                self.long_followup_pending = True
                return
            self.long_followup_pending = False
            if self._ha_two_bar_bear_run():
                self._csv_exit_reason = "三连后ZLS反向连续阴"
                px = float(self.data.close[0])
                self._record_rule_event("TRIP_ZLS", "BUY", self.position.size, px, px)
                self.order = self.close(coc=False)
                return
            return

        if self.data.low[0] <= self.long_stop:
            self._csv_exit_reason = self._csv_exit_reason_for_long_stop()
            self._record_rule_event("STOP", "BUY", self.position.size, self.long_stop, self.long_stop)
            self.order = self.close(coc=False)
            return

    def _manage_short(self):
        if self.entry_price <= 0:
            self.entry_price = self.position.price

        if self._three_bullish():
            cand = self._max_high3() + POINT_TRIPLE
            prev_stop = float(self.short_stop)
            self.short_stop = min(self.short_stop, cand)
            self.short_followup_pending = True
            if self.short_stop < prev_stop - 1e-12:
                self._record_rule_event(
                    "TRIPLE_STOP_SET", "SELL", self.position.size, self.short_stop, 0.0
                )

        if self._maybe_partial_tp_after_r(is_long=False):
            return

        if self.short_followup_pending:
            if self.data.high[0] >= self.short_stop:
                self.short_followup_pending = False
                self._csv_exit_reason = self._csv_exit_reason_for_short_stop()
                self._record_rule_event("STOP", "SELL", self.position.size, self.short_stop, self.short_stop)
                self.order = self.close(coc=False)
                return
            z_prev = float(self.data.zlsma[-1])
            z_cur = float(self.data.zlsma[0])
            z_ref = z_prev if not np.isnan(z_prev) else z_cur
            if np.isnan(z_ref):
                self.short_followup_pending = True
                return
            std_o = float(self.data.open[0])
            if std_o < z_ref:
                self.short_followup_pending = True
                return
            self.short_followup_pending = False
            if self._ha_two_bar_bull_run():
                self._csv_exit_reason = "三连后ZLS反向连续阳"
                px = float(self.data.close[0])
                self._record_rule_event("TRIP_ZLS", "SELL", self.position.size, px, px)
                self.order = self.close(coc=False)
                return
            return

        if self.data.high[0] >= self.short_stop:
            self._csv_exit_reason = self._csv_exit_reason_for_short_stop()
            self._record_rule_event("STOP", "SELL", self.position.size, self.short_stop, self.short_stop)
            self.order = self.close(coc=False)
            return


def _max_consecutive_runs(pnls: list[float]) -> tuple[int, int]:
    """返回 (最大连续盈利笔数, 最大连续亏损笔数)。"""
    best_w = best_l = cur_w = cur_l = 0
    for x in pnls:
        if x > 0:
            cur_w += 1
            cur_l = 0
            best_w = max(best_w, cur_w)
        elif x < 0:
            cur_l += 1
            cur_w = 0
            best_l = max(best_l, cur_l)
        else:
            cur_w = cur_l = 0
    return best_w, best_l


def _fmt_trade_review_dt(dt) -> str:
    """与手工复盘表一致：2026/4/30 13:02（月日不补零）。"""
    if dt is None:
        return ""
    try:
        if hasattr(dt, "year"):
            y, mo, d, h, mi = dt.year, dt.month, dt.day, dt.hour, dt.minute
        else:
            ts = pd.Timestamp(dt)
            y, mo, d, h, mi = ts.year, ts.month, ts.day, ts.hour, ts.minute
        return f"{y}/{mo}/{d} {h}:{mi:02d}"
    except Exception:
        return str(dt)


def write_trade_review_csv(
    strat: CEZLSMAStrategy,
    report_dir: str | Path,
    df: pd.DataFrame,
    symbol_display: str = "XAU/USD",
    replay_csv_name: str | None = None,
) -> Path:
    """写出 UTF-8-BOM 复盘 CSV：基础列与手工表一致，末尾多「平仓后权益」（整笔平仓后 broker 权益）；行按平仓时间降序。"""
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    end = df.index[-1]
    try:
        ts_end = pd.Timestamp(end)
        y, m, d = ts_end.year, ts_end.month, ts_end.day
    except Exception:
        y, m, d = 0, 0, 0
    if not replay_csv_name:
        replay_csv_name = f"交易复盘_{y}_{m}_{d}.csv"
    path = report_dir / replay_csv_name
    header = [
        "时间",
        "品种",
        "方向",
        "开仓价",
        "平仓价",
        "手数",
        "盈亏",
        "入场原因",
        "交易类型",
        "离场理由",
        "备注",
        "平仓后权益",
    ]
    rows = list(strat.closed_trades)

    def _sort_key(t: dict):
        ed = t.get("exit_dt")
        if ed is None:
            return pd.Timestamp.min
        try:
            return pd.Timestamp(ed)
        except Exception:
            return pd.Timestamp.min

    rows.sort(key=_sort_key, reverse=True)

    def _is_write_lock_error(exc: BaseException) -> bool:
        if isinstance(exc, PermissionError):
            return True
        if isinstance(exc, OSError) and getattr(exc, "errno", None) in (13, 32):
            return True
        return False

    def _iter_write_candidates(primary: Path):
        yield primary
        ts = time.strftime("%Y%m%d_%H%M%S")
        yield primary.with_name(f"{primary.stem}_{ts}{primary.suffix}")
        for i in range(2, 100):
            yield primary.with_name(f"{primary.stem}_n{i}{primary.suffix}")

    write_path: Path | None = None
    last_err: BaseException | None = None
    fp = None
    for candidate in _iter_write_candidates(path):
        try:
            fp = candidate.open("w", newline="", encoding="utf-8-sig")
            write_path = candidate
            break
        except OSError as e:
            if _is_write_lock_error(e):
                last_err = e
                continue
            raise
    if fp is None or write_path is None:
        raise PermissionError(
            f"无法写入复盘 CSV（目标可能被 Excel 等程序占用，请关闭后重试）: {path}"
        ) from last_err

    with fp:
        w = csv.writer(fp)
        w.writerow(header)
        for t in rows:
            exit_dt = t.get("exit_dt")
            is_long = bool(t.get("is_long"))
            entry_px = float(t.get("entry_px", 0.0) or 0.0)
            exit_px = float(t.get("exit_px", 0.0) or 0.0)
            lots = float(t.get("lots", 0.0) or 0.0)
            pnl = float(t.get("pnl", 0.0) or 0.0)
            eq_after = t.get("equity_after_trade")
            eq_cell = (
                f"{float(eq_after):.2f}"
                if eq_after is not None and math.isfinite(float(eq_after))
                else ""
            )
            w.writerow(
                [
                    _fmt_trade_review_dt(exit_dt),
                    symbol_display,
                    "做多" if is_long else "做空",
                    f"{entry_px:.2f}",
                    f"{exit_px:.2f}",
                    f"{lots:.2f}",
                    (
                        str(int(round(pnl)))
                        if abs(round(pnl, 2) - int(round(pnl))) < 1e-9
                        else f"{round(pnl, 2):.2f}"
                    ),
                    t.get("entry_reason") or "",
                    "",
                    t.get("exit_reason") or "",
                    "",
                    eq_cell,
                ]
            )
    if write_path.resolve() != path.resolve():
        print(
            f"[复盘] 原路径无法写入（通常因文件正被打开），已改用备用文件:\n"
            f"       {write_path}\n"
            f"       若需覆盖默认文件名，请先关闭: {path}"
        )
    print(f"[复盘] 已写 {write_path}（{len(rows)} 笔）")
    return write_path


def print_extended_performance_report(
    strat,
    initial_cash: float,
    df: pd.DataFrame,
    report_dir: Path,
    save_charts: bool,
) -> None:
    """打印扩展绩效指标并可选保存权益/回撤图。"""
    final_val = float(strat.broker.getvalue())
    pnl = final_val - initial_cash
    ret_pct = (pnl / initial_cash * 100.0) if initial_cash else 0.0

    span = df.index[-1] - df.index[0]
    days = max(span.days + span.seconds / 86400.0, 1e-6)
    years = days / 365.25
    ann = ((final_val / initial_cash) ** (1.0 / years) - 1.0) * 100.0 if initial_cash > 0 and years > 0 else 0.0

    trades = list(strat.closed_trades)
    n_tr = len(trades)
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] < 0]
    win_rate = (len(wins) / n_tr * 100.0) if n_tr else 0.0
    # 盈亏比（Profit factor）：盈利总额 / 亏损总额；亏损总额为各笔亏损绝对值之和（口径：每笔已平仓 pnlcomm）
    profit_total = sum(t["pnl"] for t in trades if t["pnl"] > 0.0)
    loss_total = sum(-t["pnl"] for t in trades if t["pnl"] < 0.0)
    win_loss_ratio = (
        (profit_total / loss_total)
        if loss_total > 1e-12
        else (float("inf") if profit_total > 0 else 0.0)
    )

    bars_list = [t["bars"] for t in trades if t["bars"] > 0]
    avg_bars = float(np.mean(bars_list)) if bars_list else 0.0
    bar_minutes = 5.0
    if len(df.index) > 1:
        bar_deltas = pd.Series(df.index).diff().dropna().dt.total_seconds() / 60.0
        positive_deltas = bar_deltas[bar_deltas > 0]
        if not positive_deltas.empty:
            bar_minutes = float(positive_deltas.median())
    avg_hold_min = avg_bars * bar_minutes

    pnls = [t["pnl"] for t in trades]
    max_streak_w, max_streak_l = _max_consecutive_runs(pnls)

    risks = [t["risk_pct"] for t in trades]
    avg_risk_pct = float(np.mean(risks)) if risks else 0.0
    max_risk_pct = float(np.max(risks)) if risks else 0.0

    long_tr = [t for t in trades if t["is_long"]]
    short_tr = [t for t in trades if not t["is_long"]]
    lw = [t for t in long_tr if t["pnl"] > 0]
    sw = [t for t in short_tr if t["pnl"] > 0]
    long_wr = (len(lw) / len(long_tr) * 100.0) if long_tr else 0.0
    short_wr = (len(sw) / len(short_tr) * 100.0) if short_tr else 0.0

    by_atr: dict[str, float] = {"低波动": 0.0, "中波动": 0.0, "高波动": 0.0, "N/A": 0.0}
    for t in trades:
        by_atr[t.get("atr_bucket", "N/A")] = by_atr.get(t.get("atr_bucket", "N/A"), 0.0) + t["pnl"]

    pnl_eu = sum(t["pnl"] for t in trades if t["in_europe"])
    pnl_ny = sum(t["pnl"] for t in trades if t["in_newyork"])
    pnl_both = sum(t["pnl"] for t in trades if t["in_europe"] and t["in_newyork"])
    pnl_other = sum(t["pnl"] for t in trades if not t["in_europe"] and not t["in_newyork"])

    eq_an = strat.analyzers.eqcurve
    eq = np.array(eq_an.equity, dtype=float)
    peak = np.maximum.accumulate(eq)
    dd_series = (eq - peak) / np.maximum(peak, 1e-12)
    max_dd_pct = float(dd_series.min() * 100.0) if len(eq) else 0.0

    bar_ret = np.diff(eq) / np.maximum(eq[:-1], 1e-12) if len(eq) > 1 else np.array([])
    bars_per_year = len(eq) / max(years, 1e-9)
    sharpe = (
        (np.mean(bar_ret) / (np.std(bar_ret) + 1e-12)) * math.sqrt(bars_per_year)
        if len(bar_ret) > 2
        else 0.0
    )

    try:
        dd_bt = strat.analyzers.drawdown.get_analysis()
        max_dd_bt = float(dd_bt.get("max", {}).get("drawdown", max_dd_pct))
    except Exception:
        max_dd_bt = max_dd_pct

    print("\n========== 完整回测绩效 ==========")
    print(f"1. 总盈亏: {pnl:,.2f}  |  总收益率: {ret_pct:.2f}%")
    print(f"2. 年化收益率: {ann:.2f}%  （按样本跨度 {days:.1f} 天 ≈ {years:.3f} 年复利折算）")
    print(f"3. 最大回撤: {max_dd_pct:.2f}% （权益曲线） / 分析器 max: {max_dd_bt:.2f}%")
    print(f"4. 夏普比率(近似): {sharpe:.3f}  （按 {bar_minutes:g}m 收益序列年化，无风险利率=0）")
    print(f"5. 胜率: {win_rate:.2f}%  ({len(wins)}/{n_tr})")
    print(
        f"6. 盈亏比: {win_loss_ratio:.3f}  = 盈利总额 {profit_total:,.2f} ÷ 亏损总额 {loss_total:,.2f} "
        f"（已平仓每笔含手续费 pnlcomm；持平笔不计入分子分母）"
    )
    print(f"7. 交易次数(已平仓完整笔): {n_tr}")
    print(
        "    （每笔=从开仓到完全平仓计 1 笔；仅在策略信号出现时下单，故通常远小于样本内 K 线根数。）"
    )
    print(f"8. 平均持仓时间: {avg_hold_min:.1f} 分钟  (约 {avg_bars:.1f} 根{bar_minutes:g}m K线)")
    print(f"9. 最大连续盈利笔数: {max_streak_w}  |  最大连续亏损笔数: {max_streak_l}")
    try:
        ta_bt = strat.analyzers.trades.get_analysis()
        st = ta_bt.get("streak", {})
        w_bt = st.get("won", {}).get("longest", None)
        l_bt = st.get("lost", {}).get("longest", None)
        if w_bt is not None or l_bt is not None:
            print(f"    (Backtrader TradeAnalyzer 连续赢/亏最长: {w_bt} / {l_bt})")
    except Exception:
        pass
    print(f"10. 单笔风险占比(开仓时): 平均 {avg_risk_pct:.3f}%  | 最大 {max_risk_pct:.3f}%  (|止损距离|×手数/当时权益；目标≈{strat.p.risk_per_trade*100:.1f}%，手数取整后略低)")
    print(
        f"11. 方向胜率 — 多: {long_wr:.2f}% ({len(lw)}/{len(long_tr)})  "
        f"| 空: {short_wr:.2f}% ({len(sw)}/{len(short_tr)})"
    )
    print("12. ATR14(开仓时) 三分位盈亏 — ", end="")
    print(
        " | ".join(f"{k}: {v:,.2f}" for k, v in by_atr.items() if k in ("低波动", "中波动", "高波动", "N/A"))
    )
    print(
        f"13. 时段盈亏(按平仓时刻小时; 欧{EUROPE_SESSION_HOURS} 纽{NEWYORK_SESSION_HOURS}，可重叠): "
        f"欧洲 {pnl_eu:,.2f} | 纽约 {pnl_ny:,.2f} | 重叠 {pnl_both:,.2f} | 其他 {pnl_other:,.2f}"
    )
    print("==================================\n")

    trade_eq = getattr(strat, "equity_on_trade_close", None) or []
    if save_charts and len(trade_eq) > 1:
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            report_dir.mkdir(parents=True, exist_ok=True)
            fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
            x = np.array([t[0] for t in trade_eq], dtype=float)
            eq_t = np.array([t[1] for t in trade_eq], dtype=float)
            peak_t = np.maximum.accumulate(eq_t)
            dd_t = (eq_t - peak_t) / np.maximum(peak_t, 1e-12)
            axes[0].plot(x, eq_t, color="tab:blue", linewidth=0.8)
            axes[0].set_ylabel("Equity")
            axes[0].set_title("Equity after each closed trade")
            axes[0].grid(True, alpha=0.3)

            axes[1].fill_between(x, dd_t * 100.0, 0.0, color="tab:red", alpha=0.35)
            axes[1].plot(x, dd_t * 100.0, color="darkred", linewidth=0.7)
            axes[1].set_ylabel("Drawdown %")
            axes[1].set_xlabel("Closed trade # (1-based)")
            axes[1].set_title("Drawdown from running peak (sampled at trade close)")
            axes[1].grid(True, alpha=0.3)
            plt.tight_layout()
            out = report_dir / "ce_zlsma_equity_drawdown.png"
            fig.savefig(out, dpi=120)
            plt.close(fig)
            print(f"[图表] 已保存: {out.resolve()}")
        except Exception as e:
            print(f"[图表] 未生成（需安装 matplotlib 或出错）: {e}", file=sys.stderr)
    elif save_charts and len(eq) > 1:
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            report_dir.mkdir(parents=True, exist_ok=True)
            fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
            x = np.arange(len(eq))
            axes[0].plot(x, eq, color="tab:blue", linewidth=0.8)
            axes[0].set_ylabel("Equity")
            axes[0].set_title("Equity vs bar index")
            axes[0].grid(True, alpha=0.3)

            axes[1].fill_between(x, dd_series * 100.0, 0.0, color="tab:red", alpha=0.35)
            axes[1].plot(x, dd_series * 100.0, color="darkred", linewidth=0.7)
            axes[1].set_ylabel("Drawdown %")
            axes[1].set_xlabel("Bar index")
            axes[1].set_title("Drawdown from running peak")
            axes[1].grid(True, alpha=0.3)
            plt.tight_layout()
            out = report_dir / "ce_zlsma_equity_drawdown.png"
            fig.savefig(out, dpi=120)
            plt.close(fig)
            print(f"[图表] 已保存: {out.resolve()}")
        except Exception as e:
            print(f"[图表] 未生成（需安装 matplotlib 或出错）: {e}", file=sys.stderr)


def install_dynamic_spread_slippage(br, slip_perc: float, default_half_spread: float) -> None:
    """成交价：买价更差 = price*(1+perc)+half，卖价更差 = price*(1-perc)-half；
    half 取当前订单 data 的 `half_spread_price[0]`（在 `_try_exec` 内按 bar 设置），无则回退 default。"""
    from backtrader.brokers.bbroker import BackBroker

    br.p.slip_perc = slip_perc
    br.p.slip_fixed = 0.0

    _orig_try_exec = BackBroker._try_exec

    def _try_exec_dyn(self, order):
        try:
            self._exec_half_spread = float(order.data.half_spread_price[0])
        except Exception:
            self._exec_half_spread = float(default_half_spread)
        try:
            return _orig_try_exec(self, order)
        finally:
            self._exec_half_spread = None

    def _slip_up(self, pmax, price, doslip=True, lim=False):
        if not doslip:
            return price
        pp = self.p
        half = float(getattr(self, "_exec_half_spread", default_half_spread))
        pslip = price * (1.0 + pp.slip_perc) + half
        if pslip <= pmax:
            return pslip
        if pp.slip_match or (lim and pp.slip_limit):
            if not pp.slip_out:
                return pmax
            return pslip
        return None

    def _slip_down(self, pmin, price, doslip=True, lim=False):
        if not doslip:
            return price
        pp = self.p
        half = float(getattr(self, "_exec_half_spread", default_half_spread))
        pslip = price * (1.0 - pp.slip_perc) - half
        if pslip >= pmin:
            return pslip
        if pp.slip_match or (lim and pp.slip_limit):
            if not pp.slip_out:
                return pmin
            return pslip
        return None

    br._try_exec = types.MethodType(_try_exec_dyn, br)
    br._slip_up = types.MethodType(_slip_up, br)
    br._slip_down = types.MethodType(_slip_down, br)


def install_tv_market_price_fills(br) -> None:
    """让带 `tv_fill_price` 的开仓市价单按规则价在当前 bar 成交。

    仅用于入场：`next_open` 按当前标准 K `open` 传 `tv_fill_price`。
    STOP/FOLLOWUP 平仓用 `close(coc=False)` 无 `tv_fill_price`，走默认市价逻辑（下一根开盘等）。

    条件：经纪商 `cheat_on_close=True`（本脚本 `run_backtest` 已 `set_coc(True)`）。
    """
    from backtrader.brokers.bbroker import BackBroker

    _orig_try_exec_market = BackBroker._try_exec_market

    def _try_exec_market_tv(self, order, popen, phigh, plow):
        tv_price = order.info.get("tv_fill_price", None)
        if tv_price is not None and self.p.coc:
            self._execute(
                order,
                ago=0,
                price=float(tv_price),
                dtcoc=order.created.dt,
            )
            return
        return _orig_try_exec_market(self, order, popen, phigh, plow)

    br._try_exec_market = types.MethodType(_try_exec_market_tv, br)


def _margin_cash_per_unit_oz(
    margin_per_001_lot: float, lot_step: float, oz_per_full_lot: float
) -> float:
    """头寸 size 为「盎司」时，每 1 盎司冻结的保证金（账户货币）。"""
    return margin_per_001_lot / (lot_step * oz_per_full_lot)


def run_backtest(
    symbol: str = "XAUUSD=X",
    period: str = "60d",
    interval: str = "5m",
    csv_path: str | None = None,
    demo: bool = False,
    cash: float = 10_000.0,
    margin_per_001_lot: float = 200.0,
    lot_step: float = 0.01,
    oz_per_full_lot: float = 100.0,
    risk_per_trade: float = 0.02,
    csv_tz: str | None = None,
    csv_cn_offset_hours: float = 0.0,
    csv_assume_wallclock_tz: str | None = None,
    no_entry_sessions: bool = True,
    max_lots: float = 0.0,
    plot: bool = False,
    report_dir: str | Path = ".",
    no_charts: bool = False,
    write_replay_csv: bool = True,
    replay_symbol: str = "XAU/USD",
    replay_csv_name: str | None = None,
    zlsma_formula: str = "veryfid",
    ce_use_close_for_extremes: bool = CE_USE_CLOSE_FOR_EXTREMES,
    zlsma_linreg_offset: int = 0,
    ha_first_open_mode: str = HA_FIRST_OPEN_MODE,
    partial_tp_r: float = PARTIAL_TP_R,
    partial_tp_pct: float = PARTIAL_TP_PCT,
):
    df = load_price_data(
        symbol,
        period,
        interval,
        csv_path,
        demo=demo,
        csv_tz=csv_tz,
        csv_cn_offset_hours=csv_cn_offset_hours,
        csv_assume_wallclock_tz=csv_assume_wallclock_tz,
        no_entry_sessions=no_entry_sessions,
        zlsma_formula=zlsma_formula,
        ce_use_close_for_extremes=ce_use_close_for_extremes,
        zlsma_linreg_offset=zlsma_linreg_offset,
        ha_first_open_mode=ha_first_open_mode,
    )
    if df.empty:
        raise SystemExit("价格数据为空")

    if csv_path:
        span = df.index[-1] - df.index[0]
        print(
            f"[数据] 已读 CSV → Heikin Ashi 后 K 线数={len(df)}，"
            f"时间 {df.index[0]} — {df.index[-1]}（约 {span.days} 天），"
            f"标准K Close 区间 [{df['Close'].min():.2f}, {df['Close'].max():.2f}]"
        )
    ce_ext_note = (
        "极值在 close（Pine useClose=true）"
        if ce_use_close_for_extremes
        else "极值在 high/low（Pine useClose=false）"
    )
    ha_open_note = (
        "HA 首根 Open=(O+C)/2（TV）"
        if ha_first_open_mode == HA_FIRST_OPEN_TV
        else "HA 首根 Open=普通 Open（Heikin-Ashi backtest.py）"
    )
    print(
        f"[指标] ZLSMA 公式={zlsma_formula!r}，linreg offset={zlsma_linreg_offset}（veryfid Pine 默认 0）；"
        f" CE：`atr=mult*ta.atr(len)` 当根；{ce_ext_note}；{ha_open_note}。"
    )
    print(
        f"[风控] 每笔目标风险={risk_per_trade*100:.2f}% 权益；手数=该风险额/|开仓价-初始止损|，"
        f"按 {lot_step} 手向下取整；初始止损=近{STRATEGY_RISK_LOOKBACK}根(不含当根)HA low/high 极值；"
        f"分批止盈：标准 K 极值达 {partial_tp_r:g}×初始风险价距时按 {partial_tp_pct:g}% 减仓（不调止损）；"
        f"每整手 {oz_per_full_lot} 盎司。"
        + (f" 单手数上限≤{max_lots:g} 手。" if max_lots and max_lots > 0 else ""),
    )
    print(
        "[成交] TV严格规则：上一根收盘确认信号→当前根标准K开盘价入场（tv_fill_price）；"
        "止损触价用标准K high/low；STOP/FOLLOWUP 触发后市价平仓（无 tv_fill_price，"
        "与 Pine strategy.close 一致，默认下一根标准K开盘等撮合）；不额外叠加点差/滑点。"
    )

    data = HABTData(dataname=df)
    _at = df["atr14"].dropna()
    q33 = float(_at.quantile(0.33)) if len(_at) > 20 else 0.0
    q66 = float(_at.quantile(0.66)) if len(_at) > 20 else 0.0

    cerebro = bt.Cerebro(cheat_on_open=True)
    cerebro.adddata(data)
    cerebro.addstrategy(
        CEZLSMAStrategy,
        margin_per_001_lot=margin_per_001_lot,
        lot_step=lot_step,
        oz_per_full_lot=oz_per_full_lot,
        risk_per_trade=risk_per_trade,
        max_lots=max_lots,
        atr_q33=q33,
        atr_q66=q66,
        partial_tp_r=partial_tp_r,
        partial_tp_pct=partial_tp_pct,
    )
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(EquityCurveAnalyzer, _name="eqcurve")
    cerebro.broker.setcash(cash)
    cerebro.broker.set_coc(True)
    cerebro.broker.set_coo(True)
    cerebro.broker.set_shortcash(True)
    m_oz = _margin_cash_per_unit_oz(margin_per_001_lot, lot_step, oz_per_full_lot)
    cerebro.broker.setcommission(
        commission=0.0,
        margin=m_oz,
        commtype=bt.CommInfoBase.COMM_FIXED,
        stocklike=False,
    )
    install_tv_market_price_fills(cerebro.broker)

    results = cerebro.run()
    strat = results[0]

    print(f"初始资金: {cash:.2f}")
    print(f"期末权益: {cerebro.broker.getvalue():.2f}")

    print_extended_performance_report(
        strat,
        cash,
        df,
        Path(report_dir),
        save_charts=not no_charts,
    )

    if write_replay_csv:
        write_trade_review_csv(
            strat,
            Path(report_dir),
            df,
            symbol_display=replay_symbol,
            replay_csv_name=replay_csv_name,
        )

    if plot:
        cerebro.plot(style="candlestick")


def main():
    ap = argparse.ArgumentParser(description="CE + ZLSMA XAUUSD 回测 (Backtrader)")
    ap.add_argument("--symbol", default="XAUUSD=X", help="yfinance 代码")
    ap.add_argument("--period", default="60d", help="yfinance intraday 通常最长约 60d")
    ap.add_argument("--interval", default="5m")
    ap.add_argument("--csv", default=None, help="本地 CSV（含 OHLCV）")
    ap.add_argument(
        "--disable-no-entry-sessions",
        action="store_true",
        help="关闭两段禁开（默认：上海 04:00–06:30、15:00–21:45 内禁止新开仓，与 Pine 一致）",
    )
    ap.add_argument(
        "--csv-tz",
        default=None,
        metavar="IANA",
        help="CSV 无时区时先 localize 到此区再转上海判时段；勿与 --csv-assume-timezone 同用。若与固定 +H 并用，仍以 +H 优先，需纯 IANA 换算时请设 --csv-cn-offset-hours 0",
    )
    ap.add_argument(
        "--csv-cn-offset-hours",
        type=float,
        default=0.0,
        metavar="H",
        help=(
            "无时区 CSV：整根时间戳先加 H 小时，再按上海墙钟判禁开时段（默认 0；"
            "MT5 常见对齐上海用 5，请在命令行显式传入）。"
            "索引已带时区（如 yfinance）时本参数不生效，改为转上海取钟点。"
            "与 --csv-assume-timezone 互斥；配合 --csv-tz 时请视情况设为 0。"
        ),
    )
    ap.add_argument(
        "--csv-assume-timezone",
        default=None,
        metavar="IANA",
        help=(
            "无时区 CSV：整根时间戳视为该 IANA 墙钟，再转 Asia/Shanghai 判禁开时段。"
            "与固定 +H 二选一，一般 MT5 不必用。"
        ),
    )
    ap.add_argument("--demo", action="store_true", help="使用内置随机数据自检（不联网）")
    ap.add_argument("--cash", type=float, default=10000.0)
    ap.add_argument("--margin-per-001-lot", type=float, default=200.0, help="每 0.01 手占用保证金（仅经纪商冻结与缩仓上限）")
    ap.add_argument("--lot-step", type=float, default=0.01, help="最小手数步长")
    ap.add_argument("--oz-per-full-lot", type=float, default=100.0, help="1 标准手对应标的数量（默认 100 盎司）")
    ap.add_argument(
        "--risk-pct",
        type=float,
        default=2.0,
        help="每笔目标风险占当前权益的百分比（默认 2，用于按止损距离算手数）",
    )
    ap.add_argument(
        "--partial-tp-r",
        type=float,
        default=PARTIAL_TP_R,
        metavar="R",
        help="分批止盈：标准 K 极值相对开仓价达到 R×开仓时冻结的初始风险价距时触发（默认 1.5，与 Pine PARTIAL_TP_R 一致）",
    )
    ap.add_argument(
        "--partial-tp-pct",
        type=float,
        default=PARTIAL_TP_PCT,
        metavar="PCT",
        help="分批止盈：平掉当前持仓的百分比 1–100（默认 50；与 Pine PARTIAL_TP_PCT 一致）",
    )
    ap.add_argument(
        "--max-lots",
        type=float,
        default=0.0,
        metavar="L",
        help="开仓单手数上限，0 表示不限制（按 lot_step 向下取整到网格，例 1=最多 1.00 手）",
    )
    ap.add_argument("--report-dir", default=".", help="绩效报告与图片输出目录")
    ap.add_argument("--no-charts", action="store_true", help="不生成权益/回撤 PNG")
    ap.add_argument(
        "--plot",
        action="store_true",
        help="回测结束后调用 cerebro.plot（需本机图形界面，默认关闭）",
    )
    ap.add_argument(
        "--no-replay-csv",
        action="store_true",
        help="不生成交易复盘 CSV（与 交易复盘_*.csv 同列）",
    )
    ap.add_argument(
        "--replay-symbol",
        default="XAU/USD",
        help="复盘 CSV「品种」列显示名",
    )
    ap.add_argument(
        "--replay-csv-name",
        default=None,
        metavar="FILE.csv",
        help="复盘 CSV 文件名（默认 交易复盘_样本末日_Y_M_D.csv）",
    )
    ap.add_argument(
        "--zlsma-formula",
        choices=("veryfid", "gamma"),
        default="veryfid",
        help="ZLSMA：veryfid=TV @veryfid（2*LSMA-linreg(LSMA)）；gamma=旧版 lsma+(src-lsma)*2/(len+1)",
    )
    ap.add_argument(
        "--zlsma-linreg-offset",
        type=int,
        default=0,
        metavar="N",
        help="veryfid ZLSMA 中 linreg(..., offset) 的偏移，默认 0（与原版指标一致）；建议 0..length-1",
    )
    ap.add_argument(
        "--ce-extremes-from-high-low",
        action="store_true",
        help="CE 极值用 highest(high)/lowest(low)（everget Pine useClose=false）；默认用 close",
    )
    ap.add_argument(
        "--ha-first-open",
        choices=(HA_FIRST_OPEN_TV, HA_FIRST_OPEN_LEGACY_OPEN0),
        default=HA_FIRST_OPEN_TV,
        metavar="MODE",
        help="HA 首根开盘价：tv=(O+C)/2 对齐 TradingView；legacy_open0=普通 Open[0] 对齐 d:\\Heikin-Ashi backtest.py",
    )
    args = ap.parse_args()
    run_backtest(
        symbol=args.symbol,
        period=args.period,
        interval=args.interval,
        csv_path=args.csv,
        demo=args.demo,
        cash=args.cash,
        margin_per_001_lot=args.margin_per_001_lot,
        lot_step=args.lot_step,
        oz_per_full_lot=args.oz_per_full_lot,
        risk_per_trade=args.risk_pct / 100.0,
        csv_tz=args.csv_tz,
        csv_cn_offset_hours=args.csv_cn_offset_hours,
        csv_assume_wallclock_tz=args.csv_assume_timezone,
        no_entry_sessions=not args.disable_no_entry_sessions,
        max_lots=args.max_lots,
        plot=args.plot,
        report_dir=args.report_dir,
        no_charts=args.no_charts,
        write_replay_csv=not args.no_replay_csv,
        replay_symbol=args.replay_symbol,
        replay_csv_name=args.replay_csv_name,
        zlsma_formula=args.zlsma_formula,
        ce_use_close_for_extremes=not args.ce_extremes_from_high_low,
        zlsma_linreg_offset=max(0, args.zlsma_linreg_offset),
        ha_first_open_mode=args.ha_first_open,
        partial_tp_r=args.partial_tp_r,
        partial_tp_pct=args.partial_tp_pct,
    )


if __name__ == "__main__":
    main()
