"""
==================================================================
BINARY / OTC TRADING SIGNAL ENGINE
==================================================================
Real (non-demo) implementations of:
  1. Trend / Moving-Average strategies
  2. RSI + EMA + Bollinger Bands price-action strategy
  3. Volatility market filters (normal + strong)
  4. Trend "flow" (majority-vote) strategy
  5. Doji market filter
  6. Big-candle market filter
  7. High-volume market filter
  8. Final combined BUY / PUT signal generator

Input format
------------
All functions expect a pandas DataFrame `df` with columns:
    'open', 'high', 'low', 'close'   (required)
    'volume'                          (optional, needed only for volume filter)
Index should be time-ordered (oldest -> newest row).

Usage
-----
    signal = generate_final_signal(df)
    print(signal)

No external TA library is required — everything is built with
pandas + numpy only, so it runs anywhere.
==================================================================
"""

import numpy as np
import pandas as pd


# ==================================================================
# 0. CORE INDICATOR HELPERS
# ==================================================================

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50)


def bollinger_bands(series: pd.Series, period: int = 20, std_mult: float = 2.0):
    mid = sma(series, period)
    std = series.rolling(period).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    return upper, mid, lower


def true_range(df: pd.DataFrame) -> pd.Series:
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    return pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tr = true_range(df)
    return tr.ewm(alpha=1 / period, min_periods=period).mean()


def _last(series: pd.Series, default=np.nan):
    s = series.dropna()
    return s.iloc[-1] if len(s) else default


def _prev(series: pd.Series, default=np.nan):
    s = series.dropna()
    return s.iloc[-2] if len(s) > 1 else default


# ==================================================================
# 1. TREND / MOVING-AVERAGE STRATEGIES  (real logic)
# ==================================================================

def ema_crossover_strategy(data: pd.DataFrame, fast=9, slow=21) -> str:
    """EMA Crossover Strategy"""
    f, s = ema(data['close'], fast), ema(data['close'], slow)
    if _prev(f) <= _prev(s) and _last(f) > _last(s):
        return "BUY"
    if _prev(f) >= _prev(s) and _last(f) < _last(s):
        return "PUT"
    return "HOLD"


def sma_crossover_strategy(data: pd.DataFrame, fast=10, slow=30) -> str:
    """SMA Crossover Strategy"""
    f, s = sma(data['close'], fast), sma(data['close'], slow)
    if _prev(f) <= _prev(s) and _last(f) > _last(s):
        return "BUY"
    if _prev(f) >= _prev(s) and _last(f) < _last(s):
        return "PUT"
    return "HOLD"


def golden_cross_strategy(data: pd.DataFrame, fast=50, slow=200) -> str:
    """Golden Cross Strategy (bullish cross only)"""
    f, s = sma(data['close'], fast), sma(data['close'], slow)
    if _prev(f) <= _prev(s) and _last(f) > _last(s):
        return "BUY"
    return "HOLD"


def death_cross_strategy(data: pd.DataFrame, fast=50, slow=200) -> str:
    """Death Cross Strategy (bearish cross only)"""
    f, s = sma(data['close'], fast), sma(data['close'], slow)
    if _prev(f) >= _prev(s) and _last(f) < _last(s):
        return "PUT"
    return "HOLD"


def triple_ema_strategy(data: pd.DataFrame, e1=5, e2=10, e3=20) -> str:
    """Triple EMA Strategy (stacked EMAs = trend direction)"""
    a, b, c = ema(data['close'], e1), ema(data['close'], e2), ema(data['close'], e3)
    if _last(a) > _last(b) > _last(c):
        return "BUY"
    if _last(a) < _last(b) < _last(c):
        return "PUT"
    return "HOLD"


def supertrend_strategy(data: pd.DataFrame, period=10, multiplier=3) -> str:
    """Supertrend Strategy"""
    line, direction = _supertrend(data, period, multiplier)
    d = _last(direction, 0)
    if d == 1:
        return "BUY"
    if d == -1:
        return "PUT"
    return "HOLD"


def _supertrend(df, period=10, multiplier=3):
    hl2 = (df['high'] + df['low']) / 2
    a = atr(df, period)
    upper = hl2 + multiplier * a
    lower = hl2 - multiplier * a
    final_upper = upper.copy()
    final_lower = lower.copy()
    direction = pd.Series(1, index=df.index)
    line = pd.Series(index=df.index, dtype=float)

    for i in range(1, len(df)):
        if df['close'].iloc[i - 1] > final_upper.iloc[i - 1]:
            direction.iloc[i] = 1
        elif df['close'].iloc[i - 1] < final_lower.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]
            if direction.iloc[i] == 1 and lower.iloc[i] < final_lower.iloc[i - 1]:
                final_lower.iloc[i] = final_lower.iloc[i - 1]
            if direction.iloc[i] == -1 and upper.iloc[i] > final_upper.iloc[i - 1]:
                final_upper.iloc[i] = final_upper.iloc[i - 1]
        line.iloc[i] = final_lower.iloc[i] if direction.iloc[i] == 1 else final_upper.iloc[i]

    return line, direction


def parabolic_sar_strategy(data: pd.DataFrame, af_step=0.02, af_max=0.2) -> str:
    """Parabolic SAR Strategy"""
    psar, bull_now, bull_prev = _parabolic_sar(data, af_step, af_max)
    if bull_now and not bull_prev:
        return "BUY"
    if (not bull_now) and bull_prev:
        return "PUT"
    return "HOLD"


def _parabolic_sar(df, af_step=0.02, af_max=0.2):
    high, low, close = df['high'].values, df['low'].values, df['close'].values
    n = len(df)
    psar = close.copy().astype(float)
    bull_hist = np.ones(n, dtype=bool)
    if n < 3:
        return pd.Series(psar, index=df.index), True, True

    bull = True
    af = af_step
    ep = high[0]
    hp, lp = high[0], low[0]

    for i in range(2, n):
        psar[i] = psar[i - 1] + af * ((hp if bull else lp) - psar[i - 1])
        reverse = False
        if bull:
            if low[i] < psar[i]:
                bull, reverse = False, True
                psar[i] = hp
                lp = low[i]
                af = af_step
        else:
            if high[i] > psar[i]:
                bull, reverse = True, True
                psar[i] = lp
                hp = high[i]
                af = af_step
        if not reverse:
            if bull:
                if high[i] > hp:
                    hp = high[i]
                    af = min(af + af_step, af_max)
                psar[i] = min(psar[i], low[i - 1], low[i - 2])
            else:
                if low[i] < lp:
                    lp = low[i]
                    af = min(af + af_step, af_max)
                psar[i] = max(psar[i], high[i - 1], high[i - 2])
        bull_hist[i] = bull

    return pd.Series(psar, index=df.index), bull_hist[-1], bull_hist[-2]


def donchian_trend_strategy(data: pd.DataFrame, period=20) -> str:
    """Donchian Trend Strategy (channel breakout)"""
    upper = data['high'].rolling(period).max()
    lower = data['low'].rolling(period).min()
    close = data['close']
    if _last(close) >= _last(upper):
        return "BUY"
    if _last(close) <= _last(lower):
        return "PUT"
    return "HOLD"


def ichimoku_cloud_strategy(data: pd.DataFrame, conv=9, base=26, span_b_p=52, disp=26) -> str:
    """Ichimoku Cloud Strategy"""
    conv_line = (data['high'].rolling(conv).max() + data['low'].rolling(conv).min()) / 2
    base_line = (data['high'].rolling(base).max() + data['low'].rolling(base).min()) / 2
    span_a = ((conv_line + base_line) / 2).shift(disp)
    span_b = ((data['high'].rolling(span_b_p).max() + data['low'].rolling(span_b_p).min()) / 2).shift(disp)

    price = _last(data['close'])
    top_cloud = max(_last(span_a, -np.inf), _last(span_b, -np.inf))
    bottom_cloud = min(_last(span_a, np.inf), _last(span_b, np.inf))

    if price > top_cloud and _last(conv_line) > _last(base_line):
        return "BUY"
    if price < bottom_cloud and _last(conv_line) < _last(base_line):
        return "PUT"
    return "HOLD"


def alligator_strategy(data: pd.DataFrame, jaw=13, teeth=8, lips=5,
                        jaw_shift=8, teeth_shift=5, lips_shift=3) -> str:
    """Williams Alligator Strategy"""
    median = (data['high'] + data['low']) / 2
    jaw_l = median.rolling(jaw).mean().shift(jaw_shift)
    teeth_l = median.rolling(teeth).mean().shift(teeth_shift)
    lips_l = median.rolling(lips).mean().shift(lips_shift)

    j, t, l, price = _last(jaw_l), _last(teeth_l), _last(lips_l), _last(data['close'])
    if l > t > j and price > l:
        return "BUY"          # alligator "awake", trending up
    if l < t < j and price < l:
        return "PUT"           # alligator "awake", trending down
    return "HOLD"               # alligator "sleeping" / choppy


# ==================================================================
# 2. RSI + EMA + BOLLINGER BANDS  PRICE-ACTION SIGNAL
# ==================================================================

def rsi_ema_bb_price_action_signal(data: pd.DataFrame, rsi_period=14,
                                    ema_trend=50, bb_period=20, bb_std=2.0) -> str:
    """
    Combines RSI (momentum), EMA (trend filter) and Bollinger Bands
    (price extension) for a mean-reversion price-action signal —
    ideal for short-expiry binary/OTC trades.
    """
    close = data['close']
    r = rsi(close, rsi_period)
    trend = ema(close, ema_trend)
    upper, mid, lower = bollinger_bands(close, bb_period, bb_std)

    price = _last(close)
    r_val = _last(r)
    trend_val = _last(trend)

    oversold = r_val <= 30 and price <= _last(lower)
    overbought = r_val >= 70 and price >= _last(upper)

    if oversold and price > trend_val * 0.995:   # not in a hard downtrend
        return "BUY"
    if overbought and price < trend_val * 1.005:  # not in a hard uptrend
        return "PUT"
    return "HOLD"


# ==================================================================
# 3. VOLATILITY MARKET FILTERS
# ==================================================================

def volatility_filter(data: pd.DataFrame, period=14, min_atr_pct=0.05) -> bool:
    """
    Basic volatility filter.
    Returns True  -> market has ENOUGH volatility to trade
    Returns False -> market too flat/quiet (avoid trading, common OTC trap)
    min_atr_pct is ATR as % of price (e.g. 0.05 = 0.05%).
    """
    a = atr(data, period)
    price = _last(data['close'])
    atr_pct = (_last(a) / price) * 100 if price else 0
    return atr_pct >= min_atr_pct


def strong_volatility_filter(data: pd.DataFrame, period=14, bb_period=20,
                              bb_std=2.0, lookback=20) -> str:
    """
    Rates current volatility strength using ATR trend + Bollinger Band
    width expansion.
    Returns: "STRONG", "NORMAL", or "WEAK"
    """
    a = atr(data, period)
    upper, mid, lower = bollinger_bands(data['close'], bb_period, bb_std)
    bb_width = (upper - lower) / mid

    atr_now, atr_avg = _last(a), a.tail(lookback).mean()
    width_now, width_avg = _last(bb_width), bb_width.tail(lookback).mean()

    if atr_now > atr_avg * 1.3 and width_now > width_avg * 1.3:
        return "STRONG"
    if atr_now < atr_avg * 0.7 and width_now < width_avg * 0.7:
        return "WEAK"
    return "NORMAL"


# ==================================================================
# 4. TREND "FLOW" STRATEGY  (majority vote of all trend strategies)
# ==================================================================

TREND_STRATEGIES = [
    ema_crossover_strategy,
    sma_crossover_strategy,
    golden_cross_strategy,
    death_cross_strategy,
    triple_ema_strategy,
    supertrend_strategy,
    parabolic_sar_strategy,
    donchian_trend_strategy,
    ichimoku_cloud_strategy,
    alligator_strategy,
]


def trend_flow_strategy(data: pd.DataFrame) -> dict:
    """
    Runs every trend strategy and returns the majority "flow" direction
    plus the individual votes (useful for debugging/confidence scoring).
    """
    votes = {}
    for strat in TREND_STRATEGIES:
        try:
            votes[strat.__name__] = strat(data)
        except Exception:
            votes[strat.__name__] = "HOLD"

    buy = sum(1 for v in votes.values() if v == "BUY")
    put = sum(1 for v in votes.values() if v == "PUT")

    if buy > put and buy >= 4:
        flow = "BUY"
    elif put > buy and put >= 4:
        flow = "PUT"
    else:
        flow = "HOLD"

    return {"flow": flow, "buy_votes": buy, "put_votes": put, "votes": votes}


# ==================================================================
# 5. DOJI MARKET FILTER
# ==================================================================

def doji_filter(data: pd.DataFrame, body_ratio=0.1) -> bool:
    """
    Returns True if the last candle is a DOJI (market indecision) —
    signals should normally be SKIPPED on a doji.
    body_ratio: body must be <= this fraction of the full range to count as doji.
    """
    row = data.iloc[-1]
    rng = row['high'] - row['low']
    if rng == 0:
        return True
    body = abs(row['close'] - row['open'])
    return (body / rng) <= body_ratio


# ==================================================================
# 6. BIG CANDLE MARKET FILTER
# ==================================================================

def big_candle_filter(data: pd.DataFrame, lookback=20, factor=1.5) -> dict:
    """
    Detects unusually large candles vs the recent average body size.
    Returns dict: {"is_big": bool, "is_exhaustion": bool}
      is_big        -> candle body is > factor x average (strong momentum, can confirm signal)
      is_exhaustion -> candle body is > 2.5x average (possible reversal / blow-off, be cautious)
    """
    bodies = (data['close'] - data['open']).abs()
    avg_body = bodies.tail(lookback).mean()
    current = bodies.iloc[-1]

    is_big = avg_body > 0 and current > avg_body * factor
    is_exhaustion = avg_body > 0 and current > avg_body * 2.5
    return {"is_big": bool(is_big), "is_exhaustion": bool(is_exhaustion)}


# ==================================================================
# 7. HIGH VOLUME MARKET FILTER
# ==================================================================

def volume_filter(data: pd.DataFrame, period=20, factor=1.2) -> bool:
    """
    Returns True if current volume confirms the move (above average).
    If 'volume' column is missing (common on OTC synthetic feeds),
    returns True by default so it never blocks a trade.
    """
    if 'volume' not in data.columns:
        return True
    avg_vol = data['volume'].rolling(period).mean()
    return _last(data['volume'], 0) > _last(avg_vol, 0) * factor


# ==================================================================
# 8. FINAL COMBINED SIGNAL ENGINE
# ==================================================================

def generate_final_signal(data: pd.DataFrame, min_rows=210) -> dict:
    """
    Combines everything above into one final BUY / PUT / NO TRADE
    decision, the way a real OTC binary-options filter chain works:

        1) Enough data?                -> else NO TRADE
        2) Doji candle?                -> skip (indecision)
        3) Volatility too low?         -> skip (flat/choppy market)
        4) Trend flow + price action agree?
        5) Confirm with big-candle / volume filter (adds confidence)

    Returns a dict with the final signal + full reasoning breakdown.
    """
    result = {
        "signal": "NO TRADE",
        "confidence": "LOW",
        "reason": "",
        "details": {},
    }

    if len(data) < min_rows:
        result["reason"] = f"Not enough candles (need >= {min_rows}, have {len(data)})"
        return result

    # --- filters first ---
    is_doji = doji_filter(data)
    if is_doji:
        result["reason"] = "Last candle is a Doji -> market indecision, no trade"
        result["details"]["doji"] = True
        return result

    vol_ok = volatility_filter(data)
    if not vol_ok:
        result["reason"] = "Volatility too low -> flat/quiet market, no trade"
        result["details"]["volatility_ok"] = False
        return result

    strength = strong_volatility_filter(data)

    # --- core signals ---
    flow = trend_flow_strategy(data)
    price_action = rsi_ema_bb_price_action_signal(data)
    big_candle = big_candle_filter(data)
    vol_confirm = volume_filter(data)

    result["details"] = {
        "trend_flow": flow,
        "price_action_signal": price_action,
        "volatility_strength": strength,
        "big_candle": big_candle,
        "volume_confirm": vol_confirm,
    }

    # --- decision logic ---
    final_direction = None
    if flow["flow"] == "BUY" and price_action in ("BUY", "HOLD"):
        final_direction = "BUY"
    elif flow["flow"] == "PUT" and price_action in ("PUT", "HOLD"):
        final_direction = "PUT"
    elif flow["flow"] == "HOLD" and price_action in ("BUY", "PUT"):
        # price action alone, weaker signal
        final_direction = price_action

    if final_direction is None:
        result["reason"] = "Trend flow and price-action disagree / no clear setup"
        return result

    if big_candle["is_exhaustion"]:
        result["reason"] = "Candle looks exhausted (possible reversal blow-off), skipping"
        return result

    # confidence scoring
    score = 0
    score += 2 if flow["flow"] == final_direction else 0
    score += 1 if price_action == final_direction else 0
    score += 1 if strength == "STRONG" else (0 if strength == "NORMAL" else -1)
    score += 1 if big_candle["is_big"] else 0
    score += 1 if vol_confirm else 0

    confidence = "HIGH" if score >= 4 else "MEDIUM" if score >= 2 else "LOW"

    result["signal"] = final_direction
    result["confidence"] = confidence
    result["reason"] = "Trend flow + price action + filters aligned"
    return result


# ==================================================================
# DEMO / TEST (synthetic OHLCV data — replace with your real feed)
# ==================================================================

if __name__ == "__main__":
    np.random.seed(42)
    n = 300
    price = 100 + np.cumsum(np.random.normal(0, 0.3, n))
    high = price + np.random.uniform(0.05, 0.4, n)
    low = price - np.random.uniform(0.05, 0.4, n)
    open_ = price + np.random.normal(0, 0.15, n)
    close = price
    volume = np.random.randint(100, 1000, n)

    df = pd.DataFrame({
        "open": open_, "high": high, "low": low,
        "close": close, "volume": volume
    })

    final = generate_final_signal(df)
    print("=== FINAL SIGNAL ===")
    for k, v in final.items():
        print(f"{k}: {v}")
