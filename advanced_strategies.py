"""
==================================================================
ADVANCED BINARY / OTC STRATEGY PACK  (v2)
==================================================================
Adds 12 more REAL price-action / indicator strategies on top of the
base file `binary_otc_strategies.py` (10 trend strategies + filters),
and produces one final combined BUY / PUT / NO TRADE decision.

New strategies in this file
----------------------------
 1. EMA 20 + EMA 50 Trend Pullback
 2. EMA 50 + EMA 200 Golden / Death Cross (combined)
 3. Support & Resistance Bounce
 4. Breakout + Retest Entry
 5. RSI (14) + Divergence
 6. MACD Zero-Line + Crossover
 7. Bollinger Bands Rejection
 8. Price Action Pin Bar
 9. Engulfing Candle + Trend Confirmation
10. Supply & Demand Zone Trading
11. Fibonacci 61.8% Retracement Entry
12. VWAP Pullback

This file requires `binary_otc_strategies.py` to be in the SAME
folder (it reuses the indicator helpers + filters from there instead
of duplicating code).

Usage
-----
    from advanced_strategies import generate_master_signal
    result = generate_master_signal(df)   # df: open, high, low, close, (volume)
    print(result)
==================================================================
"""

import numpy as np
import pandas as pd

from binary_otc_strategies import (
    ema, sma, rsi, bollinger_bands, atr, _last, _prev,
    TREND_STRATEGIES, trend_flow_strategy,
    rsi_ema_bb_price_action_signal,
    doji_filter, big_candle_filter, volume_filter,
    volatility_filter, strong_volatility_filter,
)


# ==================================================================
# EXTRA INDICATOR HELPER
# ==================================================================

def macd(series: pd.Series, fast=12, slow=26, signal=9):
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


# ==================================================================
# 1. EMA 20 + EMA 50 TREND PULLBACK
# ==================================================================

def ema_20_50_pullback_strategy(data: pd.DataFrame, fast=20, slow=50) -> str:
    """EMA 20 + EMA 50 Trend Pullback"""
    close, low, high = data['close'], data['low'], data['high']
    f, s = ema(close, fast), ema(close, slow)
    tol = _last(atr(data, 14)) * 0.5

    uptrend = _last(f) > _last(s)
    downtrend = _last(f) < _last(s)
    last_low, last_high, last_close, last_f = _last(low), _last(high), _last(close), _last(f)

    if uptrend and last_low <= last_f + tol and last_close > last_f:
        return "BUY"
    if downtrend and last_high >= last_f - tol and last_close < last_f:
        return "PUT"
    return "HOLD"


# ==================================================================
# 2. EMA 50 + EMA 200 GOLDEN / DEATH CROSS (combined)
# ==================================================================

def ema_50_200_cross_strategy(data: pd.DataFrame, fast=50, slow=200) -> str:
    """EMA 50 + EMA 200 Golden/Death Cross"""
    f, s = ema(data['close'], fast), ema(data['close'], slow)
    if _prev(f) <= _prev(s) and _last(f) > _last(s):
        return "BUY"       # golden cross
    if _prev(f) >= _prev(s) and _last(f) < _last(s):
        return "PUT"        # death cross
    return "HOLD"


# ==================================================================
# 3. SUPPORT & RESISTANCE BOUNCE
# ==================================================================

def support_resistance_bounce_strategy(data: pd.DataFrame, lookback=20) -> str:
    """Support & Resistance Bounce"""
    high, low, close, open_ = data['high'], data['low'], data['close'], data['open']
    support = low.rolling(lookback).min()
    resistance = high.rolling(lookback).max()
    tol = _last(atr(data, 14)) * 0.3

    last_low, last_high = _last(low), _last(high)
    last_close, last_open = _last(close), _last(open_)

    near_support = abs(last_low - _last(support)) <= tol
    near_resistance = abs(last_high - _last(resistance)) <= tol

    if near_support and last_close > last_open:
        return "BUY"
    if near_resistance and last_close < last_open:
        return "PUT"
    return "HOLD"


# ==================================================================
# 4. BREAKOUT + RETEST ENTRY
# ==================================================================

def breakout_retest_strategy(data: pd.DataFrame, lookback=20, retest_window=5) -> str:
    """Breakout + Retest Entry"""
    high, low, close = data['high'], data['low'], data['close']
    prior_res = high.rolling(lookback).max().shift(retest_window)
    prior_sup = low.rolling(lookback).min().shift(retest_window)
    tol = _last(atr(data, 14)) * 0.3

    recent_close = close.tail(retest_window)
    breakout_up = (recent_close > prior_res.tail(retest_window)).any()
    breakout_down = (recent_close < prior_sup.tail(retest_window)).any()

    last_low, last_high, last_close = _last(low), _last(high), _last(close)
    last_prior_res, last_prior_sup = _last(prior_res), _last(prior_sup)

    if breakout_up and abs(last_low - last_prior_res) <= tol and last_close > last_prior_res:
        return "BUY"
    if breakout_down and abs(last_high - last_prior_sup) <= tol and last_close < last_prior_sup:
        return "PUT"
    return "HOLD"


# ==================================================================
# 5. RSI (14) + DIVERGENCE
# ==================================================================

def rsi_divergence_strategy(data: pd.DataFrame, period=14, lookback=20) -> str:
    """RSI (14) + Divergence"""
    close = data['close']
    r = rsi(close, period)
    if len(close) < lookback:
        return "HOLD"

    recent_price = close.tail(lookback)
    recent_rsi = r.tail(lookback)
    half = lookback // 2

    p1, p2 = recent_price.iloc[:half], recent_price.iloc[half:]
    r1, r2 = recent_rsi.iloc[:half], recent_rsi.iloc[half:]

    # Bullish divergence: price makes a lower low, RSI makes a higher low
    if p2.min() < p1.min() and r2.min() > r1.min():
        return "BUY"
    # Bearish divergence: price makes a higher high, RSI makes a lower high
    if p2.max() > p1.max() and r2.max() < r1.max():
        return "PUT"
    return "HOLD"


# ==================================================================
# 6. MACD ZERO-LINE + CROSSOVER
# ==================================================================

def macd_zero_cross_strategy(data: pd.DataFrame, fast=12, slow=26, signal=9) -> str:
    """MACD Zero Line + Crossover"""
    macd_line, signal_line, _ = macd(data['close'], fast, slow, signal)

    cross_up = _prev(macd_line) <= _prev(signal_line) and _last(macd_line) > _last(signal_line)
    cross_down = _prev(macd_line) >= _prev(signal_line) and _last(macd_line) < _last(signal_line)

    if cross_up and _last(macd_line) > 0:
        return "BUY"
    if cross_down and _last(macd_line) < 0:
        return "PUT"
    return "HOLD"


# ==================================================================
# 7. BOLLINGER BANDS REJECTION
# ==================================================================

def bollinger_rejection_strategy(data: pd.DataFrame, period=20, std=2.0) -> str:
    """Bollinger Bands Rejection"""
    upper, mid, lower = bollinger_bands(data['close'], period, std)
    last_high, last_low = _last(data['high']), _last(data['low'])
    last_close = _last(data['close'])

    if last_high >= _last(upper) and last_close < _last(upper):
        return "PUT"        # rejected from upper band
    if last_low <= _last(lower) and last_close > _last(lower):
        return "BUY"        # rejected from lower band
    return "HOLD"


# ==================================================================
# 8. PRICE ACTION PIN BAR
# ==================================================================

def pin_bar_strategy(data: pd.DataFrame, wick_ratio=2.0) -> str:
    """Price Action Pin Bar"""
    row = data.iloc[-1]
    body = abs(row['close'] - row['open'])
    upper_wick = row['high'] - max(row['close'], row['open'])
    lower_wick = min(row['close'], row['open']) - row['low']
    rng = row['high'] - row['low']
    if rng == 0:
        return "HOLD"

    if lower_wick >= body * wick_ratio and lower_wick > upper_wick * 1.5 and body / rng < 0.35:
        return "BUY"         # bullish pin bar / hammer
    if upper_wick >= body * wick_ratio and upper_wick > lower_wick * 1.5 and body / rng < 0.35:
        return "PUT"         # bearish pin bar / shooting star
    return "HOLD"


# ==================================================================
# 9. ENGULFING CANDLE + TREND CONFIRMATION
# ==================================================================

def engulfing_trend_strategy(data: pd.DataFrame, ema_period=50) -> str:
    """Engulfing Candle + Trend Confirmation"""
    if len(data) < 2:
        return "HOLD"
    trend = ema(data['close'], ema_period)
    uptrend = _last(data['close']) > _last(trend)
    downtrend = _last(data['close']) < _last(trend)

    prev_row, cur_row = data.iloc[-2], data.iloc[-1]
    bullish_engulf = (prev_row['close'] < prev_row['open'] and
                      cur_row['close'] > cur_row['open'] and
                      cur_row['close'] >= prev_row['open'] and
                      cur_row['open'] <= prev_row['close'])
    bearish_engulf = (prev_row['close'] > prev_row['open'] and
                       cur_row['close'] < cur_row['open'] and
                       cur_row['close'] <= prev_row['open'] and
                       cur_row['open'] >= prev_row['close'])

    if bullish_engulf and uptrend:
        return "BUY"
    if bearish_engulf and downtrend:
        return "PUT"
    return "HOLD"


# ==================================================================
# 10. SUPPLY & DEMAND ZONE TRADING
# ==================================================================

def supply_demand_zone_strategy(data: pd.DataFrame, lookback=30, impulse_factor=1.8) -> str:
    """Supply & Demand Zone Trading"""
    if len(data) < lookback + 5:
        return "HOLD"

    window = data.iloc[-lookback:-3]
    bodies = (window['close'] - window['open']).abs()
    avg_body = bodies.mean()
    if avg_body == 0 or bodies.empty:
        return "HOLD"

    impulse_idx = bodies.idxmax()
    impulse_row = data.loc[impulse_idx]
    impulse_body = abs(impulse_row['close'] - impulse_row['open'])
    if impulse_body < avg_body * impulse_factor:
        return "HOLD"

    zone_low = min(impulse_row['open'], impulse_row['close'])
    zone_high = max(impulse_row['open'], impulse_row['close'])
    bullish_impulse = impulse_row['close'] > impulse_row['open']

    price = _last(data['close'])
    in_zone = zone_low <= price <= zone_high

    if bullish_impulse and in_zone:
        return "BUY"          # demand zone retest
    if not bullish_impulse and in_zone:
        return "PUT"           # supply zone retest
    return "HOLD"


# ==================================================================
# 11. FIBONACCI 61.8% RETRACEMENT ENTRY
# ==================================================================

def fibonacci_618_strategy(data: pd.DataFrame, lookback=30) -> str:
    """Fibonacci 61.8% Retracement Entry"""
    if len(data) < lookback:
        return "HOLD"

    highs = data['high'].tail(lookback)
    lows = data['low'].tail(lookback)
    idx_max = int(np.argmax(highs.values))
    idx_min = int(np.argmin(lows.values))

    sh, sl = highs.max(), lows.min()
    tol = _last(atr(data, 14)) * 0.3
    last_close, last_low, last_high = _last(data['close']), _last(data['low']), _last(data['high'])

    if idx_max > idx_min:
        # swing low happened first -> up move -> retracement buy zone
        fib618 = sh - 0.618 * (sh - sl)
        if last_low <= fib618 + tol and last_close > fib618:
            return "BUY"
    else:
        # swing high happened first -> down move -> retracement sell zone
        fib618 = sl + 0.618 * (sh - sl)
        if last_high >= fib618 - tol and last_close < fib618:
            return "PUT"
    return "HOLD"


# ==================================================================
# 12. VWAP PULLBACK
# ==================================================================

def vwap_pullback_strategy(data: pd.DataFrame) -> str:
    """VWAP Pullback"""
    if 'volume' not in data.columns or len(data) < 6:
        return "HOLD"

    typical_price = (data['high'] + data['low'] + data['close']) / 3
    cum_vol = data['volume'].cumsum()
    cum_tp_vol = (typical_price * data['volume']).cumsum()
    vwap = cum_tp_vol / cum_vol.replace(0, np.nan)

    tol = _last(atr(data, 14)) * 0.3
    v = _last(vwap)
    last_close = _last(data['close'])
    last_low, last_high = _last(data['low']), _last(data['high'])
    momentum_up = data['close'].iloc[-1] > data['close'].iloc[-5]
    momentum_down = data['close'].iloc[-1] < data['close'].iloc[-5]

    if last_low <= v + tol and last_close > v and momentum_up:
        return "BUY"
    if last_high >= v - tol and last_close < v and momentum_down:
        return "PUT"
    return "HOLD"


# ==================================================================
# COLLECT ALL ADVANCED STRATEGIES + FLOW VOTE
# ==================================================================

ADVANCED_STRATEGIES = [
    ema_20_50_pullback_strategy,
    ema_50_200_cross_strategy,
    support_resistance_bounce_strategy,
    breakout_retest_strategy,
    rsi_divergence_strategy,
    macd_zero_cross_strategy,
    bollinger_rejection_strategy,
    pin_bar_strategy,
    engulfing_trend_strategy,
    supply_demand_zone_strategy,
    fibonacci_618_strategy,
    vwap_pullback_strategy,
]


def advanced_flow_strategy(data: pd.DataFrame) -> dict:
    """Runs all 12 advanced strategies and returns the majority vote."""
    votes = {}
    for strat in ADVANCED_STRATEGIES:
        try:
            votes[strat.__name__] = strat(data)
        except Exception:
            votes[strat.__name__] = "HOLD"

    buy = sum(1 for v in votes.values() if v == "BUY")
    put = sum(1 for v in votes.values() if v == "PUT")

    if buy > put and buy >= 3:
        flow = "BUY"
    elif put > buy and put >= 3:
        flow = "PUT"
    else:
        flow = "HOLD"

    return {"flow": flow, "buy_votes": buy, "put_votes": put, "votes": votes}


# ==================================================================
# MASTER SIGNAL — combines BASE trend strategies + ADVANCED strategies
# + price action + all market filters into one final BUY/PUT decision
# ==================================================================

def generate_master_signal(data: pd.DataFrame, min_rows=210) -> dict:
    result = {"signal": "NO TRADE", "confidence": "LOW", "reason": "", "details": {}}

    if len(data) < min_rows:
        result["reason"] = f"Not enough candles (need >= {min_rows}, have {len(data)})"
        return result

    # ---- filters first ----
    if doji_filter(data):
        result["reason"] = "Last candle is a Doji -> indecision, no trade"
        return result

    if not volatility_filter(data):
        result["reason"] = "Volatility too low -> flat/quiet market, no trade"
        return result

    strength = strong_volatility_filter(data)
    big_candle = big_candle_filter(data)
    if big_candle["is_exhaustion"]:
        result["reason"] = "Candle looks exhausted (blow-off risk), skipping"
        return result

    vol_confirm = volume_filter(data)

    # ---- core votes ----
    base_flow = trend_flow_strategy(data)          # from binary_otc_strategies.py (10 strategies)
    adv_flow = advanced_flow_strategy(data)          # 12 new strategies (this file)
    price_action = rsi_ema_bb_price_action_signal(data)

    result["details"] = {
        "base_trend_flow": base_flow,
        "advanced_flow": adv_flow,
        "price_action_signal": price_action,
        "volatility_strength": strength,
        "big_candle": big_candle,
        "volume_confirm": vol_confirm,
    }

    votes_buy = sum([base_flow["flow"] == "BUY", adv_flow["flow"] == "BUY", price_action == "BUY"])
    votes_put = sum([base_flow["flow"] == "PUT", adv_flow["flow"] == "PUT", price_action == "PUT"])

    if votes_buy >= 2 and votes_buy > votes_put:
        final_direction = "BUY"
    elif votes_put >= 2 and votes_put > votes_buy:
        final_direction = "PUT"
    else:
        result["reason"] = "Base trend, advanced strategies and price action do not agree"
        return result

    # ---- confidence scoring ----
    score = 0
    score += 2 if base_flow["flow"] == final_direction else 0
    score += 2 if adv_flow["flow"] == final_direction else 0
    score += 1 if price_action == final_direction else 0
    score += 1 if strength == "STRONG" else (0 if strength == "NORMAL" else -1)
    score += 1 if big_candle["is_big"] else 0
    score += 1 if vol_confirm else 0

    confidence = "HIGH" if score >= 5 else "MEDIUM" if score >= 3 else "LOW"

    result["signal"] = final_direction
    result["confidence"] = confidence
    result["reason"] = "Base trend + advanced strategies + price action aligned"
    return result


# ==================================================================
# DEMO / TEST
# ==================================================================

if __name__ == "__main__":
    np.random.seed(7)
    n = 300
    price = 100 + np.cumsum(np.random.normal(0.02, 0.3, n))  # slight uptrend drift
    high = price + np.random.uniform(0.05, 0.4, n)
    low = price - np.random.uniform(0.05, 0.4, n)
    open_ = price + np.random.normal(0, 0.15, n)
    close = price
    volume = np.random.randint(100, 1000, n)

    df = pd.DataFrame({
        "open": open_, "high": high, "low": low,
        "close": close, "volume": volume
    })

    final = generate_master_signal(df)
    print("=== MASTER SIGNAL ===")
    for k, v in final.items():
        print(f"{k}: {v}")
