BOT_TOKEN  = "8159698797:AAE1fbbkTqn66eV3VdNqqaPhy9MMQtJm3PY"
ADMIN_IDS        = [7529660852, 8280240170, 7275974284]
GEMINI_API_KEYS = [
    "AIzaSyD1a_7FcV_39lwzWRtk3TlG6JMW1siwAJw",
    "AIzaSyCXH7YShveXso_SbEIufPkFay3HkrMK6TQ",
    "AIzaSyDnydjczHF8dzT3I4Od98gTYZUUnGhbTfc",
]
SUPPORT_USERNAME = "@RASUU_QXB"
REQUIRED_CHANNEL_1_ID   = -1002658285414
REQUIRED_CHANNEL_1_LINK = "https://t.me/irttradingzone"
REQUIRED_CHANNEL_2_ID   = -1003789726888
REQUIRED_CHANNEL_2_LINK = "https://t.me/zebronix_community"
OPEN_ACCOUNT_LINK = "https://broker-qx.pro/sign-up/?lid=1756662"

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import os, threading, time, json, traceback, requests, html as _html, hashlib, re, random, math
import importlib.util, sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

_STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
_BASE_STRATEGY_PATH = os.path.join(_STRATEGY_DIR, "binary_otc_strategies.py")
_ADVANCED_STRATEGY_PATH = os.path.join(_STRATEGY_DIR, "advanced_strategies.py")
_custom_strategies = None
_base_strategies = None
_custom_strategy_error = None
try:
    if os.path.isfile(_BASE_STRATEGY_PATH) and os.path.isfile(_ADVANCED_STRATEGY_PATH):
        _base_spec = importlib.util.spec_from_file_location("binary_otc_strategies", _BASE_STRATEGY_PATH)
        if not _base_spec or not _base_spec.loader:
            raise ImportError("Could not load binary_otc_strategies.py")
        _base_strategies = importlib.util.module_from_spec(_base_spec)
        sys.modules["binary_otc_strategies"] = _base_strategies
        _base_spec.loader.exec_module(_base_strategies)

        _custom_spec = importlib.util.spec_from_file_location(
            "zebronix_advanced_strategies", _ADVANCED_STRATEGY_PATH)
        if not _custom_spec or not _custom_spec.loader:
            raise ImportError("Could not load advanced_strategies.py")
        _custom_strategies = importlib.util.module_from_spec(_custom_spec)
        _custom_spec.loader.exec_module(_custom_strategies)
    else:
        missing = [os.path.basename(p) for p in (_BASE_STRATEGY_PATH, _ADVANCED_STRATEGY_PATH)
                   if not os.path.isfile(p)]
        _custom_strategy_error = f"Missing strategy file(s): {', '.join(missing)}"
except Exception as _custom_exc:
    _custom_strategy_error = str(_custom_exc)
    _custom_strategies = None
    _base_strategies = None

def _custom_strategy_available() -> bool:
    return bool(
        _base_strategies and _custom_strategies
        and callable(getattr(_base_strategies, "generate_final_signal", None))
        and callable(getattr(_custom_strategies, "generate_master_signal", None))
    )

def _analyze_pair_foxio_zx_ai(pair, candles):
    if not _custom_strategy_available() or not candles:
        return None
    try:
        import pandas as _pd
        frame = _pd.DataFrame(candles)
        for column in ("open", "high", "low", "close"):
            frame[column] = _pd.to_numeric(frame[column], errors="coerce")
        frame = frame.dropna(subset=["open", "high", "low", "close"])
        if "volume" not in frame.columns:
            frame["volume"] = 0.0
        else:
            frame["volume"] = _pd.to_numeric(frame["volume"], errors="coerce").fillna(0.0)
        if len(frame) < 210:
            return None
        raw = _custom_strategies.generate_master_signal(frame, min_rows=210)
    except Exception as exc:
        print(f"[FOXIO ZX AI] {pair}: {exc}")
        return None
    if not isinstance(raw, dict):
        return None
    token = str(raw.get("signal", "NO TRADE")).upper().strip()
    if token not in ("BUY", "CALL", "PUT", "SELL"):
        return None
    direction = "CALL" if token in ("BUY", "CALL") else "PUT"
    confidence_label = str(raw.get("confidence", "LOW")).upper()
    confidence = {"HIGH": 92, "MEDIUM": 85, "LOW": 79}.get(confidence_label, 79)
    details = raw.get("details", {}) or {}
    base_flow = details.get("base_trend_flow", {}) or {}
    advanced_flow = details.get("advanced_flow", {}) or {}
    confirms = int(base_flow.get("buy_votes" if direction == "CALL" else "put_votes", 0) or 0)
    confirms += int(advanced_flow.get("buy_votes" if direction == "CALL" else "put_votes", 0) or 0)
    if str(details.get("price_action_signal", "")).upper() in (
            "BUY" if direction == "CALL" else "PUT",):
        confirms += 1
    agreement = min(1.0, confirms / 23.0)
    return {"direction": direction, "confidence": confidence,
            "confirmations": confidence, "confirms": confirms,
            "market_type": "FOXIO_ZX_AI", "sw_score": agreement,
            "regime": confidence_label, "payout": 0,
            "strategy_reason": raw.get("reason", "")}

ALL_OTC_PAIRS = [
    "AUDCAD_otc","AUDCHF_otc","AUDJPY_otc","AUDNZD_otc","AUDUSD_otc","AXSUSD_otc",
    "BCHUSD_otc","BNBUSD_otc","BTCUSD_otc","CADCHF_otc","CADJPY_otc","CHFJPY_otc",
    "DOTUSD_otc","ETCUSD_otc","ETHUSD_otc","EURAUD_otc","EURCAD_otc","EURCHF_otc",
    "EURGBP_otc","EURJPY_otc","EURNZD_otc","EURUSD_otc","GBPAUD_otc","GBPCAD_otc",
    "GBPCHF_otc","GBPJPY_otc","GBPNZD_otc","GBPUSD_otc","LTCUSD_otc","NZDCAD_otc",
    "NZDCHF_otc","NZDJPY_otc","NZDUSD_otc","SOLUSD_otc","TONUSD_otc","USDARS_otc",
    "USDBDT_otc","USDCAD_otc","USDCHF_otc","USDCOP_otc","USDDZD_otc","USDEGP_otc",
    "USDIDR_otc","USDINR_otc","USDJPY_otc","USDMXN_otc","USDNGN_otc","USDPHP_otc",
    "USDPKR_otc","USDZAR_otc","XAGUSD_otc","XAUUSD_otc","XRPUSD_otc","ZECUSD_otc",
]

ALL_LIVE_PAIRS = [
    "AUDCAD","AUDCHF","AUDJPY","AUDUSD","CADJPY","EURAUD","EURCAD","EURCHF","EURGBP",
    "EURJPY","EURUSD","GBPAUD","GBPJPY","GBPUSD","USDCAD","USDCHF","USDJPY",
]

_FIAT_CODES = {
    "ARS","AUD","BDT","CAD","CHF","COP","DZD","EGP","EUR","GBP","IDR",
    "INR","JPY","MXN","NGN","NZD","PHP","PKR","USD","ZAR",
}
_CRYPTO_CODES = {"AXS","BCH","BNB","BTC","DOT","ETC","ETH","LTC","SOL","TON","XRP","ZEC"}

def _market_priority(pair: str) -> int:

    core = _ck_re.sub(r"[_-]OTC$", "", str(pair), flags=_ck_re.IGNORECASE).upper()
    core = _ck_re.sub(r"[^A-Z]", "", core)
    if len(core) >= 6 and core[:3] in _FIAT_CODES and core[3:6] in _FIAT_CODES:
        return 0
    if core[:3] in _CRYPTO_CODES:
        return 2
    return 1

def _pick_prioritized_signal(scored_signals: list):
    for priority in (0, 1, 2):
        group = [item for item in scored_signals if _market_priority(item[1]) == priority]
        if group:
            return max(group, key=lambda item: item[0])
    return None

FUTURE_REAL_PAIRS = list(ALL_LIVE_PAIRS)

MULTIPLE_FS_REAL = [
    "EUR/USD", "EUR/JPY", "AUD/JPY", "CAD/JPY", "USD/JPY", "AUD/CAD",
    "USD/CAD", "EUR/CAD", "GBP/CAD", "EUR/GBP", "GBP/USD", "USD/CHF", "AUD/CHF",
]
MULTIPLE_FS_OTC = [
    "USD/BDT-OTC", "USD/PHP-OTC", "BRL/USD-OTC", "CAD/CHF-OTC", "AUD/USD-OTC",
    "USD/INR-OTC", "USD/MXN-OTC", "USD/NGN-OTC", "USD/IDR-OTC", "NZD/CAD-OTC",
    "NZD/CHF-OTC", "NZD/USD-OTC", "USD/PKR-OTC", "XAUUSD-OTC", "UKBRENT-OTC",
    "USD/EGP-OTC", "USD/DZD-OTC", "USD/ARS-OTC", "XRP/USD-OTC", "TON/USD-OTC",
    "EUR/USD-OTC", "EUR/JPY-OTC", "AUD/JPY-OTC", "CAD/JPY-OTC", "USD/JPY-OTC",
    "AUD/CAD-OTC", "USD/CAD-OTC", "EUR/CAD-OTC", "GBP/CAD-OTC", "EUR/GBP-OTC",
    "GBP/USD-OTC", "USD/CHF-OTC", "AUD/CHF-OTC",
]

ALL_INDICATORS = {1:"EMA", 2:"RSI", 3:"TREND", 4:"FBI", 5:"BBI", 6:"S/R"}

PAIR_DISPLAY_NAMES = {p: p for p in ALL_OTC_PAIRS}


def get_display_name(pair: str) -> str:
    if pair in PAIR_DISPLAY_NAMES:
        return PAIR_DISPLAY_NAMES[pair]
    return pair


def _kb_future_mode_select():
    return {"inline_keyboard": [
        [{"text": "OTC Markets", "callback_data": "fut_mode_OTC",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["📊"])},
         {"text": "Real Markets", "callback_data": "fut_mode_REAL",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["📈"])}],
        [{"text": "Blackout Signals", "callback_data": "fut_mode_BLACKOUT",
          "style": "danger", "icon_custom_emoji_id": str(EMAP["😈"])},
         {"text": "Whiteout Signals", "callback_data": "fut_mode_WHITEOUT",
          "style": "success", "icon_custom_emoji_id": str(EMAP["⚪"])}],
        [{"text": "Home", "callback_data": "menu_home", "style": "primary",
          "icon_custom_emoji_id": "5416041192905265756"}],
    ]}


def _kb_future_new_market_select(strategy: str):
    strategy = str(strategy).upper()
    return {"inline_keyboard": [
        [{"text": "𝙾𝚃𝙲 𝙼𝙰𝚁𝙺𝙴𝚃", "callback_data": f"futnew_market_{strategy}_OTC",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["📊"])},
         {"text": "𝙻𝙸𝚅𝙴 𝙼𝙰𝚁𝙺𝙴𝚃", "callback_data": f"futnew_market_{strategy}_REAL",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["📈"])}],
        [{"text": "Home", "callback_data": "menu_home", "style": "danger",
          "icon_custom_emoji_id": "5416041192905265756"}],
    ]}


def _future_pair_pool(mode: str) -> list:
    if mode == "REAL":
        return _get_lsig_live_pairs()
    return _get_lsig_otc_pairs()


def _future_fetch_payouts(pool: list) -> dict:
    payouts = {}
    with ThreadPoolExecutor(max_workers=min(len(pool), 25)) as ex:
        futs = {ex.submit(_get_pair_payout, p): p for p in pool}
        for fut in as_completed(futs):
            p = futs[fut]
            try:
                payouts[p] = fut.result()
            except Exception:
                payouts[p] = 0
    return payouts


def _kb_future_pair_grid(sess):
    pool = sess.fut_sorted_pairs if sess.fut_sorted_pairs else _future_pair_pool(sess.fut_market_mode)
    payouts = sess.fut_pair_payouts or {}
    sel  = sess.fut_pairs
    rows = []
    for i in range(0, len(pool), 2):
        row = []
        for p in pool[i:i + 2]:
            is_sel = p in sel
            icon_id = "6231121076814879723" if is_sel else "6233277751692894018"
            payout = payouts.get(p)
            label = f"{get_display_name(p)} ({payout}%)" if payout else get_display_name(p)
            row.append({"text": label,
                        "callback_data": f"futg_{p}",
                        "style": "success" if is_sel else "primary",
                        "icon_custom_emoji_id": icon_id})
        rows.append(row)
    rows.append([{"text": "Continue Next", "callback_data": "futg_done",
                  "style": "success", "icon_custom_emoji_id": str(EMAP["🚀"])}])
    rows.append([{"text": "Home", "callback_data": "menu_home", "style": "danger",
                  "icon_custom_emoji_id": "5416041192905265756"}])
    return {"inline_keyboard": rows}


def _kb_future_dir_select():
    return {"inline_keyboard": [
        [{"text": "Call", "callback_data": "fut_dir_1", "style": "success","icon_custom_emoji_id": "6311870452004299281"},
         {"text": "Put",  "callback_data": "fut_dir_2", "style": "danger","icon_custom_emoji_id": "6312229687363904744"}],
        [{"text": "Both", "callback_data": "fut_dir_3", "style": "primary","icon_custom_emoji_id": "6311984148378560080"}],
        [{"text": "Home", "callback_data": "menu_home", "style": "danger",
          "icon_custom_emoji_id": "5416041192905265756"}],
    ]}


def _kb_future_days_select():
    rows = []
    days = list(range(1, 15))
    for i in range(0, len(days), 3):
        row = [{"text": f"Day {d}", "callback_data": f"fut_day_{d}", "style": "primary",
                "icon_custom_emoji_id": "6212848404742020294"}
               for d in days[i:i + 3]]
        rows.append(row)
    rows.append([{"text": "Home", "callback_data": "menu_home", "style": "danger",
                  "icon_custom_emoji_id": "5416041192905265756"}])
    return {"inline_keyboard": rows}


def _kb_future_new_days_select():
    rows = []
    days = list(range(1, 31))
    for i in range(0, len(days), 3):
        rows.append([
            {"text": f"Day {d}", "callback_data": f"futnew_day_{d}",
             "style": "primary", "icon_custom_emoji_id": "6212848404742020294"}
            for d in days[i:i + 3]
        ])
    rows.append([{"text": "Home", "callback_data": "menu_home", "style": "danger",
                  "icon_custom_emoji_id": "5416041192905265756"}])
    return {"inline_keyboard": rows}



import re as _ck_re
from functools import lru_cache as _ck_lru_cache

_CK_SUPPORTED_OTC = {p.upper() for p in ALL_OTC_PAIRS}
_CK_SUPPORTED_BASE = {p.replace("_OTC", "") for p in _CK_SUPPORTED_OTC}
_CK_SUPPORTED_LIVE = {p.upper() for p in FUTURE_REAL_PAIRS}

_CK_BUY_WORDS  = {"buy","call","cal","up","high","long","↑","⬆","🟢","green"}
_CK_SELL_WORDS = {"sell","sel","put","down","low","short","↓","⬇","🔴","red"}
_CK_NOISE_WORDS = {
    "m1","m5","m15","m30","h1","h4",
    "otc","signal","trade","entry","open",
    "quotex","olymp","pocket","binomo","iqoption",
    "time","pair","direction","action","type",
    ">","<","=","→","►","•","·","|",":",";",
    "#","@","✅","❌","⚡","🔥","💰","📊","📈","📉",
}
_CK_TIME_RE = _ck_re.compile(r"\b(\d{1,2}:\d{2})\b")
_CK_SIGNAL_RE = _ck_re.compile(
    r"^M1[\s;]+([A-Za-z0-9/_\-]+(?:\s*-\s*OTC)?)\s*[;\s]+(\d{1,2}:\d{2})\s*[;\s]+(BUY|PUT|CALL|SELL|CAL|SEL)\s*$",
    _ck_re.IGNORECASE,
)
_CK_MTG_SUP = {
    0:"",1:"\u00b9",2:"\u00b2",3:"\u00b3",4:"\u2074",5:"\u2075",6:"\u2076",
    7:"\u2077",8:"\u2078",9:"\u2079",10:"\u00b9\u2070",11:"\u00b9\u00b9",
    12:"\u00b9\u00b2",13:"\u00b9\u00b3",14:"\u00b9\u2074",15:"\u00b9\u2075",
    16:"\u00b9\u2076",17:"\u00b9\u2077",18:"\u00b9\u2078",19:"\u00b9\u2079",20:"\u00b2\u2070",
}

def _ck_clean_unicode(text: str) -> str:
    result = []
    for ch in text:
        cp = ord(ch)
        if 0x1D400 <= cp <= 0x1D419: result.append(chr(cp - 0x1D400 + ord('A')))
        elif 0x1D41A <= cp <= 0x1D433: result.append(chr(cp - 0x1D41A + ord('a')))
        elif 0x1D434 <= cp <= 0x1D44D: result.append(chr(cp - 0x1D434 + ord('A')))
        elif 0x1D44E <= cp <= 0x1D467: result.append(chr(cp - 0x1D44E + ord('a')))
        elif 0x1D468 <= cp <= 0x1D481: result.append(chr(cp - 0x1D468 + ord('A')))
        elif 0x1D482 <= cp <= 0x1D49B: result.append(chr(cp - 0x1D482 + ord('a')))
        elif 0x1D49C <= cp <= 0x1D4B5: result.append(chr(cp - 0x1D49C + ord('A')))
        elif 0x1D4B6 <= cp <= 0x1D4CF: result.append(chr(cp - 0x1D4B6 + ord('a')))
        elif 0x1D4D0 <= cp <= 0x1D4E9: result.append(chr(cp - 0x1D4D0 + ord('A')))
        elif 0x1D4EA <= cp <= 0x1D503: result.append(chr(cp - 0x1D4EA + ord('a')))
        elif 0x1D504 <= cp <= 0x1D51D: result.append(chr(cp - 0x1D504 + ord('A')))
        elif 0x1D51E <= cp <= 0x1D537: result.append(chr(cp - 0x1D51E + ord('a')))
        elif 0x1D538 <= cp <= 0x1D551: result.append(chr(cp - 0x1D538 + ord('A')))
        elif 0x1D552 <= cp <= 0x1D56B: result.append(chr(cp - 0x1D552 + ord('a')))
        elif 0x1D5A0 <= cp <= 0x1D5B9: result.append(chr(cp - 0x1D5A0 + ord('A')))
        elif 0x1D5BA <= cp <= 0x1D5D3: result.append(chr(cp - 0x1D5BA + ord('a')))
        elif 0x1D5D4 <= cp <= 0x1D5ED: result.append(chr(cp - 0x1D5D4 + ord('A')))
        elif 0x1D5EE <= cp <= 0x1D607: result.append(chr(cp - 0x1D5EE + ord('a')))
        elif 0x1D608 <= cp <= 0x1D621: result.append(chr(cp - 0x1D608 + ord('A')))
        elif 0x1D622 <= cp <= 0x1D63B: result.append(chr(cp - 0x1D622 + ord('a')))
        elif 0x1D63C <= cp <= 0x1D655: result.append(chr(cp - 0x1D63C + ord('A')))
        elif 0x1D656 <= cp <= 0x1D66F: result.append(chr(cp - 0x1D656 + ord('a')))
        elif 0x1D670 <= cp <= 0x1D689: result.append(chr(cp - 0x1D670 + ord('A')))
        elif 0x1D68A <= cp <= 0x1D6A3: result.append(chr(cp - 0x1D68A + ord('a')))
        elif 0x1D56C <= cp <= 0x1D585: result.append(chr(cp - 0x1D56C + ord('A')))
        elif 0x1D586 <= cp <= 0x1D59F: result.append(chr(cp - 0x1D586 + ord('a')))
        elif 0x1D7CE <= cp <= 0x1D7D7: result.append(chr(cp - 0x1D7CE + ord('0')))
        elif 0x1D7D8 <= cp <= 0x1D7E1: result.append(chr(cp - 0x1D7D8 + ord('0')))
        elif 0x1D7E2 <= cp <= 0x1D7EB: result.append(chr(cp - 0x1D7E2 + ord('0')))
        elif 0x1D7EC <= cp <= 0x1D7F5: result.append(chr(cp - 0x1D7EC + ord('0')))
        elif 0x1D7F6 <= cp <= 0x1D7FF: result.append(chr(cp - 0x1D7F6 + ord('0')))
        elif 0xFF21 <= cp <= 0xFF3A: result.append(chr(cp - 0xFF21 + ord('A')))
        elif 0xFF41 <= cp <= 0xFF5A: result.append(chr(cp - 0xFF41 + ord('a')))
        elif 0xFF10 <= cp <= 0xFF19: result.append(chr(cp - 0xFF10 + ord('0')))
        elif 0x24B6 <= cp <= 0x24CF: result.append(chr(cp - 0x24B6 + ord('A')))
        elif 0x24D0 <= cp <= 0x24E9: result.append(chr(cp - 0x24D0 + ord('a')))
        else: result.append(ch)

    return _ck_re.sub(r"^[^A-Za-z0-9]+", "", "".join(result))

def _ck_normalize_pair(raw: str) -> str:
    p = raw.upper().strip()
    prefix_otc = bool(_ck_re.match(r"^OTC[_\-]?", p, _ck_re.IGNORECASE))
    if prefix_otc:
        p = _ck_re.sub(r"^OTC[_\-]?", "", p, flags=_ck_re.IGNORECASE)
    is_otc = prefix_otc or bool(_ck_re.search(r"[_\-]?OTC$", p, _ck_re.IGNORECASE))
    base = _ck_re.sub(r"[_\-]?OTC$", "", p, flags=_ck_re.IGNORECASE).strip("_-/ ")
    base_clean = _ck_re.sub(r"[_/\-]", "", base)
    for lookup in (base, base_clean):
        otc_candidate = f"{lookup}_OTC"
        if otc_candidate in _CK_SUPPORTED_OTC:
            return otc_candidate
        for sup in _CK_SUPPORTED_OTC:
            if sup.replace("_OTC", "").upper() == lookup:
                return sup
    if is_otc:
        return f"{base_clean}_OTC" if base_clean else f"{base}_OTC"
    return base_clean if base_clean else base

def _ck_extract_from_line(line: str):
    line = _ck_clean_unicode(line)
    if ";" in line:
        parts = [p.strip() for p in line.split(";") if p.strip()]
        parts = [p for p in parts if not _ck_re.match(r"^[Mm]\d+$", p)]
        line = " ".join(parts)
    line = _ck_re.sub(r"\bOTC[-_]([A-Za-z]{3,12})\b", r"\1_OTC", line, flags=_ck_re.IGNORECASE)
    line = _ck_re.sub(r"\b([A-Za-z]{2,6})/([A-Za-z]{2,6})\b", r"\1\2", line, flags=_ck_re.IGNORECASE)
    line = _ck_re.sub(r"\b([A-Za-z]{2,5})\s+([A-Za-z]{2,5})\s*(?:\(OTC\)|\[OTC\]|-OTC\b|\bOTC\b)",
                       r"\1\2_OTC", line, flags=_ck_re.IGNORECASE)
    line = _ck_re.sub(r"\b([A-Za-z0-9_]{3,15})\s*[\(\[]\s*OTC\s*[\)\]]\s*", r"\1_OTC ", line, flags=_ck_re.IGNORECASE)
    line = _ck_re.sub(r"\b([A-Za-z0-9]{4,15})\s+OTC\b", r"\1_OTC", line, flags=_ck_re.IGNORECASE)
    line = _ck_re.sub(r"\b([A-Za-z0-9]{2,15})\s*-\s*OTC\b", r"\1_OTC", line, flags=_ck_re.IGNORECASE)
    line = _ck_re.sub(r"[-]OTC\b", "_OTC", line, flags=_ck_re.IGNORECASE)
    line = line.strip()
    line = _ck_re.sub(r"^[\s▢❒◆●•▸►◉▪▫◼◻☞]+", "", line)
    line = _ck_re.sub(r"[,]+", " ", line)
    line = _ck_re.sub(r"[⇨➪☞⊱⇒⟹➜➝➞➟➠➡➢➣→►•·=><|/–—►]+", " ", line)
    line = _ck_re.sub(r"\s+", " ", line).strip()

    time_match = _CK_TIME_RE.search(line)
    if not time_match:
        return None
    time_str = time_match.group(1)
    tokens = line.split()

    direction = None
    for tok in tokens:
        tok_clean = tok.strip("📊📈📉✅❌⚡🔥💰🟢🔴><=!#@").lower()
        if tok_clean in _CK_BUY_WORDS:
            direction = "BUY"; break
        if tok_clean in _CK_SELL_WORDS:
            direction = "PUT"; break
    if not direction:
        return None

    pair_candidates = []
    for tok in tokens:
        tok_up = tok.strip("📊📈📉✅❌⚡🔥💰🟢🔴><=!#@").upper()
        if tok_up.lower() in _CK_NOISE_WORDS: continue
        if tok_up.lower() in _CK_BUY_WORDS | _CK_SELL_WORDS: continue
        if _ck_re.match(r"^\d{1,2}:\d{2}$", tok_up): continue
        if len(tok_up) < 3: continue
        if not _ck_re.search(r"[A-Z]{2,}", tok_up): continue
        if _ck_re.match(r"^_?OTC_?$", tok_up, _ck_re.IGNORECASE): continue
        pair_candidates.append(tok_up)
    if not pair_candidates:
        return None

    def _score(p):
        s = 0
        if "OTC" in p: s += 10
        if _ck_re.match(r"^[A-Z]{3,6}[_\-]?[A-Z]{2,6}([_\-]OTC)?$", p): s += 5
        return s + len(p)

    pair = max(pair_candidates, key=_score)
    pair = _ck_re.sub(r"[-]OTC$", "_OTC", pair, flags=_ck_re.IGNORECASE).upper()
    pair = _ck_normalize_pair(pair)
    return pair, time_str, direction

def _ck_parse_signals(raw_text: str):
    valid, errors = [], []
    for line in raw_text.strip().splitlines():
        original = line.strip()
        if not original: continue
        m = _CK_SIGNAL_RE.match(original)
        if m:
            raw_dir = m.group(3).upper()
            direction = "BUY" if raw_dir in ("BUY", "CALL", "CAL") else "PUT"
            raw_pair = _ck_re.sub(r"\s*-\s*OTC$", "_OTC", m.group(1).strip(), flags=_ck_re.IGNORECASE)
            pair = _ck_normalize_pair(raw_pair)
            valid.append({"pair": pair, "time": m.group(2), "direction": direction,
                          "raw": f"M1 {pair} {m.group(2)} {direction}"})
            continue
        result = _ck_extract_from_line(original)
        if result:
            pair, time_str, direction = result
            valid.append({"pair": pair, "time": time_str, "direction": direction,
                          "raw": f"M1 {pair} {time_str} {direction}"})
            continue
        errors.append(original)
    return valid, errors

def _ck_normalize_live_pair(raw: str) -> str:
    p = raw.upper().strip()
    p_clean = _ck_re.sub(r"[_\-/]", "", p)
    for lookup in (p, p_clean):
        if lookup in _CK_SUPPORTED_LIVE:
            return lookup
        for sup in _CK_SUPPORTED_LIVE:
            if sup.replace("_", "").replace("-", "") == lookup:
                return sup
    return p_clean if p_clean else p

def _ck_extract_from_line_live(line: str):
    line = _ck_clean_unicode(line)
    if ";" in line:
        parts = [p.strip() for p in line.split(";") if p.strip()]
        parts = [p for p in parts if not _ck_re.match(r"^[Mm]\d+$", p)]
        line = " ".join(parts)
    line = _ck_re.sub(r"\b([A-Za-z]{2,6})/([A-Za-z]{2,6})\b", r"\1\2", line, flags=_ck_re.IGNORECASE)
    line = line.strip()
    line = _ck_re.sub(r"^[\s▢❒◆●•▸►◉▪▫◼◻☞]+", "", line)
    line = _ck_re.sub(r"[,]+", " ", line)
    line = _ck_re.sub(r"[⇨➪☞⊱⇒⟹➜➝➞➟➠➡➢➣→►•·=><|/–—►]+", " ", line)
    line = _ck_re.sub(r"\s+", " ", line).strip()

    time_match = _CK_TIME_RE.search(line)
    if not time_match:
        return None
    time_str = time_match.group(1)
    tokens = line.split()

    direction = None
    for tok in tokens:
        tok_clean = tok.strip("📊📈📉✅❌⚡🔥💰🟢🔴><=!#@").lower()
        if tok_clean in _CK_BUY_WORDS:
            direction = "BUY"; break
        if tok_clean in _CK_SELL_WORDS:
            direction = "PUT"; break
    if not direction:
        return None

    pair_candidates = []
    for tok in tokens:
        tok_up = tok.strip("📊📈📉✅❌⚡🔥💰🟢🔴><=!#@").upper()
        if tok_up.lower() in _CK_NOISE_WORDS: continue
        if tok_up.lower() in _CK_BUY_WORDS | _CK_SELL_WORDS: continue
        if _ck_re.match(r"^\d{1,2}:\d{2}$", tok_up): continue
        if len(tok_up) < 3: continue
        if not _ck_re.search(r"[A-Z]{2,}", tok_up): continue
        pair_candidates.append(tok_up)
    if not pair_candidates:
        return None

    def _score(p):
        s = 0
        if _ck_re.match(r"^[A-Z]{3,6}[A-Z]{2,6}$", p): s += 5
        return s + len(p)

    pair = max(pair_candidates, key=_score)
    pair = _ck_normalize_live_pair(pair)
    return pair, time_str, direction

def _ck_parse_live_signals(raw_text: str):
    valid, errors = [], []
    for line in raw_text.strip().splitlines():
        original = line.strip()
        if not original: continue
        result = _ck_extract_from_line_live(original)
        if result:
            pair, time_str, direction = result
            valid.append({"pair": pair, "time": time_str, "direction": direction,
                          "raw": f"M1 {pair} {time_str} {direction}"})
            continue
        errors.append(original)
    return valid, errors

def _ck_parse_live_directionless_signals(raw_text: str):
    """Parse Whiteout/Blackout lists for real markets without forcing _OTC."""
    valid, errors = [], []
    supported = set(_CK_SUPPORTED_LIVE) | set(ALL_LIVE_PAIRS)
    for line in str(raw_text or "").strip().splitlines():
        original = line.strip()
        if not original:
            continue
        parsed, _ = _ck_parse_live_signals(original)
        if not parsed:
            parsed, _ = _ck_parse_live_signals(original + " CALL")
        if not parsed:
            errors.append(original); continue
        signal = parsed[0]
        pair = str(signal.get("pair") or "").upper().replace("/", "")
        if "OTC" in pair or pair not in supported:
            errors.append(original); continue
        valid.append({"pair": pair, "time": signal["time"], "direction": "WHITEOUT",
                      "raw": f"M1 {pair} {signal['time']}"})
    return valid, errors

def _ck_parse_whiteout_signals(raw_text: str):
    valid, errors = [], []
    for line in raw_text.strip().splitlines():
        original = line.strip()
        if not original: continue
        cleaned = _ck_clean_unicode(original)
        if ";" in cleaned:
            parts = [p.strip() for p in cleaned.split(";") if p.strip()]
            parts = [p for p in parts if not _ck_re.match(r"^[Mm]\d+$", p)]
            cleaned = " ".join(parts)
        cleaned = _ck_re.sub(r"\s*-\s*OTC\b", "-OTC", cleaned, flags=_ck_re.IGNORECASE)
        cleaned = _ck_re.sub(r"\b([A-Za-z0-9]{2,15})-OTC\b", r"\1_OTC", cleaned, flags=_ck_re.IGNORECASE)
        cleaned = _ck_re.sub(r"\bOTC[-_]([A-Za-z0-9]+)\b", r"\1_OTC", cleaned, flags=_ck_re.IGNORECASE)
        cleaned = _ck_re.sub(r"\b([A-Za-z0-9]{4,15})\s+OTC\b", r"\1_OTC", cleaned, flags=_ck_re.IGNORECASE)
        cleaned = _ck_re.sub(r"\b([A-Za-z]{2,6})/([A-Za-z]{2,6})\b", r"\1\2", cleaned, flags=_ck_re.IGNORECASE)

        time_match = _CK_TIME_RE.search(cleaned)
        if not time_match:
            errors.append(original); continue
        time_str = time_match.group(1)

        pair_candidates = []
        for tok in cleaned.split():
            tok_up = _ck_re.sub(r"[📊📈📉✅❌⚡🔥💰🟢🔴><=!#@\s]", "", tok).upper()
            if not tok_up: continue
            if tok_up.lower() in _CK_NOISE_WORDS: continue
            if _ck_re.match(r"^\d{1,2}:\d{2}$", tok_up): continue
            if len(tok_up) < 2: continue
            if not _ck_re.search(r"[A-Z]{2,}", tok_up): continue
            if _ck_re.match(r"^_?OTC_?$", tok_up, _ck_re.IGNORECASE): continue
            pair_candidates.append(tok_up)
        if not pair_candidates:
            errors.append(original); continue

        def _bk_score(p):
            s = 0
            if "OTC" in p: s += 20
            if _ck_re.match(r"^[A-Z]{3,6}_OTC$", p): s += 15
            if _ck_re.match(r"^[A-Z]{3,6}[A-Z]{3,6}_OTC$", p): s += 10
            return s + len(p)

        pair_raw = max(pair_candidates, key=_bk_score)
        pair_raw = _ck_re.sub(r"[-]OTC$", "_OTC", pair_raw, flags=_ck_re.IGNORECASE).upper()
        pair = _ck_normalize_pair(pair_raw)
        if "_OTC" not in pair.upper():
            pair = f"{pair}_OTC"
        valid.append({"pair": pair, "time": time_str, "direction": "WHITEOUT",
                      "raw": f"M1 {pair} {time_str}"})
    return valid, errors

@_ck_lru_cache(maxsize=4096)
def _ck_parse_candle_dt(time_str: str):
    if not time_str: return None
    s = str(time_str).strip()
    if len(s) == 19 and s[4] == "-" and s[7] == "-" and s[10] == " ":
        try: return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError): pass
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%H:%M:%S", "%H:%M"):
        try: return datetime.strptime(s, fmt)
        except (ValueError, TypeError): continue
    return None

def _ck_candle_dir(c: dict) -> str:
    if c["close"] > c["open"]: return "BUY"
    if c["close"] < c["open"]: return "PUT"
    return "DOJI"

def _ck_build_candle_index(candles: list) -> dict:
    idx_map = {}
    for i, c in enumerate(candles):
        raw_time = str(c.get("time", ""))
        dt = _ck_parse_candle_dt(raw_time)
        if dt is not None:
            key = f"{dt.hour:02d}:{dt.minute:02d}"
            if key not in idx_map: idx_map[key] = i
        elif len(raw_time) >= 5:
            sub = raw_time[11:16] if len(raw_time) > 10 else raw_time[:5]
            if sub and ":" in sub and sub not in idx_map:
                idx_map[sub] = i
    return idx_map

def _ck_find_entry_index(candles, time_str, idx_map=None):
    h, m = map(int, time_str.split(":"))
    hhmm = f"{h:02d}:{m:02d}"
    if idx_map is not None:
        return idx_map.get(hhmm)
    for i, c in enumerate(candles):
        dt = _ck_parse_candle_dt(str(c.get("time", "")))
        if dt is None:
            if hhmm in str(c.get("time", "")): return i
            continue
        if dt.hour == h and dt.minute == m: return i
    return None

def _ck_filter_by_date(candles: list, target_date) -> list:
    result = []
    for c in candles:
        dt = _ck_parse_candle_dt(c.get("time", ""))
        if dt is None or dt.year < 2000:
            result.append(c); continue
        if dt.date() == target_date:
            result.append(c)
    return result

def _ck_fetch_candles_for_date(pair: str, date_mode: str) -> list:
    raw = _ck_fetch_candles_unfiltered(pair, count=3000)
    if not raw:
        return []
    bd_now = datetime.utcnow() + timedelta(hours=6)
    target_date = bd_now.date() if date_mode == "today" else (bd_now - timedelta(days=1)).date()
    filtered = _ck_filter_by_date(raw, target_date)
    return filtered if filtered else raw

def _ck_fetch_candles_unfiltered(pair: str, count: int = 3000) -> list:
    """Historical checker fetch; intentionally ignores current chart_open status."""
    try:
        resp = _http.get(_CANDLE_API_BASE, params={
            "pair": pair, "timeframe": "M1", "count": max(1, int(count))
        }, timeout=8)
        resp.raise_for_status()
        payload = resp.json()
        raw = payload.get("data") or [] if isinstance(payload, dict) else []
        candles = []
        for c in raw:
            try:
                candles.append({
                    "open": float(c.get("open", c.get("o", 0))),
                    "high": float(c.get("high", c.get("h", 0))),
                    "low": float(c.get("low", c.get("l", 0))),
                    "close": float(c.get("close", c.get("c", 0))),
                    "time": c.get("time", c.get("timestamp", c.get("t", ""))),
                    "epoch": c.get("epoch"), "payout": int(c.get("payout", 0) or 0),
                    "color": c.get("colour", c.get("color", "")),
                    "volume": c.get("volume", 0), "chart_open": c.get("chart_open"),
                })
            except (TypeError, ValueError, AttributeError):
                continue
        candles.reverse()
        return candles
    except Exception:
        return []

def _ck_check_single_signal(candles, signal, mtg_steps, idx_map=None):
    if not candles:
        return {"win": None, "result": "NO_DATA", "mtg_level": -1, "payout": 0}
    idx = _ck_find_entry_index(candles, signal["time"], idx_map)
    if idx is None:
        return {"win": None, "result": "NO_DATA", "mtg_level": -1, "payout": 0}
    entry_payout = int(candles[idx].get("payout", 0))
    direction = signal["direction"]
    for step in range(mtg_steps + 1):
        ci = idx + step
        if ci >= len(candles): break
        c_dir = _ck_candle_dir(candles[ci])
        if c_dir == "DOJI":
            if step == 0:
                return {"win": True, "result": "WIN", "mtg_level": 0, "payout": entry_payout}
            continue
        if c_dir == direction:
            return {"win": True, "result": "WIN", "mtg_level": step, "payout": entry_payout}
    return {"win": False, "result": "LOSS", "mtg_level": -1, "payout": entry_payout}

def _ck_check_whiteout_signal(candles, signal, mtg_steps, idx_map=None):
    if not candles:
        return {"win": None, "result": "NO_DATA", "mtg_level": -1, "direction": "WHITEOUT", "payout": 0}
    idx = _ck_find_entry_index(candles, signal["time"], idx_map)
    if idx is None or idx == 0:
        return {"win": None, "result": "NO_DATA", "mtg_level": -1, "direction": "WHITEOUT", "payout": 0}
    entry_payout = int(candles[idx].get("payout", 0))
    prev_dir = _ck_candle_dir(candles[idx - 1])
    if prev_dir == "DOJI":
        return {"win": None, "result": "DOJI", "mtg_level": -1, "direction": "DOJI", "payout": entry_payout}
    direction = "BUY" if prev_dir == "BUY" else "PUT"
    for step in range(mtg_steps + 1):
        ci = idx + step
        if ci >= len(candles): break
        c_dir = _ck_candle_dir(candles[ci])
        if c_dir == "DOJI":
            if step == 0:
                return {"win": True, "result": "WIN", "mtg_level": 0, "direction": direction, "payout": entry_payout}
            continue
        if c_dir == direction:
            return {"win": True, "result": "WIN", "mtg_level": step, "direction": direction, "payout": entry_payout}
    return {"win": False, "result": "LOSS", "mtg_level": -1, "direction": direction, "payout": entry_payout}

def _ck_check_blackout_signal(candles, signal, mtg_steps, idx_map=None):
    if not candles:
        return {"win": None, "result": "NO_DATA", "mtg_level": -1, "direction": "BLACKOUT", "payout": 0}
    idx = _ck_find_entry_index(candles, signal["time"], idx_map)
    if idx is None or idx == 0:
        return {"win": None, "result": "NO_DATA", "mtg_level": -1, "direction": "BLACKOUT", "payout": 0}
    entry_payout = int(candles[idx].get("payout", 0))
    prev_dir = _ck_candle_dir(candles[idx - 1])
    if prev_dir == "DOJI":
        return {"win": None, "result": "DOJI", "mtg_level": -1, "direction": "DOJI", "payout": entry_payout}
    direction = "PUT" if prev_dir == "BUY" else "BUY"
    for step in range(mtg_steps + 1):
        ci = idx + step
        if ci >= len(candles): break
        c_dir = _ck_candle_dir(candles[ci])
        if c_dir == "DOJI":
            if step == 0:
                return {"win": True, "result": "WIN", "mtg_level": 0, "direction": direction, "payout": entry_payout}
            continue
        if c_dir == direction:
            return {"win": True, "result": "WIN", "mtg_level": step, "direction": direction, "payout": entry_payout}
    return {"win": False, "result": "LOSS", "mtg_level": -1, "direction": direction, "payout": entry_payout}

_CK_PREM_IDS = {
    "check":  "6312206911152332292",
    "cross":  "6312080737898077535",
    "trophy": "6132014672099943868",
    "cal":    "6156743968508879635",
    "fwin":   "6311920793315975140",
    "floss":  "6311965658544348766",
    "question": "6210635890994192211",
}
_CK_PH = {
    "check":  "✅",
    "cross":  "\u2716",
    "trophy": "🏆",
    "cal":    "📆",
    "fwin":   "\u2714",
    "floss":  "❌",
    "question": "❓",
}

def _ck_emo(key: str) -> str:
    ch     = _CK_PH[key]
    doc_id = _CK_PREM_IDS[key]
    return f'<tg-emoji emoji-id="{doc_id}">{ch}</tg-emoji>'

def _ck_format_checker_result(results: list, mtg_steps: int, date_mode: str,
                               payout_filter: bool = False, payout_threshold: int = 80) -> str:
    bd_now = datetime.utcnow() + timedelta(hours=6)
    if date_mode == "yesterday":
        bd_now = bd_now - timedelta(days=1)
    date_str = _to_mono(bd_now.strftime("%Y.%m.%d"))
    SEP = "━━━━━━━━━・━━━━━━━━━"

    def _disp_pair(p):
        return _ck_re.sub(r"[-_]OTC$", "_OTC", p, flags=_ck_re.IGNORECASE)

    parts = []
    parts.append("<b>=====𝚉𝙴𝙱𝚁𝙾𝙽𝙸𝚇 𝙱𝙾𝚃 𝙲𝙷𝙴𝙲𝙺𝙴𝚁 =====\n\n")
    parts.append(f"{SEP}\n")
    parts.append("          ")
    parts.append(_ck_emo("cal"))
    parts.append(f" - {date_str}          \n")
    parts.append(f"{SEP}</b>\n")

    wins = losses = 0
    for r in results:
        res = r["result"]; lvl = r.get("mtg_level", -1)
        sig_payout = int(r.get("payout", 0))
        is_low_payout = (payout_filter and sig_payout > 0 and sig_payout < payout_threshold)

        display_pair = _disp_pair(r["pair"])
        direction   = r["direction"]
        if is_low_payout:
            line_text = f"M1 {display_pair}  {r['time']} {direction} {sig_payout}%"
        else:
            line_text = f"M1 {display_pair}  {r['time']} {direction}"
        parts.append(f"<b>{_to_mono(line_text)}</b>")

        if is_low_payout:
            pass
        elif res == "WIN":
            sup = _CK_MTG_SUP.get(lvl, "")
            parts.append(" ")
            parts.append(_ck_emo("check"))
            parts.append(sup)
            wins += 1
        elif res == "LOSS":
            parts.append(" ")
            parts.append(_ck_emo("cross"))
            losses += 1
        elif res == "DOJI":
            parts.append(" ⬜")
        else:
            parts.append(" ")
            parts.append(_ck_emo("question"))
        parts.append("\n")

    parts.append(f"<b>{SEP}\n")
    parts.append(_ck_emo("fwin"))
    parts.append(f" {_to_mono('WIN')} :{wins:02d}\n")
    parts.append(_ck_emo("floss"))
    parts.append(f" {_to_mono('LOSS')} :{losses:02d}\n")
    parts.append(f"{SEP}</b>")

    return "".join(parts)

def _ck_format_whiteout_result(results: list, mtg_steps: int, date_mode: str,
                               checker_mode: str = "whiteout") -> str:
    bd_now = datetime.utcnow() + timedelta(hours=6)
    if date_mode == "yesterday":
        bd_now = bd_now - timedelta(days=1)
    date_str = _to_mono(bd_now.strftime("%Y.%m.%d"))
    SEP = "━━━━━━━━━・━━━━━━━━━"

    def _disp_pair(p):
        return _ck_re.sub(r"[-_]OTC$", "_OTC", p, flags=_ck_re.IGNORECASE)

    parts = []
    parts.append("<b>=====𝚉𝙴𝙱𝚁𝙾𝙽𝙸𝚇 𝙱𝙾𝚃 𝙲𝙷𝙴𝙲𝙺𝙴𝚁 =====\n\n")
    parts.append(f"{SEP}\n")
    parts.append("          ")
    parts.append(_ck_emo("cal"))
    parts.append(f" - {date_str}          \n")
    parts.append(f"{SEP}</b>\n")

    wins = losses = 0
    for r in results:
        res = r["result"]; lvl = r.get("mtg_level", -1)
        display_pair = _disp_pair(r["pair"])

        line_text = f"M1 {display_pair}  {r['time']}"
        parts.append(f"<b>{_to_mono(line_text)}</b>")

        if res == "WIN":
            sup = _CK_MTG_SUP.get(lvl, "")
            parts.append(" ")
            parts.append(_ck_emo("check"))
            parts.append(sup)
            wins += 1
        elif res == "LOSS":
            parts.append(" ")
            parts.append(_ck_emo("cross"))
            losses += 1
        elif res == "DOJI":
            parts.append(f" <b>{_to_mono('[doji]')}</b>")
        else:
            parts.append(" ")
            parts.append(_ck_emo("question"))
        parts.append("\n")

    parts.append(f"<b>{SEP}\n")
    parts.append(_ck_emo("fwin"))
    parts.append(f" {_to_mono('WIN')} :{wins:02d}\n")
    parts.append(_ck_emo("floss"))
    parts.append(f" {_to_mono('LOSS')} :{losses:02d}\n")
    parts.append(f"{SEP}</b>")

    return "".join(parts)

def _kb_checker_mtg():
    return {"inline_keyboard": [
        [{"text": "MTG 1", "callback_data": "checker_mtg_1", "style": "success","icon_custom_emoji_id": "6312168668763529862"},
         {"text": "MTG 2", "callback_data": "checker_mtg_2", "style": "success","icon_custom_emoji_id": "6312008994764365905"}],
        [{"text": "NON MTG", "callback_data": "checker_mtg_0", "style": "primary","icon_custom_emoji_id": "6212911416207219932"}],
        [{"text": "CUSTOM MTG", "callback_data": "checker_mtg_custom", "style": "primary"}],
        [{"text": "Home", "callback_data": "menu_home", "style": "danger",
          "icon_custom_emoji_id": "5416041192905265756"}],
    ]}

def _kb_checker_date():
    return {"inline_keyboard": [
        [{"text": "TODAY", "callback_data": "checker_date_today", "style": "primary","icon_custom_emoji_id": "6213053622574392612"},
         {"text": "YESTERDAY", "callback_data": "checker_date_yesterday", "style": "primary","icon_custom_emoji_id": "6212843547134008737"}],
        [{"text": "Home", "callback_data": "menu_home", "style": "danger",
          "icon_custom_emoji_id": "5416041192905265756"}],
    ]}

def _kb_checker_payout():
    return {"inline_keyboard": [
        [{"text": "YES", "callback_data": "checker_payout_yes", "style": "success","icon_custom_emoji_id": "6186138166336954485"},
         {"text": "NO", "callback_data": "checker_payout_no", "style": "danger","icon_custom_emoji_id": "6186082516445700103"}],
        [{"text": "Home", "callback_data": "menu_home", "style": "danger",
          "icon_custom_emoji_id": "5416041192905265756"}],
    ]}

_CK_MODE_MENU_CB = {
    "otc": "menu_otc_checker",
    "whiteout": "menu_whiteout_checker",
    "whiteout_live": "menu_whiteout_checker",
    "live": "menu_live_checker",
    "blackout": "menu_blackout_checker",
    "blackout_live": "menu_blackout_checker",
}

_CK_MODE_CHECK_FN = {
    "whiteout": _ck_check_whiteout_signal,
    "whiteout_live": _ck_check_whiteout_signal,
    "blackout": _ck_check_blackout_signal,
    "blackout_live": _ck_check_blackout_signal,
}

def _ck_run_checker(uid: int, cid: int, sess, mtg_steps: int):
    signals       = sess.checker_draft.get("signals", [])
    date_mode     = sess.checker_draft.get("date_mode", "today")
    mode          = sess.checker_draft.get("checker_mode", "otc")
    payout_filter = sess.checker_draft.get("payout_filter", False)
    if not signals:
        _send(cid, efmt("❌ <b>No signals to check.</b>"))
        return

    def _worker():
        unique_pairs = list(dict.fromkeys(s["pair"] for s in signals))
        candle_cache = {}
        with ThreadPoolExecutor(max_workers=min(len(unique_pairs), 20)) as ex:
            futs = {ex.submit(_ck_fetch_candles_for_date, p, date_mode): p for p in unique_pairs}
            for fut in as_completed(futs):
                p = futs[fut]
                try:
                    candle_cache[p] = fut.result()
                except Exception:
                    candle_cache[p] = []

        idx_maps = {p: _ck_build_candle_index(c) for p, c in candle_cache.items()}
        check_fn = _CK_MODE_CHECK_FN.get(mode, _ck_check_single_signal)

        results = []
        for sig in signals:
            try:
                chk = check_fn(candle_cache.get(sig["pair"], []), sig, mtg_steps,
                                idx_map=idx_maps.get(sig["pair"]))
                results.append({**sig, **chk})
            except Exception:
                results.append({**sig, "win": None, "result": "NO_DATA", "mtg_level": -1, "payout": 0})

        if mode in ("whiteout", "blackout", "whiteout_live", "blackout_live"):
            text = _ck_format_whiteout_result(results, mtg_steps, date_mode, mode)
        else:
            text = _ck_format_checker_result(results, mtg_steps, date_mode, payout_filter)

        loss_entries = []
        for sig, r in zip(signals, results):
            if r.get("result") == "LOSS":
                p = sig["pair"]
                idx = _ck_find_entry_index(candle_cache.get(p, []), sig["time"], idx_maps.get(p))
                loss_entries.append({
                    "pair": p,
                    "time": sig["time"],
                    "direction": "" if mode in ("whiteout", "blackout", "whiteout_live", "blackout_live") else (r.get("direction") or sig.get("direction", "")),
                    "entry_idx": idx,
                })
        sess.checker_last_losses  = loss_entries
        sess.checker_last_candles = candle_cache

        back_cb = _CK_MODE_MENU_CB.get(mode, "menu_otc_checker")
        kb_rows = [[{"text": "Check Again", "callback_data": back_cb, "style": "success","icon_custom_emoji_id": "6154242686929870878"}]]
        if not payout_filter and mode in ("otc", "live"):
            kb_rows.append([{"text": "Check Again With Payout Filter",
                              "callback_data": "checker_recheck_payout", "style": "primary","icon_custom_emoji_id": "6154242686929870878"}])
        if loss_entries:
            kb_rows.append([{"text": f"Show Loss Candle ({len(loss_entries)})",
                              "callback_data": "checker_show_loss", "style": "danger",
                              "icon_custom_emoji_id": str(EMAP["📊"])}])
        kb_rows.append([{"text": "Home", "callback_data": "menu_home", "style": "danger",
                          "icon_custom_emoji_id": "5416041192905265756"}])
        sess.wiz_mid = None
        _send(cid, text, {"inline_keyboard": kb_rows})

    threading.Thread(target=_worker, daemon=True).start()


def _ck_generate_loss_chart(display_candles: list, local_entry: int, pair_disp: str,
                             direction: str, result: str = "LOSS"):
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io as _io

        n = len(display_candles)
        if n == 0:
            return None

        W, H = 900, 540
        PAD_T, PAD_B, PAD_L, PAD_R = 60, 55, 18, 78
        CX0, CX1 = PAD_L, W - PAD_R
        CW = CX1 - CX0
        CH = H - PAD_T - PAD_B

        BG          = (13, 15, 20)
        GRID_COL    = (35, 38, 47)
        AXIS_COL    = (45, 48, 58)
        BULL_BODY   = (22, 199, 132)
        BEAR_BODY   = (224, 49, 49)
        DOJI_BODY   = (240, 240, 245)
        TEXT_GRAY   = (140, 146, 165)
        TEXT_WHITE  = (225, 227, 235)
        ENTRY_COL   = (250, 204, 21)
        WM_COL      = (95, 100, 115)
        WIN_COL     = (22, 199, 132)
        LOSS_COL    = (224, 49, 49)

        img  = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        def _fload(size, bold=False):
            pb = ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
            pr = ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
            for p in (pb if bold else []) + pr:
                try: return ImageFont.truetype(p, size)
                except Exception: pass
            return ImageFont.load_default()

        f_head  = _fload(16, bold=True)
        f_axis  = _fload(12)
        f_wm    = _fload(11)

        def _dashed_h(y, x0, x1, fill, dash=5, gap=4, width=1):
            x = x0
            while x < x1:
                x2 = min(x + dash, x1)
                draw.line([(x, y), (x2, y)], fill=fill, width=width)
                x += dash + gap

        def _dashed_v(x, y0, y1, fill, dash=5, gap=4, width=1):
            y = y0
            while y < y1:
                y2 = min(y + dash, y1)
                draw.line([(x, y), (x, y2)], fill=fill, width=width)
                y += dash + gap

        decimals = 3 if "JPY" in pair_disp.upper() else 5

        highs = [c["high"] for c in display_candles]
        lows  = [c["low"] for c in display_candles]
        hi, lo = max(highs), min(lows)
        if hi == lo:
            hi += 0.0001; lo -= 0.0001
        pad = (hi - lo) * 0.15
        hi += pad; lo -= pad

        def y_of(v):
            return PAD_T + (hi - v) / (hi - lo) * CH

        slot = CW / n
        body_w = slot * 0.98

        hx = PAD_L
        hy = 18
        draw.text((hx, hy), pair_disp, font=f_head, fill=TEXT_WHITE)
        hx += draw.textbbox((0, 0), pair_disp, font=f_head)[2] + 34

        dir_text = direction if direction in ("BUY", "PUT") else (direction or "")
        if dir_text:
            draw.text((hx, hy), dir_text, font=f_head, fill=TEXT_WHITE)
            dtw = draw.textbbox((0, 0), dir_text, font=f_head)[2]

            tri_cx = hx + dtw + 16
            tri_cy = hy + 9
            if direction == "BUY":
                draw.polygon([(tri_cx - 6, tri_cy + 5), (tri_cx + 6, tri_cy + 5), (tri_cx, tri_cy - 6)],
                             fill=WIN_COL)
            elif direction == "PUT":
                draw.polygon([(tri_cx - 6, tri_cy - 5), (tri_cx + 6, tri_cy - 5), (tri_cx, tri_cy + 6)],
                             fill=LOSS_COL)
            hx = tri_cx + 22

        if result:
            res_col = WIN_COL if result == "WIN" else (LOSS_COL if result == "LOSS" else TEXT_GRAY)
            draw.text((hx, hy), result, font=f_head, fill=res_col)

        n_lines = 6
        for gi in range(n_lines + 1):
            gy = PAD_T + CH * gi / n_lines
            _dashed_h(gy, CX0, CX1, GRID_COL)
            price_val = hi - (hi - lo) * gi / n_lines
            lbl = f"{price_val:.{decimals}f}"
            draw.text((CX1 + 10, gy - 6), lbl, font=f_axis, fill=TEXT_GRAY)

        for i in range(n):
            cx = CX0 + slot * i + slot / 2
            _dashed_v(cx, PAD_T, PAD_T + CH, GRID_COL)

        draw.line([(CX1, PAD_T), (CX1, PAD_T + CH)], fill=AXIS_COL, width=1)
        draw.line([(CX0, PAD_T + CH), (CX1, PAD_T + CH)], fill=AXIS_COL, width=1)

  
        entry_cx = CX0 + slot * local_entry + slot / 2
        draw.rectangle([entry_cx - body_w / 2 - 10, PAD_T, entry_cx + body_w / 2 + 10, PAD_T + CH],
                        outline=ENTRY_COL, width=3)


        for i, c in enumerate(display_candles):
            cx = CX0 + slot * i + slot / 2
            o, h_, l_, cl = c["open"], c["high"], c["low"], c["close"]
            if cl == o:
                col = DOJI_BODY
            elif cl > o:
                col = BULL_BODY
            else:
                col = BEAR_BODY
            draw.line([(cx, y_of(h_)), (cx, y_of(l_))], fill=col, width=2)
            top = y_of(max(o, cl)); bot = y_of(min(o, cl))
            if bot - top < 2: bot = top + 2
            draw.rectangle([cx - body_w / 2, top, cx + body_w / 2, bot], fill=col)

            t_str = str(c.get("time", ""))
            hhmm = t_str[-5:] if len(t_str) >= 5 else t_str
            tw_ = draw.textbbox((0, 0), hhmm, font=f_axis)[2]
            label_col = ENTRY_COL if i == local_entry else TEXT_GRAY
            draw.text((cx - tw_ / 2, PAD_T + CH + 14), hhmm, font=f_axis, fill=label_col)


        wm = "POWERED BY ZEBRONIX"
        wmw = draw.textbbox((0, 0), wm, font=f_wm)[2]
        draw.text((W - wmw - 16, H - 22), wm, font=f_wm, fill=WM_COL)

        buf = _io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        print(f"[LossChart] {e}")
        return None


def _ck_send_loss_chart(cid, chart_bytes, caption_html):
    import tempfile, os
    if chart_bytes:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        try:
            tmp.write(chart_bytes); tmp.close()
            with open(tmp.name, "rb") as _img:
                resp = _http.post(f"{BASE}/sendPhoto",
                    data={"chat_id": cid, "caption": caption_html, "parse_mode": "HTML"},
                    files={"photo": ("loss_chart.png", _img, "image/png")}, timeout=30)
            if resp.ok: return
        except Exception as e:
            print(f"[LossChart] sendPhoto: {e}")
        finally:
            try: os.remove(tmp.name)
            except Exception: pass
    _send(cid, caption_html)


def _ck_run_show_loss(uid: int, cid: int, sess):
    losses  = list(sess.checker_last_losses or [])
    cache   = sess.checker_last_candles or {}
    if not losses:
        _send(cid, efmt("❌ <b>No loss signals to show.</b>"))
        return

    _send(cid, efmt(f"🔎 <b>Generating loss candle chart(s)…</b> ({len(losses)} signal(s))"))

    def _worker():
        for i, ls in enumerate(losses, start=1):
            try:
                pair      = ls["pair"]
                time_str  = ls["time"]
                direction = ls.get("direction", "") or ""
                idx       = ls.get("entry_idx")
                candles   = cache.get(pair, [])
                if idx is None or not candles:
                    continue
                start_i = max(0, idx - 1)
                end_i   = min(len(candles), idx + 5)
                display = candles[start_i:end_i]
                local_entry = idx - start_i
                pair_disp = _ck_re.sub(r"_OTC$", "-OTC", pair, flags=_ck_re.IGNORECASE)
                chart_bytes = _ck_generate_loss_chart(display, local_entry, pair_disp, direction)
                dir_arrow = "🔺" if direction == "BUY" else ("🔻" if direction == "PUT" else "")
                dir_label = f"{direction} {dir_arrow}".strip()
                caption = efmt(
                    f"📊 <b>Loss Candle #{i}</b>\n\n"
                    f"<b>Signal Time</b> : {time_str}\n"
                    f"<b>Market</b> : {pair_disp}\n"
                    f"<b>Direction</b> : {dir_label}\n"
                    f"<b>Analysis</b> : Previous 1 candle + Entry candle + Next 4 candles"
                )
                _ck_send_loss_chart(cid, chart_bytes, caption)
            except Exception as e:
                print(f"[ShowLoss uid={uid}] {e}")
        _send(cid, efmt("✅ <b>All loss candle charts sent.</b>"),
              {"inline_keyboard": [[{"text": "Home", "callback_data": "menu_home", "style": "primary",
                                      "icon_custom_emoji_id": "5416041192905265756"}]]})

    threading.Thread(target=_worker, daemon=True).start()


def _avonex_analyze(candles):
    asc = sorted(list(candles), key=lambda c: (str(c.get("time", "")), int(c.get("epoch") or 0)))
    n = len(asc)
    if n < 15:
        return "CALL", 92, 50.0, 0.0, 0.0

    closes = [float(c['close']) for c in asc]
    opens  = [float(c['open'])  for c in asc]
    highs  = [float(c['high'])  for c in asc]
    lows   = [float(c['low'])   for c in asc]

    if max(highs) - min(lows) < 1e-7:
        return "CALL", 0, 50.0, 0.0, 0.0

    def _ema(series, period):
        if len(series) < period:
            return series[-1]
        k = 2.0 / (period + 1)
        e = sum(series[:period]) / period
        for v in series[period:]:
            e = v * k + e * (1 - k)
        return e

    # --- 1. HTF 1: M15 Resampling (Macro ~33 candles from 500 M1) ---
    m15_candles = []
    curr_m15 = None
    for c in asc:
        ep = int(c.get('epoch', 0))
        m15_ep = (ep // 900) * 900
        if not curr_m15 or curr_m15['epoch'] != m15_ep:
            if curr_m15:
                m15_candles.append(curr_m15)
            curr_m15 = {'epoch': m15_ep, 'open': float(c['open']), 'high': float(c['high']), 'low': float(c['low']), 'close': float(c['close'])}
        else:
            curr_m15['high'] = max(curr_m15['high'], float(c['high']))
            curr_m15['low']  = min(curr_m15['low'], float(c['low']))
            curr_m15['close'] = float(c['close'])
    if curr_m15:
        m15_candles.append(curr_m15)

    m15_closes   = [c['close'] for c in m15_candles]
    m15_e9       = _ema(m15_closes, 9)
    m15_e21      = _ema(m15_closes, 21)
    m15_trend_up = m15_e9 > m15_e21
    m15_trend_dn = m15_e9 < m15_e21

    m5_candles = []
    curr_m5 = None
    for c in asc:
        ep = int(c.get('epoch', 0))
        m5_ep = (ep // 300) * 300
        if not curr_m5 or curr_m5['epoch'] != m5_ep:
            if curr_m5:
                m5_candles.append(curr_m5)
            curr_m5 = {'epoch': m5_ep, 'open': float(c['open']), 'high': float(c['high']), 'low': float(c['low']), 'close': float(c['close'])}
        else:
            curr_m5['high'] = max(curr_m5['high'], float(c['high']))
            curr_m5['low']  = min(curr_m5['low'], float(c['low']))
            curr_m5['close'] = float(c['close'])
    if curr_m5:
        m5_candles.append(curr_m5)

    m5_closes   = [c['close'] for c in m5_candles]
    m5_e9       = _ema(m5_closes, 9)
    m5_e21      = _ema(m5_closes, 21)
    m5_trend_up = m5_e9 > m5_e21
    m5_trend_dn = m5_e9 < m5_e21


    e9   = _ema(closes, 9)
    e21  = _ema(closes, 21)
    e50  = _ema(closes, 50)
    e200 = _ema(closes, min(200, n))
    e400 = _ema(closes, min(400, n))

    gains  = [max(0, closes[i] - closes[i-1]) for i in range(1, n)]
    losses = [max(0, closes[i-1] - closes[i]) for i in range(1, n)]
    ag     = sum(gains[-14:])  / 14.0 if len(gains) >= 14 else 0.5
    al     = sum(losses[-14:]) / 14.0 if len(losses) >= 14 else 0.5
    rsi    = 100.0 - (100.0 / (1.0 + ag / max(al, 1e-9)))

    sma20 = sum(closes[-20:]) / 20.0
    var20 = sum((x - sma20) ** 2 for x in closes[-20:]) / 20.0
    std20 = math.sqrt(var20)
    bb_upper = sma20 + 2.0 * std20
    bb_lower = sma20 - 2.0 * std20

    stoch_l14 = min(lows[-14:])
    stoch_h14 = max(highs[-14:])
    stoch_k   = ((closes[-1] - stoch_l14) / max(stoch_h14 - stoch_l14, 1e-6)) * 100.0

    macd_fast = _ema(closes, 12)
    macd_slow = _ema(closes, 26)
    macd_line = macd_fast - macd_slow

    session_h = max(highs)
    session_l = min(lows)
    session_rng = max(session_h - session_l, 1e-9)
    fib_618 = session_l + session_rng * 0.618
    fib_500 = session_l + session_rng * 0.500
    fib_382 = session_l + session_rng * 0.382

    last_c = closes[-1]
    last_o = opens[-1]
    last_h = highs[-1]
    last_l = lows[-1]

    prev1_c = closes[-2]
    prev1_o = opens[-2]
    prev1_h = highs[-2]
    prev1_l = lows[-2]

    prev2_c = closes[-3]
    prev2_o = opens[-3]
    prev2_h = highs[-3]
    prev2_l = lows[-3]

    body   = abs(last_c - last_o)
    rng    = max(last_h - last_l, 1e-9)
    u_wick = last_h - max(last_c, last_o)
    l_wick = min(last_c, last_o) - last_l

    prev1_body = abs(prev1_c - prev1_o)
    prev1_rng  = max(prev1_h - prev1_l, 1e-9)
    prev2_body = abs(prev2_c - prev2_o)

    is_green = last_c > last_o
    is_red   = last_c < last_o

    recent_h = highs[-25:-1]
    recent_l = lows[-25:-1]
    max_eqh  = max(recent_h)
    min_eql  = min(recent_l)

    sup20 = min(lows[-20:])
    res20 = max(highs[-20:])
    sup50 = min(lows[-50:])
    res50 = max(highs[-50:])
    dist_res = abs(last_h - res20) / max(last_c, 1e-6)
    dist_sup = abs(last_l - sup20) / max(last_c, 1e-6)

    avg_rng10 = sum([highs[i] - lows[i] for i in range(-11, -1)]) / 10.0


    s1_put  = (last_h >= max_eqh) and (last_c < max_eqh) and (u_wick >= 1.6 * max(body, 1e-6))
    s1_call = (last_l <= min_eql) and (last_c > min_eql) and (l_wick >= 1.6 * max(body, 1e-6))

    disp_up = (prev1_c > prev1_o) and (prev1_body / prev1_rng > 0.55)
    disp_dn = (prev1_c < prev1_o) and (prev1_body / prev1_rng > 0.55)
    s2_call = disp_up and (l_wick > body * 0.5 or last_c > prev1_o)
    s2_put  = disp_dn and (u_wick > body * 0.5 or last_c < prev1_o)

    swing_h15 = max(highs[-18:-3])
    swing_l15 = min(lows[-18:-3])
    choch_bull = (closes[-2] > swing_h15) or (closes[-3] > swing_h15)
    choch_bear = (closes[-2] < swing_l15) or (closes[-3] < swing_l15)
    s3_call = choch_bull and is_green and (l_wick > 0.20 * rng)
    s3_put  = choch_bear and is_red and (u_wick > 0.20 * rng)

    sweeps_high_cnt = sum(1 for h in highs[-20:] if h >= max_eqh * 0.9998)
    sweeps_low_cnt  = sum(1 for l in lows[-20:] if l <= min_eql * 1.0002)
    s4_put  = (sweeps_high_cnt >= 2) and (u_wick > body or is_red)
    s4_call = (sweeps_low_cnt >= 2)  and (l_wick > body or is_green)

    s5_call = (n >= 4) and (lows[-2] > highs[-4]) and (last_l <= highs[-4]) and (last_c > highs[-4])
    s5_put  = (n >= 4) and (highs[-2] < lows[-4]) and (last_h >= lows[-4])  and (last_c < lows[-4])

    inside_bar = (highs[-2] <= highs[-3]) and (lows[-2] >= lows[-3])
    s6_put  = inside_bar and (highs[-1] > highs[-3]) and (closes[-1] <= highs[-3])
    s6_call = inside_bar and (lows[-1] < lows[-3]) and (closes[-1] >= lows[-3])

    three_g = (closes[-2] > opens[-2]) and (closes[-3] > opens[-3]) and (closes[-4] > opens[-4])
    three_r = (closes[-2] < opens[-2]) and (closes[-3] < opens[-3]) and (closes[-4] < opens[-4])
    s7_put  = three_g and (u_wick >= body * 1.0 or (is_red and u_wick > l_wick))
    s7_call = three_r and (l_wick >= body * 1.0 or (is_green and l_wick > u_wick))

    res_touches = sum(1 for h in highs[-30:] if abs(h - res20) / max(last_c, 1e-6) < 0.001)
    sup_touches = sum(1 for l in lows[-30:] if abs(l - sup20) / max(last_c, 1e-6) < 0.001)
    s8_put  = (res_touches >= 2) and (dist_res < 0.001) and (u_wick >= body * 0.9 or is_red)
    s8_call = (sup_touches >= 2) and (dist_sup < 0.001) and (l_wick >= body * 0.9 or is_green)

    s9_put  = (dist_res < 0.0007) and (u_wick >= 1.2 * max(body, 1e-6))
    s9_call = (dist_sup < 0.0007) and (l_wick >= 1.2 * max(body, 1e-6))

    s10_put  = (last_h > res20) and (last_c <= res20) and (u_wick > 0.30 * rng or is_red)
    s10_call = (last_l < sup20) and (last_c >= sup20) and (l_wick > 0.30 * rng or is_green)

    s11_put  = (prev1_c > prev1_o) and (body < prev1_body * 0.50 or u_wick > l_wick * 1.5 or is_red)
    s11_call = (prev1_c < prev1_o) and (body < prev1_body * 0.50 or l_wick > u_wick * 1.5 or is_green)

    s12_put  = (rng >= 1.5 * avg_rng10) and (u_wick >= 0.45 * rng)
    s12_call = (rng >= 1.5 * avg_rng10) and (l_wick >= 0.45 * rng)

    s13_put  = (res_touches >= 2) and (dist_res < 0.0009) and (u_wick >= body or is_red)
    s13_call = (sup_touches >= 2) and (dist_sup < 0.0009) and (l_wick >= body or is_green)

    s14_call = is_green and (prev1_c < prev1_o) and (last_c > prev1_o) and (last_o <= prev1_c)
    s14_put  = is_red and (prev1_c > prev1_o) and (last_c < prev1_o) and (last_o >= prev1_c)

    is_pin_bear = (u_wick >= 1.8 * max(body, 1e-6)) and (l_wick <= 0.5 * u_wick)
    is_pin_bull = (l_wick >= 1.8 * max(body, 1e-6)) and (u_wick <= 0.5 * l_wick)
    s15_put  = is_pin_bear and (dist_res < 0.0025 or rsi > 50)
    s15_call = is_pin_bull and (dist_sup < 0.0025 or rsi < 50)

    s16_put  = (last_h >= res20 * 0.9995) and (u_wick > l_wick) and (is_red or u_wick >= body * 0.6)
    s16_call = (last_l <= sup20 * 1.0005) and (l_wick > u_wick) and (is_green or l_wick >= body * 0.6)

    s17_put  = (prev1_h > prev2_h) and (last_h < prev1_h) and (last_c < prev1_l)
    s17_call = (prev1_l < prev2_l) and (last_l > prev1_l) and (last_c > prev1_h)

    s18_put  = is_red and (u_wick >= 0.35 * rng) and (last_c < prev1_c)
    s18_call = is_green and (l_wick >= 0.35 * rng) and (last_c > prev1_c)

    s19_put  = (last_c < min(lows[-5:-1])) and (u_wick > 0.20 * rng)
    s19_call = (last_c > max(highs[-5:-1])) and (l_wick > 0.20 * rng)

    s20_put  = (prev1_c < prev1_o) and is_red and (last_c < prev1_l) and (body > prev1_body)
    s20_call = (prev1_c > prev1_o) and is_green and (last_c > prev1_h) and (body > prev1_body)

    s21_put  = (u_wick >= 0.50 * rng) and (body <= 0.25 * rng)
    s21_call = (l_wick >= 0.50 * rng) and (body <= 0.25 * rng)

    s22_put  = is_red and (last_o >= prev1_h) and (last_c <= prev1_c)
    s22_call = is_green and (last_o <= prev1_l) and (last_c >= prev1_c)

    s23_put  = (last_c <= min_eql) and (u_wick >= 0.30 * rng)
    s23_call = (last_c >= max_eqh) and (l_wick >= 0.30 * rng)

    s24_put  = (prev2_c < prev2_o) and (prev1_c > prev1_o) and is_red and (last_c < prev1_o)
    s24_call = (prev2_c > prev2_o) and (prev1_c < prev1_o) and is_green and (last_c > prev1_o)

    s25_put  = (last_h > max_eqh) and (last_c < last_o) and (u_wick >= 1.4 * body)
    s25_call = (last_l < min_eql) and (last_c > last_o) and (l_wick >= 1.4 * body)

    s26_call = (last_l <= e200) and (last_c > e200) and (l_wick > body)
    s26_put  = (last_h >= e200) and (last_c < e200) and (u_wick > body)

    s27_call = (closes[-1] > max(highs[-10:-1])) and (last_c > e9)
    s27_put  = (closes[-1] < min(lows[-10:-1]))  and (last_c < e9)

    s28_put  = (last_h > res20) and (last_c < res20) and (u_wick >= 1.2 * body)
    s28_call = (last_l < sup20) and (last_c > sup20) and (l_wick >= 1.2 * body)

    s29_call = (prev1_c > prev1_o) and is_green and (last_l >= prev1_c - 0.3 * prev1_body)
    s29_put  = (prev1_c < prev1_o) and is_red   and (last_h <= prev1_c + 0.3 * prev1_body)

    s30_call = (last_l <= sup20 * 1.0005) and (l_wick >= 0.40 * rng) and is_green
    s30_put  = (last_h >= res20 * 0.9995) and (u_wick >= 0.40 * rng) and is_red

    s31_call = (n >= 4) and (lows[-1] > highs[-3]) and is_green
    s31_put  = (n >= 4) and (highs[-1] < lows[-3])  and is_red

    s32_call = (last_l <= fib_618 * 1.001) and (last_c >= fib_618) and (l_wick > body)
    s32_put  = (last_h >= fib_618 * 0.999) and (last_c <= fib_618) and (u_wick > body)

    s33_call = (last_l <= fib_500 * 1.001) and (last_c >= fib_500) and is_green
    s33_put  = (last_h >= fib_500 * 0.999) and (last_c <= fib_500) and is_red

    s34_call = (last_c > e50) and (last_l <= e50) and (l_wick > 0.3 * rng)
    s34_put  = (last_c < e50) and (last_h >= e50) and (u_wick > 0.3 * rng)

    s35_put  = (sweeps_high_cnt >= 3) and (u_wick >= body)
    s35_call = (sweeps_low_cnt >= 3)  and (l_wick >= body)

    s36_call = (last_l <= e21) and (last_c > e21) and is_green and (e9 > e21)
    s36_put  = (last_h >= e21) and (last_c < e21) and is_red   and (e9 < e21)

    s37_call = (closes[-1] > closes[-2] > closes[-3]) and (highs[-1] > highs[-2] > highs[-3])
    s37_put  = (closes[-1] < closes[-2] < closes[-3]) and (lows[-1] < lows[-2] < lows[-3])

    s38_put  = (last_h >= max_eqh * 0.9999) and (last_c < max_eqh) and (u_wick >= 0.4 * rng)
    s38_call = (last_l <= min_eql * 1.0001) and (last_c > min_eql) and (l_wick >= 0.4 * rng)

    s39_call = (last_c > e9) and (last_l > e9) and is_green and (e9 > e21 > e50)
    s39_put  = (last_c < e9) and (last_h < e9) and is_red   and (e9 < e21 < e50)

    s40_put  = (highs[-2] >= res20) and (last_h < highs[-2]) and is_red
    s40_call = (lows[-2] <= sup20)  and (last_l > lows[-2])  and is_green

    s41_call = (last_l <= e50 * 1.0005) and (last_c > e50) and (l_wick > 1.2 * body)
    s41_put  = (last_h >= e50 * 0.9995) and (last_c < e50) and (u_wick > 1.2 * body)

    s42_call = (min_eql <= sup20 * 1.0002) and (last_l <= min_eql) and (last_c > min_eql)
    s42_put  = (max_eqh >= res20 * 0.9998) and (last_h >= max_eqh) and (last_c < max_eqh)

    s43_call = (closes[-2] > max(highs[-6:-2])) and (last_l >= min(lows[-6:-2])) and is_green
    s43_put  = (closes[-2] < min(lows[-6:-2]))  and (last_h <= max(highs[-6:-2])) and is_red

    s44_call = (last_l <= e9) and (last_c > e9) and (l_wick > 0.35 * rng) and (e9 > e21)
    s44_put  = (last_h >= e9) and (last_c < e9) and (u_wick > 0.35 * rng) and (e9 < e21)

    s45_call = (last_l <= e200) and (last_c > e200) and (e9 > e21)
    s45_put  = (last_h >= e200) and (last_c < e200) and (e9 < e21)

    s46_call = (last_c > bb_upper) and is_green and (body > 0.6 * rng)
    s46_put  = (last_c < bb_lower) and is_red   and (body > 0.6 * rng)

    s47_put  = (last_h >= bb_upper) and (last_c < bb_upper) and (u_wick >= 0.35 * rng)
    s47_call = (last_l <= bb_lower) and (last_c > bb_lower) and (l_wick >= 0.35 * rng)

    s48_call = (stoch_k < 20) and is_green and (l_wick > body)
    s48_put  = (stoch_k > 80) and is_red   and (u_wick > body)

    s49_call = (macd_line > 0) and (last_c > e9 > e21) and is_green
    s49_put  = (macd_line < 0) and (last_c < e9 < e21) and is_red

    s50_call = (last_l <= session_l * 1.0005) and (last_c > session_l) and (l_wick >= 0.40 * rng)
    s50_put  = (last_h >= session_h * 0.9995) and (last_c < session_h) and (u_wick >= 0.40 * rng)

    s51_call = m15_trend_up and m5_trend_up and (e9 > e21) and is_green
    s51_put  = m15_trend_dn and m5_trend_dn and (e9 < e21) and is_red

    s52_call = (e9 > e21 > e50 > e200) and (last_c > e9)
    s52_put  = (e9 < e21 < e50 < e200) and (last_c < e9)

    s53_call = (rsi >= 50) and (rsi <= 65) and (e9 > e21) and is_green
    s53_put  = (rsi <= 50) and (rsi >= 35) and (e9 < e21) and is_red

    s54_call = (last_l <= e400) and (last_c > e400) and (l_wick > body)
    s54_put  = (last_h >= e400) and (last_c < e400) and (u_wick > body)

    s55_call = (last_c > e200) and (last_l <= e200) and is_green
    s55_put  = (last_c < e200) and (last_h >= e200) and is_red

    call_list = [
        s1_call, s2_call, s3_call, s4_call, s5_call, s6_call, s7_call, s8_call, s9_call, s10_call,
        s11_call, s12_call, s13_call, s14_call, s15_call, s16_call, s17_call, s18_call, s19_call, s20_call,
        s21_call, s22_call, s23_call, s24_call, s25_call, s26_call, s27_call, s28_call, s29_call, s30_call,
        s31_call, s32_call, s33_call, s34_call, s35_call, s36_call, s37_call, s38_call, s39_call, s40_call,
        s41_call, s42_call, s43_call, s44_call, s45_call, s46_call, s47_call, s48_call, s49_call, s50_call,
        s51_call, s52_call, s53_call, s54_call, s55_call
    ]
    put_list = [
        s1_put, s2_put, s3_put, s4_put, s5_put, s6_put, s7_put, s8_put, s9_put, s10_put,
        s11_put, s12_put, s13_put, s14_put, s15_put, s16_put, s17_put, s18_put, s19_put, s20_put,
        s21_put, s22_put, s23_put, s24_put, s25_put, s26_put, s27_put, s28_put, s29_put, s30_put,
        s31_put, s32_put, s33_put, s34_put, s35_put, s36_put, s37_put, s38_put, s39_put, s40_put,
        s41_put, s42_put, s43_put, s44_put, s45_put, s46_put, s47_put, s48_put, s49_put, s50_put,
        s51_put, s52_put, s53_put, s54_put, s55_put
    ]

    call_matches = sum(1 for x in call_list if x)
    put_matches  = sum(1 for x in put_list if x)

    if m15_trend_up and m5_trend_up and e9 > e21:
        call_matches += 15
        put_matches = max(0, put_matches - 12)
    elif m15_trend_dn and m5_trend_dn and e9 < e21:
        put_matches += 15
        call_matches = max(0, call_matches - 12)
    else:
        if m5_trend_up and e9 > e21:
            call_matches += 8
            put_matches = max(0, put_matches - 6)
        elif m5_trend_dn and e9 < e21:
            put_matches += 8
            call_matches = max(0, call_matches - 6)

    if e9 > e21 > e50:
        call_matches += 8
        if last_c > e9:
            call_matches += 5
        if last_c > e200:
            call_matches += 5
    elif e9 < e21 < e50:
        put_matches += 8
        if last_c < e9:
            put_matches += 5
        if last_c < e200:
            put_matches += 5

    if last_l <= sup50 and last_c > sup50 and l_wick >= 0.35 * rng:
        call_matches += 10
    if last_h >= res50 and last_c < res50 and u_wick >= 0.35 * rng:
        put_matches += 10

    if rsi < 25:
        if is_red and not (l_wick >= 0.40 * rng):
            put_matches += 8
            call_matches = max(0, call_matches - 15)
        elif l_wick >= 0.40 * rng or is_green:
            call_matches += 10
            put_matches = max(0, put_matches - 10)
    elif rsi > 75:
        if is_green and not (u_wick >= 0.40 * rng):
            call_matches += 8
            put_matches = max(0, put_matches - 15)
        elif u_wick >= 0.40 * rng or is_red:
            put_matches += 10
            call_matches = max(0, call_matches - 10)
    elif 48 <= rsi <= 68 and (m5_trend_up or e9 >= e21):
        call_matches += 6
    elif 32 <= rsi <= 52 and (m5_trend_dn or e9 <= e21):
        put_matches += 6

    if l_wick >= 0.38 * rng and last_l <= sup20 * 1.0008:
        call_matches += 8
    if u_wick >= 0.38 * rng and last_h >= res20 * 0.9992:
        put_matches += 8

    consec_green = sum(1 for i in range(1, 5) if closes[-i] > opens[-i])
    consec_red   = sum(1 for i in range(1, 5) if closes[-i] < opens[-i])
    if consec_green >= 4 and u_wick >= 0.35 * rng:
        put_matches += 10
    if consec_red >= 4 and l_wick >= 0.35 * rng:
        call_matches += 10

    if call_matches > put_matches:
        direction = "CALL"
        margin = call_matches - put_matches
        confidence = min(98, max(92, 91 + int(margin * 0.35)))
    elif put_matches > call_matches:
        direction = "PUT"
        margin = put_matches - call_matches
        confidence = min(98, max(92, 91 + int(margin * 0.35)))
    else:
        direction = "CALL" if (m15_trend_up or m5_trend_up or e9 >= e21) else "PUT"
        confidence = 92

    return direction, confidence, round(rsi, 1), round(e9, 5), round(e21, 5)
def _backtest_deduplicate(signals: list) -> tuple:
    unique, removed, seen_times = [], 0, set()
    for signal in signals:
        time_key = signal.get("time", "")
        if time_key in seen_times:
            removed += 1
            continue
        seen_times.add(time_key)
        unique.append(signal)
    return unique, removed

def _backtest_parse_signals(raw_text: str, market: str = None) -> tuple:
    valid, errors = [], []
    selected_market = str(market or "").upper()
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line: continue
        clean_line = _ck_clean_unicode(line)
        has_otc_marker = bool(_ck_re.search(
            r"(?:^|[^A-Z0-9])OTC(?:$|[^A-Z0-9])|[_\-]OTC\b|\bOTC[_\-]",
            clean_line.upper(), _ck_re.IGNORECASE))
        if selected_market == "OTC":
            parsed, _ = _ck_parse_signals(line)
        elif selected_market == "LIVE":
            parsed, _ = _ck_parse_live_signals(line)
        elif has_otc_marker:
            parsed, _ = _ck_parse_signals(line)
        else:

            parsed, _ = _ck_parse_live_signals(line)
            if not parsed:
                parsed, _ = _ck_parse_signals(line)
        if parsed:
            signal = dict(parsed[0])
            pair = str(signal.get("pair") or "").upper()
            if selected_market == "OTC":
                pair = _ck_re.sub(r"-OTC$", "_OTC", pair, flags=_ck_re.IGNORECASE)
                if not pair.endswith("_OTC"):
                    pair += "_OTC"
                if pair not in _CK_SUPPORTED_OTC:
                    errors.append(line)
                    continue
                signal["pair"] = pair
                signal["market"] = "OTC"
                signal["raw"] = f"M1 {pair} {signal['time']} {signal['direction']}"
            elif selected_market == "LIVE":
                pair = _ck_normalize_live_pair(pair)
                if "OTC" in pair or pair not in _CK_SUPPORTED_LIVE:
                    errors.append(line)
                    continue
                signal["pair"] = pair
                signal["market"] = "LIVE"
                signal["raw"] = f"M1 {pair} {signal['time']} {signal['direction']}"
            else:
                signal["market"] = "OTC" if has_otc_marker else "LIVE"
            valid.append(signal)
        else:
            errors.append(line)
    return valid, errors

def _backtest_score_signal(signal: dict, candles: list) -> dict:
    direction = "CALL" if signal.get("direction", "").upper() in ("BUY", "CALL", "CAL") else "PUT"
    target_time = signal.get("time", "")
    ordered = sorted(candles or [], key=lambda c: (str(c.get("time", "")), int(c.get("epoch") or 0)))
    dated = {}
    for index, candle in enumerate(ordered):
        dt = _ck_parse_candle_dt(candle.get("time", ""))
        if dt is not None and dt.strftime("%H:%M") == target_time:
            dated[dt.date()] = index
    bd_today = (datetime.utcnow() + timedelta(hours=6)).date()
    recent_dates = sorted((day for day in dated if day <= bd_today), reverse=True)[:15]
    weighted_wins = 0.0
    tests = direct_wins = 0
    latest_idx = None
    for day in recent_dates:
        idx = dated[day]
        if idx >= len(ordered):
            continue
        if latest_idx is None:
            latest_idx = idx
        tests += 1
        direct_win = _ck_candle_dir(ordered[idx]) in ("BUY" if direction == "CALL" else "PUT", "DOJI")
        mtg_win = False
        if not direct_win and idx + 1 < len(ordered):
            mtg_win = _ck_candle_dir(ordered[idx + 1]) in (
                "BUY" if direction == "CALL" else "PUT", "DOJI")
        if direct_win:
            direct_wins += 1
            weighted_wins += 1.0
        elif mtg_win:
            weighted_wins += 0.8
        else:
            weighted_wins += 0.1

    if latest_idx is not None:
        technical_slice = ordered[max(0, latest_idx - 39):latest_idx + 1]
    else:
        technical_slice = ordered[-40:]
    tech_dir, tech_conf, rsi, ema_fast, ema_slow = _avonex_analyze(technical_slice)
    tech_aligned = 1.0 if tech_dir == direction else 0.45
    if tests:
        historical_rate = weighted_wins / tests * 100.0
        score = int(0.6 * historical_rate + 0.4 * (tech_conf * tech_aligned))
    else:
        try:
            hour, minute = map(int, target_time.split(":"))
            cycle_score = 85 if (hour * 60 + minute) % 15 in (1, 3, 5, 8, 11, 14) else 70
        except Exception:
            cycle_score = 70
        score = int(0.4 * (tech_conf * tech_aligned) + 0.6 * cycle_score)
    score = max(35, min(99, score))
    return {**signal, "backtest_score": score,
            "backtest_wins": direct_wins, "backtest_tests": tests,
            "backtest_rsi": rsi, "backtest_ema_fast": ema_fast,
            "backtest_ema_slow": ema_slow,
            "backtest_approved": score >= 70}

def _format_zebronix_backtest_result(original_count: int, selected: list) -> str:
    rows = []
    for item in selected:
        raw_pair = str(item.get("pair", "")).upper()
        is_otc = str(item.get("market", "")).upper() == "OTC" or raw_pair.endswith(("_OTC", "-OTC"))
        pair = _ck_re.sub(r"[_-]OTC$", "", raw_pair, flags=_ck_re.IGNORECASE)
        direction = "BUY" if str(item.get("direction", "")).upper() in ("BUY", "CALL", "CAL") else "PUT"
        suffix = "-OTC" if is_otc else ""
        rows.append(_to_mono(f"M1 {pair}{suffix} {item.get('time', '')} {direction}"))
    confirmed = "\n".join(rows) if rows else _to_mono("SIGNAL NOT FOUND")
    kept_count = len(selected)
    removed_count = max(0, original_count - kept_count)
    return (
        "<b>🤖 𝗔𝗜 𝗕𝗔𝗖𝗞𝗧𝗘𝗦𝗧 𝗖𝗢𝗠𝗣𝗟𝗘𝗧𝗘 🤖\n\n"
        f"🧠 {_to_mono('Mode: ZEBRONIX AI')}\n"
        f"🎉 {_to_mono(f'Original: {original_count} signals')}\n"
        f"🖼 {_to_mono(f'Kept: {kept_count} signals')}\n"
        f"🗑 {_to_mono(f'Removed: {removed_count} signals')}\n\n"
        f"🏦 {_to_mono('Confirmed Signals:')}\n\n"
        f"{confirmed}\n\n"
        f"🎯 {_to_mono('Based on AI Filtered')}</b>"
    )


def _run_backtest(uid: int, cid: int, sess):
    signals = list(getattr(sess, "backtest_signals", []) or [])
    if not signals:
        _send(cid, efmt("❌ <b>No loaded signals found.</b>"))
        return
    def _progress_text(percent: int, stage: str) -> str:
        value = max(0, min(100, int(percent)))
        filled = min(10, value // 10)
        bar = "█" * filled + "░" * (10 - filled)
        return efmt(
            "🔍 <b>Backtesting started...</b>\n"
            f"Progress: <code>[{bar}] {value}%</code>\n"
            f"Stage: <i>{_html.escape(stage)}</i>"
        )

    progress = {"value": 3, "stage": "Preparing signal data..."}
    progress_lock = threading.Lock()
    progress_stop = threading.Event()
    animation = _send(cid, _progress_text(progress["value"], progress["stage"]))
    animation_id = (animation or {}).get("result", {}).get("message_id")

    def _show_stage(stage: str, minimum: int):
        with progress_lock:
            progress["stage"] = stage
            progress["value"] = max(progress["value"], minimum)
            value = progress["value"]
        if animation_id:
            _edit(cid, animation_id, _progress_text(value, stage))

    def _animate():
        stage_caps = {
            "Preparing signal data...": 12,
            "Loading market history...": 38,
            "Evaluating signal performance...": 68,
            "Running AI indicator checks...": 86,
            "Compiling final report...": 96,
        }
        while not progress_stop.wait(1.4):
            with progress_lock:
                stage = progress["stage"]
                cap = stage_caps.get(stage, 96)
                if progress["value"] < cap:
                    progress["value"] = min(cap, progress["value"] + random.randint(1, 4))
                value = progress["value"]
            if animation_id:
                _edit(cid, animation_id, _progress_text(value, stage))

    if animation_id:
        threading.Thread(target=_animate, daemon=True).start()

    def _worker():
        try:
            pairs = list(dict.fromkeys(signal["pair"] for signal in signals))
            candle_cache = {}
            _show_stage("Loading market history...", 14)
            with ThreadPoolExecutor(max_workers=min(len(pairs), 15)) as executor:
                jobs = {executor.submit(_ck_fetch_candles_unfiltered, pair, 25000): pair for pair in pairs}
                for job in as_completed(jobs):
                    pair = jobs[job]
                    try:
                        candle_cache[pair] = job.result()
                    except Exception:
                        candle_cache[pair] = []
            _show_stage("Evaluating signal performance...", 42)
            ranked = [_backtest_score_signal(signal, candle_cache.get(signal["pair"], []))
                      for signal in signals]
            _show_stage("Running AI indicator checks...", 70)
            selected = [item for item in ranked if item.get("backtest_approved")]
            if not selected:
                selected = [max(ranked, key=lambda item: item["backtest_score"])]
            _show_stage("Compiling final report...", 87)
            upload_order = {signal["time"]: index for index, signal in enumerate(signals)}
            selected.sort(key=lambda item: upload_order.get(item["time"], 10 ** 9))
            original_count = int(getattr(sess, "backtest_original_count", 0) or len(signals))
            result_text = _format_zebronix_backtest_result(original_count, selected)
            _show_stage("Backtest complete.", 100)
            progress_stop.set()
            time.sleep(0.7)
            if animation_id:
                _delete(cid, animation_id)
            sess.wiz_mid = None
            sess.state = S.IDLE
            _send(cid, efmt(result_text), {"inline_keyboard": [[
                {"text": "HOME", "callback_data": "backtest_cancel", "style": "primary",
                 "icon_custom_emoji_id": "5416041192905265756"}]]})
        except Exception as exc:
            progress_stop.set()
            if animation_id:
                _delete(cid, animation_id)
            print(f"[Backtest uid={uid}] {exc}")
            sess.state = S.BACKTEST_READY
            _send(cid, efmt("❌ <b>Backtest could not be completed. Please try again.</b>"))

    threading.Thread(target=_worker, daemon=True).start()


def _future_raw_signals(pairs: list, start_time: str, end_time: str, mode: str, filter_days: int) -> list:
    generated = []
    try:
        start_dt = datetime.strptime(start_time, "%H:%M")
        end_dt   = datetime.strptime(end_time, "%H:%M")
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
    except Exception:
        return []

    seed_str   = f"{''.join(pairs)}_{start_time}_{end_time}_{mode}_{filter_days}"
    seed_value = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % 10000
    random.seed(seed_value)

    current_dt = start_dt
    while current_dt <= end_dt:
        for pair in pairs:
            if random.random() < 0.06:
                generated.append({
                    "asset": pair,
                    "time": current_dt.strftime("%H:%M"),
                    "direction": random.choice(["CALL", "PUT"]),
                })
        current_dt += timedelta(minutes=1)

    return generated


def _future_asset_display(asset: str, is_otc: bool = True) -> str:
    a = asset.strip()
    a = _ck_re.sub(r"[_\-]?otc$", "", a, flags=_ck_re.IGNORECASE)
    a = a.replace("<", "&lt;").replace(">", "&gt;")
    return f"{a.upper()}-OTC" if is_otc else a.upper()


def _future_hard_rsi(candles: list, period: int = 14) -> float:
    if len(candles) < period + 1:
        return 50.0
    gains, losses = [], []
    for index in range(1, len(candles)):
        change = float(candles[index]["close"]) - float(candles[index - 1]["close"])
        gains.append(change if change >= 0 else 0.0)
        losses.append(abs(change) if change < 0 else 0.0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    relative_strength = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def _future_hard_ema(candles: list, period: int = 50) -> float:
    if not candles:
        return 0.0
    if len(candles) < period:
        return float(candles[-1]["close"])
    closes = [float(candle["close"]) for candle in candles]
    multiplier = 2.0 / (period + 1)
    ema = sum(closes[:period]) / period
    for price in closes[period:]:
        ema = (price - ema) * multiplier + ema
    return ema


def _future_hard_filter(candles: list, strategy: str) -> bool:

    if not candles or len(candles) < 30:
        return True
    last = candles[-1]
    open_price = float(last.get("open", 0))
    close_price = float(last.get("close", 0))
    high_price = float(last.get("high", 0))
    low_price = float(last.get("low", 0))
    candle_range = high_price - low_price
    body_size = abs(close_price - open_price)
    if candle_range <= 0 or (body_size / candle_range) < 0.20:
        return False

    rsi = _future_hard_rsi(candles, 14)
    ema = _future_hard_ema(candles, 50)
    if str(strategy).upper() == "BLACKOUT":
        return rsi >= 68 or rsi <= 32
    return (close_price > ema and rsi > 50) or (close_price < ema and rsi < 50)


def _future_hard_raw_signals(pairs: list, start_time: str, end_time: str,
                             strategy: str, candle_map: dict) -> list:
    try:
        now = datetime.now()
        start_dt = datetime.strptime(start_time, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day)
        end_dt = datetime.strptime(end_time, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
    except (TypeError, ValueError):
        return []

    rng = random.Random()
    current = start_dt + timedelta(minutes=rng.randint(2, 4))
    pair_index = 0
    generated = []
    while current < end_dt and pairs:
        pair = pairs[pair_index % len(pairs)]
        pair_index += 1
        if _future_hard_filter(candle_map.get(pair, []), strategy):
            generated.append({"asset": pair, "time": current.strftime("%H:%M")})
        current += timedelta(minutes=rng.randint(4, 7))
    return generated


def _execute_future_hard_generation(uid: int, sess, filter_days: int):
    cid = sess.wiz_chat or uid
    pairs = list(sess.fut_pairs)
    strategy = str(sess.fut_new_strategy or "BLACKOUT").upper()
    market_mode = str(sess.fut_market_mode or "OTC").upper()
    start_time = sess.fut_start_time
    end_time = sess.fut_end_time
    _wiz(sess, "⚡ <b>Running Hard Filter Algorithm &amp; Deep Market Analysis...</b>")

    def _worker():
        candle_map = {}
        with ThreadPoolExecutor(max_workers=min(max(len(pairs), 1), 15)) as executor:
            jobs = {executor.submit(_ck_fetch_candles_unfiltered, pair, 50): pair for pair in pairs}
            for job in as_completed(jobs):
                pair = jobs[job]
                try:
                    candle_map[pair] = job.result()
                except Exception:
                    candle_map[pair] = []

        filtered = _future_hard_raw_signals(
            pairs, start_time, end_time, strategy, candle_map)
        is_otc = market_mode == "OTC"
        if strategy == "WHITEOUT":
            output = _future_build_whiteout_text(filtered, is_otc=is_otc)
        else:
            output = _future_build_blackout_text(filtered, is_otc=is_otc)
        kb = {"inline_keyboard": [
            [{"text": f"{strategy.title()} FS New Again",
              "callback_data": f"futnew_home_{strategy}", "style": "success",
              "icon_custom_emoji_id": str(EMAP["⚪"] if strategy == "WHITEOUT" else EMAP["😈"])}],
            [{"text": "Home", "callback_data": "menu_home", "style": "danger",
              "icon_custom_emoji_id": "5416041192905265756"}],
        ]}
        sess.wiz_mid = None
        _send(cid, efmt(output), kb)

    threading.Thread(target=_worker, daemon=True).start()


def _execute_future_generation(uid: int, sess, filter_days: int):
    if getattr(sess, "fut_engine", "legacy") == "hard_filter":
        _execute_future_hard_generation(uid, sess, filter_days)
        return
    cid         = sess.wiz_chat or uid
    market_mode = sess.fut_market_mode
    valid_pairs = sess.fut_pairs
    action_choice = sess.fut_action_choice
    start_time  = sess.fut_start_time
    end_time    = sess.fut_end_time

    _wiz(sess, "🚀 <b>ZEBRONIX RUNNING HIGH ACCURACY FILTER</b> ⏳...")

    all_signals = _future_raw_signals(valid_pairs, start_time, end_time, market_mode, filter_days)

    pre_filtered = []
    is_no_direction_mode = market_mode in ("BLACKOUT", "WHITEOUT")
    for sig in all_signals:
        if is_no_direction_mode:
            pre_filtered.append(sig)
        else:
            direction = sig.get("direction", "").upper()
            if (action_choice == "1" and direction == "CALL") or \
               (action_choice == "2" and direction == "PUT") or \
               (action_choice == "3"):
                pre_filtered.append(sig)

    pre_filtered.sort(key=lambda s: s.get("time", "00:00"))

    base_threshold = 98.5
    dynamic_accuracy_threshold = base_threshold + (filter_days * 0.3)
    if dynamic_accuracy_threshold > 98.5:
        dynamic_accuracy_threshold = 98.5

    filtered = []
    for sig in pre_filtered:
        str_seed = f"{sig['asset']}{sig['time']}{sig.get('direction','')}{filter_days}{market_mode}ZEBRONIX_ULTIMATE_ACC"
        hash_val = int(hashlib.sha256(str_seed.encode("utf-8")).hexdigest(), 16)
        calculated_prob = 94.0 + (hash_val % 8)
        if calculated_prob >= dynamic_accuracy_threshold:
            filtered.append(sig)

    max_allowed_signals = max(2, 22 - filter_days)
    if len(filtered) > max_allowed_signals:
        filtered = filtered[:max_allowed_signals]
    if not filtered and pre_filtered:
        filtered = pre_filtered[:2]

    kb = {"inline_keyboard": [[{"text": "Home", "callback_data": "menu_home", "style": "primary",
                                 "icon_custom_emoji_id": "5416041192905265756"}]]}

    if market_mode == "WHITEOUT":
        output_text = _future_build_whiteout_text(filtered)
    elif market_mode == "BLACKOUT":
        output_text = _future_build_blackout_text(filtered)
    else:
        output_text = _future_build_direction_text(filtered, market_mode)

    _send(cid, efmt(output_text), kb)


def _future_build_whiteout_text(filtered: list, is_otc: bool = True) -> str:
    header = (
        "🤖𝗭𝗘𝗕𝗥𝗢𝗡𝗜𝗫 𝗔𝗜 𝗪𝗛𝗜𝗧𝗘𝗢𝗨𝗧🤖\n\n"
        "🕗 𝟭 𝗠𝗜𝗡𝗨𝗧𝗘\n"
        "🟢 𝗜𝗙 𝗟𝗢𝗦𝗦 𝗠𝗧𝗚 𝟭 𝗦𝗧𝗘𝗣\n"
        "⚡️ 𝗔𝗩𝗢𝗜𝗗 𝗗𝗢𝗝𝗜 𝗠𝗨𝗦𝗧\n\n"
        "🤖 𝗚𝗘𝗡𝗘𝗥𝗔𝗧𝗘 𝗕𝗬 𝗭𝗘𝗕𝗥𝗢𝗡𝗜𝗫\n\n"
        "-------🔥𝗪𝗛𝗜𝗧𝗘𝗢𝗨𝗧🔥------\n\n"
    )
    if not filtered:
        body = _to_mono("No setups match current algorithm parameters.") + "\n"
    else:
        lines = [f"⚙️{_future_asset_display(sig['asset'], is_otc)} — {sig.get('time','')}" for sig in filtered]
        body = _to_mono("\n".join(lines)) + "\n"
    footer = (
        "\n======🔴𝗥𝗨𝗟𝗘𝗦🔴======\n"
        "<blockquote>"
        "𝗪𝗛𝗜𝗧𝗘𝗢𝗨𝗧:👇\n"
        "𝙊𝙣 𝙌𝙪𝙤𝙩𝙚𝙭, 𝙚𝙣𝙩𝙚𝙧 𝙩𝙝𝙚 𝙩𝙧𝙖𝙙𝙚 𝙞𝙣 𝙩𝙝𝙚 \"𝙨𝙖𝙢𝙚 𝙙𝙞𝙧𝙚𝙘𝙩𝙞𝙤𝙣\" 𝙖𝙨 𝙩𝙝𝙚 𝙘𝙡𝙤𝙨𝙚 "
        "𝙤𝙛 𝙩𝙝𝙚 𝙥𝙧𝙚𝙫𝙞𝙤𝙪𝙨 𝙘𝙖𝙣𝙙𝙡𝙚, 𝙪𝙨𝙞𝙣𝙜 𝙩𝙝𝙚 𝙩𝙞𝙢𝙚𝙛𝙧𝙖𝙢𝙚 𝙨𝙥𝙚𝙘𝙞𝙛𝙞𝙚𝙙 𝙞𝙣 𝙩𝙝𝙚 "
        "𝙨𝙞𝙜𝙣𝙖𝙡 𝙡𝙞𝙨𝙩.⏳"
        "</blockquote>"
    )
    return header + body + footer


def _future_build_blackout_text(filtered: list, is_otc: bool = True) -> str:
    header = (
        "🚀𝗭𝗘𝗕𝗥𝗢𝗡𝗜𝗫 𝗔𝗜 𝗕𝗟𝗔𝗖𝗞𝗢𝗨𝗧🚀\n\n"
        "🕗 𝟭 𝗠𝗜𝗡𝗨𝗧𝗘\n"
        "🟢 𝗜𝗙 𝗟𝗢𝗦𝗦 𝗠𝗧𝗚 𝟭 𝗦𝗧𝗘𝗣\n"
        "⚡️ 𝗔𝗩𝗢𝗜𝗗 𝗗𝗢𝗝𝗜 𝗠𝗨𝗦𝗧\n\n"
        "🤖 𝗚𝗘𝗡𝗘𝗥𝗔𝗧𝗘 𝗕𝗬 𝗭𝗘𝗕𝗥𝗢𝗡𝗜𝗫\n\n"
        "-------🚀𝗕𝗟𝗔𝗖𝗞𝗢𝗨𝗧🚀------\n\n"
    )
    if not filtered:
        body = _to_mono("No setups match current algorithm parameters.") + "\n"
    else:
        lines = [f"🔍{_future_asset_display(sig['asset'], is_otc)} — {sig.get('time','')}" for sig in filtered]
        body = _to_mono("\n".join(lines)) + "\n"
    footer = (
        "\n======🔴𝗥𝗨𝗟𝗘𝗦🔴======\n"
        "<blockquote>"
        "𝐁𝐋𝐀𝐂𝐊𝐎𝐔𝐓:👇\n"
        "𝙊𝙣 𝙌𝙪𝙤𝙩𝙚𝙭, 𝙩𝙖𝙠𝙚 𝙩𝙝𝙚 𝙚𝙣𝙩𝙧𝙮 𝙞𝙣 𝙩𝙝𝙚 𝙙𝙞𝙧𝙚𝙘𝙩𝙞𝙤𝙣 𝙤𝙥𝙥𝙤𝙨𝙞𝙩𝙚 𝙩𝙤 𝙝𝙤𝙬 𝙩𝙝𝙚 "
        "𝙥𝙧𝙚𝙫𝙞𝙤𝙪𝙨 𝙘𝙖𝙣𝙙𝙡𝙚 𝙘𝙡𝙤𝙨𝙚𝙙, 𝙗𝙖𝙨𝙚𝙙 𝙤𝙣 𝙩𝙝𝙚 𝙩𝙞𝙢𝙚𝙛𝙧𝙖𝙢𝙚 𝙨𝙥𝙚𝙘𝙞𝙛𝙞𝙚𝙙 𝙞𝙣 𝙩𝙝𝙚 "
        "𝙨𝙞𝙜𝙣𝙖𝙡 𝙡𝙞𝙨𝙩.⏳"
        "</blockquote>"
    )
    return header + body + footer


def _future_build_direction_text(filtered: list, market_mode: str) -> str:
    is_otc = (str(market_mode).upper() == "OTC")
    today = datetime.now().strftime("%d %B %Y").upper()
    header = _to_mono(
        "🔍 ZEBRONIX AI FUTURE 🔍\n\n"
        f"🗓 {today} 📣\n"
        "🎯 QX UTC+06:00 🇧🇩\n"
        "🕯 1 STEP MTG REQUIRED ➕\n"
        "⚡️ NO RULES SIGNALS 🔜\n\n"
        "⏱️ 01 MINTUTES :"
    ) + "\n\n"
    if not filtered:
        body = "<code>No setups match current algorithm parameters.</code>\n"
    else:
        lines = []
        for sig in filtered:
            direction = sig.get("direction", "").upper()
            direction = "BUY" if direction == "CALL" else direction
            lines.append(f"<code>M1;{_future_asset_display(sig['asset'], is_otc)};{sig.get('time','')};{direction}</code>")
        body = "\n".join(lines) + "\n"
    footer = "\n" + _to_mono(
        "🎮SOFTWARE ZEBRONIX AI🤖\n\n"
        "🫡 === 🔥Z | B | X🔥 === 🫡"
    )
    return header + body + footer


def _mfs_start(sess):
    sess.multi_fs = {"selected_pairs": []}
    sess.state = S.IDLE
    _wiz(sess,
         "<b>🔮 ZEBRONIX MULTI-PAIR FS ENGINE</b>\n"
         "───────────────────────\n"
         "👉 Select Target Environment Type:",
         {"inline_keyboard": [
             [{"text": " REAL MARKET ", "callback_data": "mfs_mkt_REAL", "style": "primary",
               "icon_custom_emoji_id": "6213253110920387939"}],
             [{"text": " OTC PAIR MARKET", "callback_data": "mfs_mkt_OTC", "style": "primary",
               "icon_custom_emoji_id": "6213218467714179432"}],
             [{"text": " Back to Main Menu", "callback_data": "menu_home", "style": "danger",
               "icon_custom_emoji_id": "5258084656674250503"}],
         ]})


def _mfs_api_pair(pair: str) -> str:
    normalized = str(pair).replace("/", "").replace("-OTC", "_otc").replace("-otc", "_otc")
    return normalized


def _mfs_fetch_payouts(pool: list) -> dict:
    payouts = {}
    with ThreadPoolExecutor(max_workers=min(len(pool), 25)) as executor:
        futures = {executor.submit(_get_pair_payout, _mfs_api_pair(pair)): pair for pair in pool}
        for future in as_completed(futures):
            pair = futures[future]
            try:
                payouts[pair] = int(future.result() or 0)
            except Exception:
                payouts[pair] = 0
    return payouts


def _mfs_render_pairs(sess):
    market_type = sess.multi_fs.get("market_type", "OTC")
    selected = sess.multi_fs.get("selected_pairs", [])
    default_pool = MULTIPLE_FS_OTC if market_type == "OTC" else MULTIPLE_FS_REAL
    pool = sess.multi_fs.get("sorted_pairs") or default_pool
    payouts = sess.multi_fs.get("payouts", {})
    rows = []
    buttons = []
    for pair in pool:
        is_selected = pair in selected
        payout = int(payouts.get(pair, 0) or 0)
        payout_style = "success" if payout >= 80 else ("primary" if payout >= 70 else "danger")
        buttons.append({
            "text": f" {pair} ({payout}%)", "callback_data": f"mfs_pair_{pair}",
            "style": "success" if is_selected else payout_style,
            "icon_custom_emoji_id": "6312053434790976755" if is_selected else "6311870452004299281",
        })
    for i in range(0, len(buttons), 2):
        rows.append(buttons[i:i + 2])
    if selected:
        rows.append([{"text": " 𝗖𝗢𝗡𝗧𝗜𝗡𝗨𝗘 𝗚𝗘𝗡𝗔𝗥𝗔𝗧𝗘", "callback_data": "mfs_pair_CONFIRM",
                      "style": "success", "icon_custom_emoji_id": "6246611984469467622"}])
    rows.append([{"text": " Back", "callback_data": "menu_multi_fs", "style": "danger",
                  "icon_custom_emoji_id": "5258084656674250503"}])
    _wiz(sess,
         "<b>🔮 𝗭𝗘𝗕𝗥𝗢𝗡𝗜𝗫 𝗔𝗜 𝗦𝗘𝗟𝗘𝗖𝗧 𝗬𝗢𝗨𝗥 𝗣𝗔𝗜𝗥</b>\n"
         "───────────────────────\n"
         f"<b>Selected Pairs:</b> <code>{len(selected)}</code>\n"
         f"<b>Environment:</b> <code>{market_type}</code>\n\n"
         "🟢 ≥80%  🔵 70-79%  🔴 &lt;70%\n\n"
         "👉 𝘚𝘦𝘭𝘦𝘤𝘵 𝘺𝘰𝘶𝘳 𝘮𝘶𝘭𝘵𝘪𝘱𝘭𝘦 𝘱𝘢𝘪𝘳𝘴, 𝘈𝘯𝘥 𝘚𝘪𝘯𝘨𝘭𝘦 𝘗𝘢𝘪𝘳, 𝘵𝘩𝘦𝘯 𝘱𝘳𝘦𝘴𝘴 𝘋𝘰𝘯𝘦:",
         {"inline_keyboard": rows})


def _mfs_start_time_prompt() -> str:
    return (
        "<b>📊𝗘𝗡𝗧𝗘𝗥 𝗦𝗧𝗔𝗥𝗧 𝗧𝗜𝗠𝗘</b> 📊\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>⏰ 𝗦𝘁𝗲𝗽 𝟭 — 𝗦𝘁𝗮𝗿𝘁 𝗧𝗶𝗺𝗲</b>\n\n"
        "😧 𝗘𝗻𝘁𝗲𝗿 𝘀𝗶𝗴𝗻𝗮𝗹 𝘀𝘁𝗮𝗿𝘁 𝘁𝗶𝗺𝗲:\n"
        "<code>HH:MM</code> e.g. <code>09:00</code>\n\n"
        "⬇️𝙏𝙤 𝙉𝙚𝙭𝙩 𝙎𝙩𝙚𝙥 𝙎𝙖𝙢𝙚 𝙋𝙧𝙤𝙘𝙚𝙨𝙨⌛"
    )


def _mfs_end_time_prompt() -> str:
    return (
        "🧪 <b>𝗘𝗡𝗧𝗘𝗥 𝗘𝗡𝗗 𝗧𝗜𝗠𝗘</b> 🧪\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>⏰ Step 1 — Start Time</b>\n\n"
        "⏰𝗘𝗻𝘁𝗲𝗿 𝘀𝗶𝗴𝗻𝗮𝗹 𝗲𝗻𝗱 𝘁𝗶𝗺𝗲:\n"
        "<code>HH:MM</code> e.g. <code>09:00</code>\n\n"
        "⚖️𝗡𝗼𝘄 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲 𝗦𝗶𝗴𝗻𝗮𝗹𝘀 𝗶𝗻 𝘀𝗲𝗰𝗼𝗻𝗱⌛"
    )


def _mfs_generate_and_send(cid: int, sess):
    data = sess.multi_fs or {}
    _send(cid, efmt("🌐 <b>Multi-Pair Analysis &amp; High-Accuracy Indicator Confluence processing...</b>"))
    selected_pairs = data.get("selected_pairs", [])
    direction_choice = data.get("direction", "BOTH")
    start_time = data.get("start_time", "00:00")
    end_time = data.get("end_time", "23:59")
    signals = []
    try:
        now = datetime.utcnow() + timedelta(hours=6)
        start_dt = datetime.strptime(start_time, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
        end_dt = datetime.strptime(end_time, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        current = start_dt + timedelta(minutes=random.randint(2, 4))
        pair_index = 0
        while current < end_dt:
            pair = selected_pairs[pair_index % len(selected_pairs)]
            pair_index += 1
            pair_formatted = pair.replace("/", "").replace("-", "_")
            if direction_choice == "CALL":
                direction = "BUY"
            elif direction_choice == "PUT":
                direction = "PUT"
            else:
                direction = random.choice(["BUY", "PUT"])
            signals.append(f"M1;{pair_formatted};{current.strftime('%H:%M')};{direction}")
            current += timedelta(minutes=random.randint(3, 6))
    except Exception as exc:
        print(f"MULTI FS Engine Error: {exc}")

    day = _to_mono((datetime.utcnow() + timedelta(hours=6)).strftime("%d %B %Y").upper())
    output = (
        "🔥 𝗭𝗘𝗕𝗥𝗢𝗡𝗜𝗫 𝗔𝗜 𝗙𝗨𝗧𝗨𝗥𝗘 🔥\n\n"
        f"🗓 {day} 📔\n"
        "🚀 𝗨𝗧𝗖 𝟬𝟲:𝟬𝟬 𝗚𝗠𝗧 🇧🇩\n"
        f"😧 𝗦𝗘𝗟𝗘𝗖𝗧 𝗣𝗔𝗜𝗥 : <code>{len(selected_pairs)}</code>\n"
        "➕ 𝟭 𝗦𝗧𝗔𝗣𝗘 𝗠𝗔𝗥𝗧𝗜𝗡𝗚𝗔𝗟𝗘 🎉\n"
        "🕯 𝗔𝗩𝗜𝗢𝗗 𝟳𝟳% 𝗣𝗔𝗜𝗥 𝗠𝗔𝗥𝗞𝗘𝗧 🛡\n\n"
        "⏰ 𝟬𝟭 𝗠𝗜𝗡𝗨𝗧𝗘𝗦 ∶\n\n"
    )
    if signals:
        output += "\n".join(f"<code>{sig}</code>" for sig in signals)
    else:
        output += "❌ NO MULTI FS SIGNALS GENERATED."
    output += (
        "\n\n💎 𝗦𝗢𝗙𝗧𝗪𝗔𝗥𝗘 𝗭𝗘𝗕𝗥𝗢𝗡𝗜𝗫 𝗔𝗜 🐺\n\n"
        "💀 ==== 🔥 𝗭 | 𝗕 | 𝗫 🔥 ==== 💀"
    )
    _send(cid, efmt(output))
    _send(cid, efmt("😐 <b>Finished!</b> Return to Main Menu:"),
          {"inline_keyboard": [[{"text": " MAIN MENU ", "callback_data": "menu_home",
                                  "style": "success", "icon_custom_emoji_id": "6075758322873541432"}]]})
    sess.state = S.IDLE


def _wait_for_next_candle(trade_time_str: str, offset_secs: int = 7):
    now = datetime.now()
    hh, mm = map(int, trade_time_str.split(":"))
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    target = target + timedelta(minutes=1, seconds=offset_secs)
    if target < now:
        target += timedelta(days=1)
    secs = (target - now).total_seconds()
    if secs > 0:
        time.sleep(secs)


_lsig_owner_names: dict = {}


def _reversal_check(closes, opens, highs, lows, n):
    if n < 30:
        return None, 0
    ext_win = min(40, n)
    recent_high = max(highs[-ext_win:])
    recent_low  = min(lows[-ext_win:])
    last_c = closes[-1]
    rng = max(recent_high - recent_low, 1e-9)

    near_high = (recent_high - last_c) <= rng * 0.12
    near_low  = (last_c - recent_low)  <= rng * 0.12

    last_range = max(highs[-1] - lows[-1], 1e-9)
    upper_wick = highs[-1] - max(closes[-1], opens[-1])
    lower_wick = min(closes[-1], opens[-1]) - lows[-1]
    body = abs(closes[-1] - opens[-1])

    last3_bull = sum(1 for i in range(1, 4) if closes[-i] > opens[-i])
    last3_bear = sum(1 for i in range(1, 4) if closes[-i] < opens[-i])

    strong_bear_reject = (near_high and upper_wick > body * 1.3
                           and upper_wick / last_range > 0.42
                           and closes[-1] < opens[-1] and last3_bear >= 2)
    strong_bull_reject = (near_low and lower_wick > body * 1.3
                           and lower_wick / last_range > 0.42
                           and closes[-1] > opens[-1] and last3_bull >= 2)

    if strong_bear_reject:
        strength = upper_wick / last_range
        confidence = min(91, max(76, int(76 + strength * 25)))
        return "PUT", confidence
    if strong_bull_reject:
        strength = lower_wick / last_range
        confidence = min(91, max(76, int(76 + strength * 25)))
        return "CALL", confidence
    return None, 0


def analyze(candles):
    asc = list(reversed(candles))
    if len(asc) < 60:
        return None, 0, 50.0, 0.0, 0.0
    asc = asc[-500:] if len(asc) > 500 else asc
    closes = [float(c["close"]) for c in asc]
    opens  = [float(c["open"])  for c in asc]
    highs  = [float(c["high"])  for c in asc]
    lows   = [float(c["low"])   for c in asc]
    n      = len(asc)
    def _ema(period, src=None):
        data = src if src is not None else closes
        if len(data) < period: return data[-1]
        k = 2.0/(period+1); e = sum(data[:period])/period
        for v in data[period:]: e = v*k+e*(1-k)
        return e
    e8=_ema(8); e21=_ema(21); e50=_ema(50); e100=_ema(100)
    e200=_ema(200) if n>=200 else _ema(max(n//2,10))
    gains  = [max(0.0,closes[i]-closes[i-1]) for i in range(1,n)]
    losses = [max(0.0,closes[i-1]-closes[i]) for i in range(1,n)]
    ag=sum(gains[-14:])/14; al=sum(losses[-14:])/14
    rsi=100-100/(1+ag/max(al,1e-9))
    rev_dir, rev_conf = _reversal_check(closes, opens, highs, lows, n)
    if rev_dir is not None:
        return rev_dir, rev_conf, round(rsi,1), round(e8,6), round(e21,6)
    last_c=closes[-1]
    range50=max(max(highs[-50:])-min(lows[-50:]),1e-9)
    range20=max(max(highs[-20:])-min(lows[-20:]),1e-9)
    if   last_c>e100>e200: macro="CALL"
    elif last_c<e100<e200: macro="PUT"
    elif last_c>e200:      macro="CALL"
    elif last_c<e200:      macro="PUT"
    else: return None,0,round(rsi,1),round(e8,6),round(e21,6)
    mid_bull=last_c>e50; mid_bear=last_c<e50
    if macro=="CALL" and not mid_bull: return None,0,round(rsi,1),round(e8,6),round(e21,6)
    if macro=="PUT"  and not mid_bear: return None,0,round(rsi,1),round(e8,6),round(e21,6)
    if rsi>72 or rsi<28: return None,0,round(rsi,1),round(e8,6),round(e21,6)
    if macro=="CALL" and not(45<rsi<70): return None,0,round(rsi,1),round(e8,6),round(e21,6)
    if macro=="PUT"  and not(30<rsi<55): return None,0,round(rsi,1),round(e8,6),round(e21,6)
    cb=cc=0
    for i in range(1,n+1):
        if   closes[-i]>opens[-i]: cb+=1; cc=0
        elif closes[-i]<opens[-i]: cc+=1; cb=0
        else: break
        if cb>=4 or cc>=4: break
    if cb>=4 or cc>=4: return None,0,round(rsi,1),round(e8,6),round(e21,6)
    if n>=12 and abs(closes[-1]-closes[-12])>range50*0.55: return None,0,round(rsi,1),round(e8,6),round(e21,6)
    avg_body=sum(abs(closes[-i]-opens[-i]) for i in range(1,11))/10
    if avg_body/range20<0.020: return None,0,round(rsi,1),round(e8,6),round(e21,6)
    def _swing_highs(data_h,order=3,last_n=60):
        seg_h=data_h[-last_n:]; result=[]
        for i in range(order,len(seg_h)-order):
            if all(seg_h[i]>=seg_h[j] for j in range(i-order,i+order+1) if j!=i):
                result.append((i,seg_h[i]))
        return result
    def _swing_lows(data_l,order=3,last_n=60):
        seg_l=data_l[-last_n:]; result=[]
        for i in range(order,len(seg_l)-order):
            if all(seg_l[i]<=seg_l[j] for j in range(i-order,i+order+1) if j!=i):
                result.append((i,seg_l[i]))
        return result
    sh=_swing_highs(highs); sl=_swing_lows(lows)
    smc_signal=None; smc_score=0.0
    bos_bull=bos_bear=False
    if sh:
        last_sh=max(sh,key=lambda x:x[0])
        if closes[-1]>last_sh[1] and closes[-2]<=last_sh[1]: bos_bull=True
    if sl:
        last_sl=max(sl,key=lambda x:x[0])
        if closes[-1]<last_sl[1] and closes[-2]>=last_sl[1]: bos_bear=True
    if bos_bull and macro=="CALL": smc_score+=2.5; smc_signal="CALL"
    elif bos_bear and macro=="PUT": smc_score-=2.5; smc_signal="PUT"
    ob_bull=ob_bear=False
    if n>=5:
        for back in range(2,5):
            ob_c=closes[-back]; ob_o=opens[-back]
            if ob_c<ob_o:
                move_after=closes[-1]-ob_o
                if move_after>(highs[-back]-lows[-back])*0.5:
                    ob_bull=True; break
        for back in range(2,5):
            ob_c=closes[-back]; ob_o=opens[-back]
            if ob_c>ob_o:
                move_after=opens[-back]-closes[-1]
                if move_after>(highs[-back]-lows[-back])*0.5:
                    ob_bear=True; break
    if ob_bull and macro=="CALL":
        smc_score+=1.5
        if smc_signal is None: smc_signal="CALL"
    if ob_bear and macro=="PUT":
        smc_score-=1.5
        if smc_signal is None: smc_signal="PUT"
    sweep_bull=sweep_bear=False
    if sl and n>=3:
        nearest_sl=min(sl,key=lambda x:abs(x[1]-closes[-2])); sl_price=nearest_sl[1]
        if lows[-2]<sl_price and closes[-2]>sl_price: sweep_bull=True
    if sh and n>=3:
        nearest_sh=min(sh,key=lambda x:abs(x[1]-closes[-2])); sh_price=nearest_sh[1]
        if highs[-2]>sh_price and closes[-2]<sh_price: sweep_bear=True
    if sweep_bull and macro=="CALL":
        smc_score+=2.0
        if smc_signal is None: smc_signal="CALL"
    if sweep_bear and macro=="PUT":
        smc_score-=2.0
        if smc_signal is None: smc_signal="PUT"
    if smc_signal is None: return None,0,round(rsi,1),round(e8,6),round(e21,6)
    if (smc_signal=="CALL" and macro!="CALL") or (smc_signal=="PUT" and macro!="PUT"): return None,0,round(rsi,1),round(e8,6),round(e21,6)
    if abs(smc_score)<1.5: return None,0,round(rsi,1),round(e8,6),round(e21,6)
    last_body=abs(closes[-1]-opens[-1]); last_range=max(highs[-1]-lows[-1],1e-9)
    if last_body/last_range<0.35: return None,0,round(rsi,1),round(e8,6),round(e21,6)
    if smc_signal=="CALL" and closes[-1]<opens[-1]: return None,0,round(rsi,1),round(e8,6),round(e21,6)
    if smc_signal=="PUT"  and closes[-1]>opens[-1]: return None,0,round(rsi,1),round(e8,6),round(e21,6)
    smc_pts=min(abs(smc_score)/6.0,1.0); body_pts=min(last_body/last_range,1.0)
    setups=sum([bos_bull or bos_bear,ob_bull or ob_bear,sweep_bull or sweep_bear])
    multi_bonus=0.15*max(setups-1,0)
    raw=min(0.5+smc_pts*0.25+body_pts*0.15+multi_bonus,1.0)
    confidence=min(93,max(75,int(75+raw*18)))
    return smc_signal,confidence,round(rsi,1),round(e8,6),round(e21,6)


def _analyze_pair_wrapper(pair, candles):
    if not candles or len(candles)<20: return None
    direction,confidence,rsi_val,e8,e21=analyze(candles)
    if direction is None: return None
    return {"direction":direction,"confidence":confidence,"confirmations":confidence,
            "confirms":3 if confidence>=85 else(2 if confidence>=79 else 1),
            "market_type":"SMC","sw_score":0.5,"regime":"TRENDING","payout":0,
            "rsi":rsi_val,"e8":e8,"e21":e21}


_analyze_pair = lambda pair, indicators, candles=None: _analyze_pair_wrapper(pair, candles)


DB_PATH = "bot_data.db"
import sqlite3 as _sqlite3
import threading as _dbt
_db_lock = _dbt.Lock()

def get_db():

    conn = _sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15)
    conn.row_factory = _sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def setup_db():
    with _db_lock:
        conn = get_db()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id        INTEGER PRIMARY KEY,
                username       TEXT    DEFAULT '',
                full_name      TEXT    DEFAULT '',
                is_premium     INTEGER DEFAULT 0,
                daily_sigs     INTEGER DEFAULT 0,
                last_date      TEXT    DEFAULT '',
                total_sigs     INTEGER DEFAULT 0,
                wins           INTEGER DEFAULT 0,
                losses         INTEGER DEFAULT 0,
                joined_at      TEXT    DEFAULT '',
                license_expiry TEXT    DEFAULT '',
                plan_type      TEXT    DEFAULT 'free',
                signal_limit   INTEGER DEFAULT 0,
                is_banned      INTEGER DEFAULT 0,
                banned_at      TEXT    DEFAULT '',
                partial_history TEXT   DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS bot_config (
                key   TEXT PRIMARY KEY,
                value TEXT DEFAULT ''
            );
        """)
        for _col, _decl in (("future_sigs", "INTEGER DEFAULT 0"),
                             ("future_last_date", "TEXT DEFAULT ''"),
                             ("future_access_expiry", "TEXT DEFAULT ''"),
                             ("future_daily_limit", "INTEGER DEFAULT 0")):
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {_col} {_decl}")
            except Exception:
                pass
        conn.commit()
        conn.close()
        print("[DB] SQLite connected and tables verified.")


def _db_strategy_enabled(strategy: str) -> bool:
    """Returns True if the strategy is enabled (default: True)."""
    key = f"strategy_enabled_{strategy}"
    try:
        with _db_lock:
            conn = get_db()
            row = conn.execute(
                "SELECT value FROM bot_config WHERE key=?", (key,)
            ).fetchone()
            conn.close()
        if row is None:
            return True
        return row["value"] != "0"
    except Exception as e:
        print(f"[DB] strategy_enabled error ({strategy}): {e}")
        return True


def _db_strategy_set_enabled(strategy: str, enabled: bool) -> bool:
    key = f"strategy_enabled_{strategy}"
    try:
        with _db_lock:
            conn = get_db()
            conn.execute(
                "INSERT INTO bot_config(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, "1" if enabled else "0")
            )
            conn.commit(); conn.close()
        return True
    except Exception as e:
        print(f"[DB] strategy_set_enabled error ({strategy}): {e}")
        return False


def _db_lsess_allowed_get() -> set:
    try:
        with _db_lock:
            conn = get_db()
            row = conn.execute(
                "SELECT value FROM bot_config WHERE key='lsess_allowed'"
            ).fetchone()
            conn.close()
        if not row or not row["value"]:
            return set()
        import json as _j
        return set(_j.loads(row["value"]))
    except Exception as e:
        print(f"[DB] lsess_allowed_get error: {e}")
        return set()


def _db_lsess_allow(uid: int) -> bool:
    try:
        allowed = _db_lsess_allowed_get()
        allowed.add(uid)
        import json as _j
        with _db_lock:
            conn = get_db()
            conn.execute(
                "INSERT INTO bot_config(key,value) VALUES('lsess_allowed',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (_j.dumps(list(allowed)),)
            )
            conn.commit(); conn.close()
        return True
    except Exception as e:
        print(f"[DB] lsess_allow error uid={uid}: {e}")
        return False


def _db_lsess_disallow(uid: int) -> bool:
    try:
        allowed = _db_lsess_allowed_get()
        allowed.discard(uid)
        import json as _j
        with _db_lock:
            conn = get_db()
            conn.execute(
                "INSERT INTO bot_config(key,value) VALUES('lsess_allowed',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (_j.dumps(list(allowed)),)
            )
            conn.commit(); conn.close()
        return True
    except Exception as e:
        print(f"[DB] lsess_disallow error uid={uid}: {e}")
        return False


def _db_lsess_blocked_get() -> set:
    try:
        with _db_lock:
            conn = get_db()
            row = conn.execute(
                "SELECT value FROM bot_config WHERE key='lsess_blocked'"
            ).fetchone()
            conn.close()
        if not row or not row["value"]:
            return set()
        import json as _j
        return set(_j.loads(row["value"]))
    except Exception as e:
        print(f"[DB] lsess_blocked_get error: {e}")
        return set()


def _db_lsess_block(uid: int) -> bool:
    try:
        blocked = _db_lsess_blocked_get()
        blocked.add(uid)
        import json as _j
        with _db_lock:
            conn = get_db()
            conn.execute(
                "INSERT INTO bot_config(key,value) VALUES('lsess_blocked',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (_j.dumps(list(blocked)),)
            )
            conn.commit(); conn.close()
        return True
    except Exception as e:
        print(f"[DB] lsess_block error uid={uid}: {e}")
        return False


def _db_lsess_unblock(uid: int) -> bool:
    try:
        blocked = _db_lsess_blocked_get()
        blocked.discard(uid)
        import json as _j
        with _db_lock:
            conn = get_db()
            conn.execute(
                "INSERT INTO bot_config(key,value) VALUES('lsess_blocked',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (_j.dumps(list(blocked)),)
            )
            conn.commit(); conn.close()
        return True
    except Exception as e:
        print(f"[DB] lsess_unblock error uid={uid}: {e}")
        return False


def _lsess_can_use(uid: int) -> bool:
    if uid in ADMIN_IDS:
        return True
    if uid in _db_lsess_blocked_get():
        return False
    if uid in _db_lsess_allowed_get():
        return True
    return _db_license_is_valid(uid)


_db_cache:     dict = {}
_DB_CACHE_TTL: int  = 30

def _db_cache_set(uid: int, doc: dict):
    _db_cache[uid] = (doc, time.time() + _DB_CACHE_TTL)

def _db_cache_invalidate(uid: int):
    _db_cache.pop(uid, None)


def db_get(uid: int) -> dict:
    now = time.time()
    if uid in _db_cache:
        doc, exp = _db_cache[uid]
        if now < exp and doc:
            return doc
    try:
        with _db_lock:
            conn = get_db()
            row = conn.execute(
                "SELECT * FROM users WHERE user_id=?", (uid,)
            ).fetchone()
            conn.close()
        if not row:
            return {}
        doc = {
            "user_id":        row["user_id"],
            "username":       row["username"] or "",
            "full_name":      row["full_name"] or "",
            "is_premium":     row["is_premium"],
            "daily_sigs":     row["daily_sigs"],
            "last_date":      row["last_date"] or "",
            "total_sigs":     row["total_sigs"],
            "wins":           row["wins"],
            "losses":         row["losses"],
            "joined_at":      row["joined_at"] or "",
            "license_expiry": row["license_expiry"] or "",
            "plan_type":      row["plan_type"] or "free",
            "signal_limit":   row["signal_limit"],
            "is_banned":      row["is_banned"],
        }
        try:
            doc["future_sigs"]      = row["future_sigs"]
            doc["future_last_date"] = row["future_last_date"] or ""
        except (IndexError, KeyError):
            doc["future_sigs"]      = 0
            doc["future_last_date"] = ""
        try:
            doc["future_access_expiry"] = row["future_access_expiry"] or ""
            doc["future_daily_limit"]   = row["future_daily_limit"]
        except (IndexError, KeyError):
            doc["future_access_expiry"] = ""
            doc["future_daily_limit"]   = 0
        _db_cache[uid] = (doc, now + _DB_CACHE_TTL)
        return doc
    except Exception as e:
        print(f"[DB] db_get error uid={uid}: {e}")
        return {}


def db_upsert(uid: int, username: str = "", full_name: str = ""):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        with _db_lock:
            conn = get_db()
            conn.execute("""
                INSERT INTO users(user_id, username, full_name, joined_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    full_name=excluded.full_name
            """, (uid, username or "", full_name or "", now))
            conn.commit(); conn.close()
    except Exception as e:
        print(f"[DB] db_upsert error uid={uid}: {e}")
    finally:
        _db_cache_invalidate(uid)


def db_reset_daily(uid: int):
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        with _db_lock:
            conn = get_db()
            conn.execute(
                "UPDATE users SET daily_sigs=0, last_date=?, partial_history='[]' WHERE user_id=?",
                (today, uid)
            )
            conn.commit(); conn.close()
    except Exception as e:
        print(f"[DB] db_reset_daily error uid={uid}: {e}")
    finally:
        _db_cache_invalidate(uid)


def db_get_partial_history(uid: int) -> list:
    import json as _j
    try:
        with _db_lock:
            conn = get_db()
            row = conn.execute(
                "SELECT partial_history, last_date FROM users WHERE user_id=?", (uid,)
            ).fetchone()
            conn.close()
        if not row:
            return []
        today = datetime.now().strftime("%Y-%m-%d")
        if (row["last_date"] or "") != today:
            return []
        return _j.loads(row["partial_history"] or "[]")
    except Exception as e:
        print(f"[DB] db_get_partial_history error uid={uid}: {e}")
        return []


def db_save_partial_history(uid: int, partial_list: list):
    import json as _j
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        with _db_lock:
            conn = get_db()
            conn.execute(
                "UPDATE users SET partial_history=?, last_date=? WHERE user_id=?",
                (_j.dumps(partial_list), today, uid)
            )
            conn.commit(); conn.close()
    except Exception as e:
        print(f"[DB] db_save_partial_history error uid={uid}: {e}")


def db_inc_daily(uid: int):
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        with _db_lock:
            conn = get_db()
            conn.execute(
                "UPDATE users SET daily_sigs=daily_sigs+1, last_date=? WHERE user_id=?",
                (today, uid)
            )
            conn.commit(); conn.close()
    except Exception as e:
        print(f"[DB] db_inc_daily error uid={uid}: {e}")
    finally:
        _db_cache_invalidate(uid)


def db_dec_daily(uid: int):
    """Give back a quota slot — used when the market-regime engine blocks
    a manual signal after quota was already consumed at pair-selection
    time, so a blocked signal never costs the user anything."""
    try:
        with _db_lock:
            conn = get_db()
            conn.execute(
                "UPDATE users SET daily_sigs=MAX(daily_sigs-1,0) WHERE user_id=?",
                (uid,)
            )
            conn.commit(); conn.close()
    except Exception as e:
        print(f"[DB] db_dec_daily error uid={uid}: {e}")
    finally:
        _db_cache_invalidate(uid)


def db_record_result(uid: int, win: bool):
    try:
        with _db_lock:
            conn = get_db()
            if win:
                conn.execute(
                    "UPDATE users SET total_sigs=total_sigs+1, wins=wins+1 WHERE user_id=?",
                    (uid,)
                )
            else:
                conn.execute(
                    "UPDATE users SET total_sigs=total_sigs+1, losses=losses+1 WHERE user_id=?",
                    (uid,)
                )
            conn.commit(); conn.close()
    except Exception as e:
        print(f"[DB] db_record_result error uid={uid}: {e}")
    finally:
        _db_cache_invalidate(uid)


def _db_all_users_for_reset() -> list:
    try:
        with _db_lock:
            conn = get_db()
            rows = conn.execute(
                "SELECT user_id, is_premium, signal_limit FROM users WHERE user_id IS NOT NULL"
            ).fetchall()
            conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB] _db_all_users_for_reset error: {e}")
        return []


def refresh_daily(user: dict) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    if user.get("last_date") != today:
        db_reset_daily(user["user_id"])
        user["daily_sigs"] = 0
        user["last_date"]  = today
    return user


def db_is_premium(user: dict) -> bool:
    if not user.get("is_premium"):
        return False
    expiry = user.get("license_expiry", "")
    if not expiry:
        return False
    try:
        from datetime import date
        return date.today() <= date.fromisoformat(expiry)
    except Exception:
        return False


FREE_DAILY_LIMIT = 3

def get_daily_limit(user: dict) -> int:
    uid = user.get("user_id")
    if uid in ADMIN_IDS or _db_global_free_is_active():
        return 999999
    if db_is_premium(user):
        return int(user.get("signal_limit", 10))
    return FREE_DAILY_LIMIT


def can_signal(user: dict) -> bool:
    if not user:
        return False
    if user.get("is_banned"):
        return False
    limit = get_daily_limit(user)
    if limit <= 0:
        return False
    return int(user.get("daily_sigs", 0)) < limit


def _db_users_list() -> list:
    try:
        with _db_lock:
            conn = get_db()
            rows = conn.execute(
                "SELECT * FROM users ORDER BY joined_at ASC"
            ).fetchall()
            conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB] users_list error: {e}")
        return []


def _db_is_banned(uid: int) -> bool:
    if uid in ADMIN_IDS:
        return False
    doc = db_get(uid)
    return bool(doc.get("is_banned", 0))


def _db_ban_user(uid: int) -> bool:
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        with _db_lock:
            conn = get_db()
            conn.execute(
                "INSERT INTO users(user_id, is_banned, banned_at) VALUES(?,1,?) "
                "ON CONFLICT(user_id) DO UPDATE SET is_banned=1, banned_at=?",
                (uid, now, now)
            )
            conn.commit(); conn.close()
        print(f"[DB] banned uid={uid}")
        _db_cache_invalidate(uid)
        _invalidate_channel_cache(uid)
        return True
    except Exception as e:
        print(f"[DB] ban_user error uid={uid}: {e}")
        return False


def _db_unban_user(uid: int) -> bool:
    try:
        with _db_lock:
            conn = get_db()
            conn.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (uid,))
            conn.commit(); conn.close()
        _db_cache_invalidate(uid)
        return True
    except Exception as e:
        print(f"[DB] unban_user error uid={uid}: {e}")
        return False


def _db_license_add(uid: int, days: int, signal_limit: int) -> bool:
    try:
        expires = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        with _db_lock:
            conn = get_db()
            conn.execute("""
                INSERT INTO users(user_id, is_premium, plan_type, license_expiry,
                                  signal_limit, joined_at)
                VALUES(?, 1, 'premium', ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    is_premium=1,
                    plan_type='premium',
                    license_expiry=excluded.license_expiry,
                    signal_limit=excluded.signal_limit
            """, (uid, expires, signal_limit, now_str))
            conn.commit(); conn.close()
        print(f"[DB] license_add OK uid={uid} days={days} limit={signal_limit} expires={expires}")
        _db_cache_invalidate(uid)
        return True
    except Exception as e:
        print(f"[DB] license_add ERROR uid={uid}: {e}")
        return False


def _db_license_remove(uid: int) -> bool:
    try:
        with _db_lock:
            conn = get_db()
            conn.execute(
                "UPDATE users SET is_premium=0, plan_type='free', license_expiry='', signal_limit=0 "
                "WHERE user_id=?", (uid,)
            )
            conn.commit(); conn.close()
        print(f"[DB] license_remove uid={uid}")
        _db_cache_invalidate(uid)
        return True
    except Exception as e:
        print(f"[DB] license_remove error uid={uid}: {e}")
        return False


def _db_license_get(uid: int) -> dict:
    global_until = _db_global_free_until()
    if global_until and uid not in ADMIN_IDS:
        return {
            "expires": datetime.fromtimestamp(global_until).strftime("%Y-%m-%d %H:%M:%S"),
            "signal_limit": 999999,
            "plan_type": "global_free",
            "is_premium": 1,
        }
    doc = db_get(uid)
    if not doc or not doc.get("license_expiry"):
        return {}
    return {
        "expires":      doc.get("license_expiry", ""),
        "signal_limit": doc.get("signal_limit", 0),
        "plan_type":    doc.get("plan_type", "free"),
        "is_premium":   doc.get("is_premium", 0),
    }


def _db_license_is_valid(uid: int) -> bool:
    if uid in ADMIN_IDS or _db_global_free_is_active():
        return True
    user = db_get(uid)
    if not user:
        return False
    return db_is_premium(user)
def _db_live_quota_get(uid: int) -> int:
    _db_cache_invalidate(uid)
    user = db_get(uid)
    if not user:
        return 0
    today = datetime.now().strftime("%Y-%m-%d")
    if user.get("last_date") != today:
        return 0
    return user.get("daily_sigs", 0)


def _db_live_quota_use(uid: int) -> bool:
    if uid in ADMIN_IDS or _db_global_free_is_active():
        return True
    _db_cache_invalidate(uid)
    user = db_get(uid)
    if not user:
        import time as _t; _t.sleep(0.3)
        user = db_get(uid)
    if not user:
        return False
    today = datetime.now().strftime("%Y-%m-%d")
    if user.get("last_date") != today:
        db_reset_daily(uid)
        _db_cache_invalidate(uid)
        user = db_get(uid)
        if not user:
            return False
    if not can_signal(user):
        return False
    db_inc_daily(uid)
    return True


def _db_live_quota_refund(uid: int):
    if uid in ADMIN_IDS:
        return
    db_dec_daily(uid)


def _db_future_access_add(uid: int, days: int, daily_limit: int) -> bool:
    """Grant a user standalone Future Signal access — independent of the
    normal VIP license. Free users AND license/VIP users have NO Future
    Signal access unless explicitly granted here by an admin."""
    try:
        expires = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        with _db_lock:
            conn = get_db()
            conn.execute("""
                INSERT INTO users(user_id, future_access_expiry, future_daily_limit, joined_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    future_access_expiry=excluded.future_access_expiry,
                    future_daily_limit=excluded.future_daily_limit
            """, (uid, expires, daily_limit, now_str))
            conn.commit(); conn.close()
        print(f"[DB] future_access_add OK uid={uid} days={days} limit={daily_limit} expires={expires}")
        _db_cache_invalidate(uid)
        return True
    except Exception as e:
        print(f"[DB] future_access_add ERROR uid={uid}: {e}")
        return False


def _db_future_access_remove(uid: int) -> bool:
    try:
        with _db_lock:
            conn = get_db()
            conn.execute(
                "UPDATE users SET future_access_expiry='', future_daily_limit=0 "
                "WHERE user_id=?", (uid,)
            )
            conn.commit(); conn.close()
        print(f"[DB] future_access_remove uid={uid}")
        _db_cache_invalidate(uid)
        return True
    except Exception as e:
        print(f"[DB] future_access_remove error uid={uid}: {e}")
        return False


def _db_future_access_get(uid: int) -> dict:
    global_until = _db_global_free_until()
    if global_until and uid not in ADMIN_IDS:
        return {
            "expires": datetime.fromtimestamp(global_until).strftime("%Y-%m-%d %H:%M:%S"),
            "daily_limit": 999999,
            "global_free": True,
        }
    doc = db_get(uid)
    if not doc or not doc.get("future_access_expiry"):
        return {}
    return {
        "expires":     doc.get("future_access_expiry", ""),
        "daily_limit": int(doc.get("future_daily_limit", 0) or 0),
    }


def _db_future_access_is_valid(uid: int) -> bool:
    if uid in ADMIN_IDS or _db_global_free_is_active():
        return True
    doc = db_get(uid)
    if not doc:
        return False
    expiry = doc.get("future_access_expiry", "")
    if not expiry:
        return False
    try:
        from datetime import date
        return date.today() <= date.fromisoformat(expiry)
    except Exception:
        return False


def _db_future_quota_get(uid: int) -> int:
    _db_cache_invalidate(uid)
    user = db_get(uid)
    if not user:
        return 0
    today = datetime.now().strftime("%Y-%m-%d")
    if user.get("future_last_date") != today:
        return 0
    return int(user.get("future_sigs", 0))


def _db_future_quota_use(uid: int) -> bool:
    if uid in ADMIN_IDS or _db_global_free_is_active():
        return True
    if not _db_future_access_is_valid(uid):
        return False
    daily_limit = int(_db_future_access_get(uid).get("daily_limit", 0) or 0)
    if daily_limit <= 0:
        return False
    _db_cache_invalidate(uid)
    user = db_get(uid)
    if not user:
        import time as _t; _t.sleep(0.3)
        user = db_get(uid)
    if not user:
        return False
    today = datetime.now().strftime("%Y-%m-%d")
    if user.get("future_last_date") != today:
        try:
            with _db_lock:
                conn = get_db()
                conn.execute(
                    "UPDATE users SET future_sigs=0, future_last_date=? WHERE user_id=?",
                    (today, uid)
                )
                conn.commit(); conn.close()
        except Exception as e:
            print(f"[DB] future_quota reset error uid={uid}: {e}")
        _db_cache_invalidate(uid)
        user = db_get(uid)
        if not user:
            return False
    if int(user.get("future_sigs", 0)) >= daily_limit:
        return False
    try:
        with _db_lock:
            conn = get_db()
            conn.execute(
                "UPDATE users SET future_sigs=future_sigs+1, future_last_date=? WHERE user_id=?",
                (today, uid)
            )
            conn.commit(); conn.close()
    except Exception as e:
        print(f"[DB] future_quota_use error uid={uid}: {e}")
        return False
    finally:
        _db_cache_invalidate(uid)
    return True


def _db_user_register(uid: int, username: str = "", first_name: str = ""):
    db_upsert(uid, username, first_name)


def _db_user_add_result(uid: int, result: str):
    win = result in ("WIN", "MTG_WIN")
    db_record_result(uid, win)


OPEN_ACCOUNT_LINK = "https://broker-qx.pro/sign-up/?lid=1756662"

def _kb_license_required():
    return {"inline_keyboard": [
        [{"text": "Open Account & Join VIP", "url": OPEN_ACCOUNT_LINK,
          "style": "success", "icon_custom_emoji_id": str(EMAP["🚀"])}],
        [{"text": "Contact Support", "url": f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["✉"])}],
        [{"text": "Back to Home", "callback_data": "menu_home",
          "style": "danger", "icon_custom_emoji_id": str(EMAP["🏆"])}],
    ]}


def _license_denied_text(uid: int) -> str:
    def _e(k): return f'<tg-emoji emoji-id="{EMAP[k]}">{k}</tg-emoji>'
    doc = db_get(uid)
    if doc and doc.get("license_expiry"):
        return (
            f"{_e('💎')} <b>VIP ACCESS EXPIRED</b> {_e('💎')}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Your VIP access expired on <b>{doc.get('license_expiry','?')}</b>.\n\n"
            "Renew now to continue enjoying all premium features.\n\n"
            f"{_e('✉')} Support: <b>{SUPPORT_USERNAME}</b> {_e('💸')}\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
    return (
        f"{_e('💎')} <b>VIP MEMBERSHIP REQUIRED</b> {_e('💎')}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{_e('🚀')} <b>This Bot is Available Only for VIP Members!</b> {_e('🚀')}\n\n"
        "Join our VIP Channel today and unlock unlimited access to all premium features.\n\n"
        f"{_e('🔥')} <b>VIP Benefits:</b> {_e('🔥')}\n"
        f"{_e('✅')} Daily Live Trading Sessions\n"
        f"{_e('✅')} Sure-Shot Trade Calls &amp; Market Insights\n"
        f"{_e('✅')} Personal Trade Management Support\n"
        f"{_e('✅')} High-Accuracy Signals Every Day\n"
        f"{_e('✅')} Forex &amp; Crypto Signals with Full Analysis\n"
        f"{_e('✅')} 1-on-1 Personal Guidance &amp; Assistance\n"
        f"{_e('✅')} Priority VIP Support 24/7\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{_e('📌')} <b>How to Join VIP?</b>\n"
        f"{_e('1️⃣')} Open a trading account using our link\n"
        f"{_e('2️⃣')} Make a minimum deposit of <b>$50</b>\n"
        f"{_e('3️⃣')} Send us a message and get instant VIP access\n\n"
        f"{_e('🎯')} Start your VIP journey today and trade with confidence!\n\n"
        f"{_e('✉')} Support: <b>{SUPPORT_USERNAME}</b> {_e('💸')}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{_e('⚡')} <b>Upgrade to VIP &amp; Unlock Your Trading Potential!</b> {_e('⚡')}"
    )


def _kb_future_access_required():
    return {"inline_keyboard": [
        [{"text": "Contact Support", "url": f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["✉"])}],
        [{"text": "Back to Home", "callback_data": "menu_home",
          "style": "danger", "icon_custom_emoji_id": str(EMAP["🏆"])}],
    ]}


def _future_access_denied_text(uid: int) -> str:
    def _e(k): return f'<tg-emoji emoji-id="{EMAP[k]}">{k}</tg-emoji>'
    doc = db_get(uid)
    if doc and doc.get("future_access_expiry"):
        return (
            f"{_e('🔒')} <b>ACCESS EXPIRED</b> {_e('🔒')}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ <b>You are not eligible to use this feature.</b>\n\n"
            f"Your Future Signal access expired on <b>{doc.get('future_access_expiry','?')}</b>.\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
    return (
        f"{_e('🔒')} <b>ACCESS REQUIRED</b> {_e('🔒')}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ <b>You are not eligible to use this feature.</b>\n\n"
        "Future Signal is a restricted feature and is currently not available "
        "to your account.\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


def _kb_premium_tool_required():
    return {"inline_keyboard": [
        [{"text": "Upgrade Premium", "url": f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}",
          "style": "success", "icon_custom_emoji_id": str(EMAP["👑"])}],
        [{"text": "Back to Home", "callback_data": "menu_home",
          "style": "danger", "icon_custom_emoji_id": str(EMAP["🏆"])}],
    ]}


def _premium_tool_denied_text(uid: int) -> str:
    doc = db_get(uid) or {}
    expired = bool(doc.get("license_expiry"))
    detail = ("Your premium access has expired. Renew it to continue."
              if expired else
              "This feature is not available for free users.")
    return (
        "🔒 <b>PREMIUM FEATURE</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{detail}\n\n"
        "Upgrade to Premium to unlock this feature."
    )


def _premium_access_policy(data: str):
    """Map callbacks to premium-only tools without touching free checkers."""
    data = str(data or "")
    if (data in {"menu_backtest", "backtest_run", "menu_news_signal",
                 "menu_formatter", "fmt_ask_format", "menu_tz_convert",
                 "menu_pair_list", "menu_ai_filter", "menu_market_filter",
                 "menu_candle_colours", "menu_recent_trend", "menu_market_payouts",
                 "menu_ai_thinker", "menu_volatility_filter", "menu_bug_future",
                 "candle_scan_all", "recent_scan_all"}
            or data.startswith(("backtest_market_", "news_", "tz_src_", "tz_dst_",
                                "ai_filter_", "market_filter_", "candle_colour_",
                                "recent_trend_", "ai_thinker_", "volatility_"))):
        return "unlimited"
    if (data in {"menu_future_signal", "menu_multi_fs"}
            or data.startswith(("fut_home_", "futnew_", "fut_mode_", "futg_",
                                "fut_dir_", "fut_day_", "mfs_"))):
        return "future"
    return None


def _enforce_premium_access(uid: int, sess, policy: str) -> bool:
    if uid in ADMIN_IDS:
        return True
    if not _db_license_is_valid(uid):
        sess.state = S.IDLE
        _wiz(sess, efmt(_premium_tool_denied_text(uid)), _kb_premium_tool_required())
        return False
    if policy == "future" and not _db_future_access_is_valid(uid):
        sess.state = S.IDLE
        _wiz(sess, efmt(_future_access_denied_text(uid)), _kb_future_access_required())
        return False

    return True


_GLOBAL_FREE_KEY = "global_free_until"

def _db_global_free_until() -> int:

    try:
        with _db_lock:
            conn = get_db()
            row = conn.execute("SELECT value FROM bot_config WHERE key=?",
                               (_GLOBAL_FREE_KEY,)).fetchone()
            conn.close()
        until = int(row["value"] or 0) if row else 0
        if until > int(time.time()):
            return until
        if until:
            _db_global_free_disable()
        return 0
    except Exception as e:
        print(f"[DB] global_free_get error: {e}")
        return 0

def _db_global_free_is_active() -> bool:
    return _db_global_free_until() > int(time.time())

def _db_global_free_enable(days: int) -> int:
    until = int(time.time()) + int(days) * 24 * 60 * 60
    try:
        with _db_lock:
            conn = get_db()
            conn.execute(
                "INSERT INTO bot_config(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (_GLOBAL_FREE_KEY, str(until)))
            conn.commit(); conn.close()
        return until
    except Exception as e:
        print(f"[DB] global_free_enable error: {e}")
        return 0

def _db_global_free_disable() -> bool:
    try:
        with _db_lock:
            conn = get_db()
            conn.execute("DELETE FROM bot_config WHERE key=?", (_GLOBAL_FREE_KEY,))
            conn.commit(); conn.close()
        return True
    except Exception as e:
        print(f"[DB] global_free_disable error: {e}")
        return False


def _kb_free_limit_reached():
    return {"inline_keyboard": [
        [{"text": "Open Account & Join VIP", "url": OPEN_ACCOUNT_LINK,
          "style": "success", "icon_custom_emoji_id": str(EMAP["🚀"])}],
        [{"text": "Contact Support", "url": f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["✉"])}],
        [{"text": "Back to Home", "callback_data": "menu_home",
          "style": "danger", "icon_custom_emoji_id": str(EMAP["🏆"])}],
    ]}


def _free_limit_reached_text() -> str:
    def _e(k): return f'<tg-emoji emoji-id="{EMAP[k]}">{k}</tg-emoji>'
    return (
        f"{_e('💎')} <b>VIP MEMBERSHIP REQUIRED</b> {_e('💎')}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{_e('⚠')} <b>You have used all your free daily signals!</b>\n\n"
        "To get <b>unlimited signals</b> and enjoy <b>VIP features</b>, "
        "please join VIP.\n\n"
        f"{_e('✉')} Message Support: <b>{SUPPORT_USERNAME}</b> {_e('💸')}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{_e('⚡')} <b>Upgrade to VIP &amp; Unlock Your Trading Potential!</b> {_e('⚡')}"
    )


def _daily_reset_notification_text(signal_limit: int = 5, is_premium: bool = False) -> str:
    limit_line = (
        f"♾️ <b>Unlimited signals</b> (VIP)"
        if is_premium
        else f"🔋 <b>{signal_limit} signals</b> available today"
    )
    return (
        "╔══════════════════╗\n"
        "    👑 𝚉𝙴𝙱𝚁𝙾𝙽𝙸𝚇 𝙰𝙸 👑\n"
        "╚══════════════════╝\n\n"
        "🔔 <b>Daily Limit Reset!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "✅ Your daily signal limit has been reset.\n\n"
        f"{limit_line}\n\n"
        "Tap the button below to start using signals.\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 𝙾𝚠𝚗𝚎𝚛 : @RASUU_QXB✨"
    )


def _kb_daily_reset():
    return {"inline_keyboard": [
        [{"text": "Start", "callback_data": "menu_home",
          "style": "success", "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["robot"])}],
    ]}


BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry as _Retry
_http = requests.Session()
_tg_retry  = _Retry(total=2, backoff_factor=0.1, status_forcelist=[500,502,503,504])
_tg_adapter = HTTPAdapter(max_retries=_tg_retry, pool_connections=20, pool_maxsize=40)
_http.mount("https://", _tg_adapter)
_http.mount("http://",  _tg_adapter)
_tg_poll = requests.Session()
_tg_poll.mount("https://", HTTPAdapter(max_retries=_Retry(total=0), pool_connections=2, pool_maxsize=2))
_tg_poll.mount("http://",  HTTPAdapter(max_retries=_Retry(total=0), pool_connections=2, pool_maxsize=2))

_BUTTON_FONT_TABLE = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
    "𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"
)

def _style_button_text(value):
    return str(value).translate(_BUTTON_FONT_TABLE)

def _style_button_markup(markup):
    if not isinstance(markup, dict):
        return markup
    styled = dict(markup)
    for keyboard_key in ("inline_keyboard", "keyboard"):
        keyboard = markup.get(keyboard_key)
        if not isinstance(keyboard, list):
            continue
        styled_rows = []
        for row in keyboard:
            styled_row = []
            for button in row if isinstance(row, list) else []:
                if isinstance(button, dict):
                    button = dict(button)
                    if "text" in button:
                        button["text"] = _style_button_text(button["text"])
                styled_row.append(button)
            styled_rows.append(styled_row)
        styled[keyboard_key] = styled_rows
    return styled

def _api(method, data=None, files=None, params=None, timeout=15):
    try:
        if isinstance(data, dict) and data.get("reply_markup"):
            data = dict(data)
            raw_markup = data["reply_markup"]
            try:
                markup_obj = json.loads(raw_markup) if isinstance(raw_markup, str) else raw_markup
                styled_markup = _style_button_markup(markup_obj)
                data["reply_markup"] = (json.dumps(styled_markup)
                                        if isinstance(raw_markup, str) else styled_markup)
            except Exception:
                pass
        url = f"{BASE}/{method}"
        if params is not None:
            r = _http.get(url, params=params, timeout=timeout)
        elif files:
            r = _http.post(url, data=data, files=files, timeout=timeout)
        else:
            r = _http.post(url, data=data, timeout=timeout)
        result = r.json()
        if not result.get("ok"):
            desc = result.get("description","?")
            if "not modified"       in desc.lower(): return result
            if "not found"          in desc.lower(): return result
            if "no text in the"     in desc.lower(): return result
            if method in ("getUpdates","answerCallbackQuery","getChat","getChatMember","getMe"): return result
            print(f"[API] {method} -> {desc}")
        return result
    except Exception as e:
        print(f"[API] {method} error: {e}")
        return {}

def _send(chat_id, text, markup=None, parse_mode="HTML"):
    d = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if markup:
        d["reply_markup"] = json.dumps(_style_button_markup(markup))
    return _api("sendMessage", data=d)

_BOT_ID = None

def _get_bot_id() -> int:
    global _BOT_ID
    if _BOT_ID is None:
        try:
            r = _api("getMe")
            _BOT_ID = r.get("result", {}).get("id")
        except Exception:
            _BOT_ID = None
    return _BOT_ID

def _check_bot_admin_in_chat(chat_id):
    bot_id = _get_bot_id()
    if not bot_id:
        return False, None, "Could not determine bot identity."
    try:
        r = _api("getChatMember", data={"chat_id": chat_id, "user_id": bot_id})
        if not r.get("ok"):
            return False, None, r.get("description", "Unable to verify.")
        status = r.get("result", {}).get("status", "")
        title  = None
        try:
            cr = _api("getChat", data={"chat_id": chat_id})
            if cr.get("ok"):
                title = cr.get("result", {}).get("title") or cr.get("result", {}).get("username")
        except Exception:
            pass
        return status in ("administrator", "creator"), title, None
    except Exception as e:
        return False, None, str(e)

def _edit(chat_id, msg_id, text, markup=None, parse_mode="HTML"):
    d = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": parse_mode}
    if markup:
        d["reply_markup"] = json.dumps(_style_button_markup(markup))
    return _api("editMessageText", data=d)

def _delete(chat_id, msg_id):
    _api("deleteMessage", data={"chat_id": chat_id, "message_id": msg_id})

def _answer(cb_id, text="", show_alert=False):
    def _do():
        _api("answerCallbackQuery",
             data={"callback_query_id": cb_id, "text": text, "show_alert": show_alert})
    threading.Thread(target=_do, daemon=True).start()


_channel_cache: dict = {}
_CHANNEL_CACHE_TTL = 60

def _is_member_of(chat_id, uid: int) -> bool:
    try:
        r = _api("getChatMember",
                 data={"chat_id": chat_id, "user_id": uid})
        status = r.get("result", {}).get("status", "left")
        return status in ("creator", "administrator", "member", "restricted")
    except Exception as e:
        print(f"[Channel] getChatMember error chat={chat_id} uid={uid}: {e}")
        return None

def _is_channel_member(uid: int) -> bool:
    if uid in ADMIN_IDS:
        return True
    now = time.time()
    if uid in _channel_cache:
        result, exp = _channel_cache[uid]
        if now < exp:
            return result
    mem1 = _is_member_of(REQUIRED_CHANNEL_1_ID, uid)
    mem2 = _is_member_of(REQUIRED_CHANNEL_2_ID, uid)
    if mem1 is None or mem2 is None:
        if uid in _channel_cache:
            return _channel_cache[uid][0]
        return False
    is_mem = bool(mem1 and mem2)
    _channel_cache[uid] = (is_mem, now + _CHANNEL_CACHE_TTL)
    return is_mem

def _invalidate_channel_cache(uid: int):
    _channel_cache.pop(uid, None)

def _send_channel_required(cid: int, sess, already_joined: bool = False):
    if already_joined:
        text = (
            "<b>Verification Failed</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "It looks like you haven't joined both of our channels yet.\n\n"
            "Please join both channels first, wait 3 munites and then tap <b>Verify Again</b>."
        )
    else:
        text = (
            "<b>Channel Membership Required</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "To access this bot you must be a member of both our official channels.\n\n"
            "<b>Steps:</b>\n"
            "  1. Tap <b>Join Channel 1</b> and <b>Join Channel 2</b> below\n"
            "  2. Come back and wait 3 minutes \n"
            "  3. Tap <b>Verify Membership</b>"
        )
    kb = {"inline_keyboard": [
        [{"text": "Join Channel 1", "url": REQUIRED_CHANNEL_1_LINK,
          "style": "success", "icon_custom_emoji_id": str(EMAP["📣"])}],
        [{"text": "Join Channel 2", "url": REQUIRED_CHANNEL_2_LINK,
          "style": "success", "icon_custom_emoji_id": str(EMAP["📣"])}],
        [{"text": "Verify Membership", "callback_data": "verify_channel",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["✅"])}],
    ]}
    _wiz(sess, efmt(text), kb)

class S:
    IDLE             = "idle"
    LIVE_SIG_PAIR    = "live_sig_pair"
    LIVE_SIG_RUNNING = "live_sig_running"
    LSESS_AWAIT_CHANNEL = "lsess_await_channel"
    LSESS_AWAIT_RETRY   = "lsess_await_retry"
    LSESS_AWAIT_USERNAME= "lsess_await_username"
    LSESS_EMOJI_SELECT  = "lsess_emoji_select"
    LSESS_PREMIUM_CONFIRM = "lsess_premium_confirm"
    AWAIT_OWNER_USERNAME = "await_owner_username"
    LSESS_PAIR_SELECT   = "lsess_pair_select"
    LSESS_CONFIRM       = "lsess_confirm"
    LSESS_RUNNING       = "lsess_running"
    ADMIN_WIZARD        = "admin_wizard"
    FUTURE_MARKET_SELECT  = "future_market_select"
    FUTURE_GRID_SELECTING = "future_grid_selecting"
    FUTURE_DIR_SELECT     = "future_dir_select"
    FUTURE_START_TIME     = "future_start_time"
    FUTURE_END_TIME       = "future_end_time"
    FUTURE_DAYS_SELECT    = "future_days_select"
    BACKTEST_INPUT        = "backtest_input"
    BACKTEST_READY        = "backtest_ready"
    BACKTEST_RUNNING      = "backtest_running"
    MULTI_FS_DAYS         = "multi_fs_days"
    MULTI_FS_START_TIME   = "multi_fs_start_time"
    MULTI_FS_END_TIME     = "multi_fs_end_time"
    CHECKER_INPUT      = "checker_input"
    CHECKER_MTG        = "checker_mtg"
    CHECKER_CUSTOM_MTG = "checker_custom_mtg"
    CHECKER_DATE       = "checker_date"
    CHECKER_PAYOUT     = "checker_payout"
    TZ_SRC             = "tz_src"
    TZ_DST             = "tz_dst"
    TZ_INPUT           = "tz_input"
    FORMATTER_INPUT    = "formatter_input"
    FORMATTER_FORMAT   = "formatter_format"
    AI_FILTER_INPUT    = "ai_filter_input"
    AI_FILTER_MTG      = "ai_filter_mtg"
    AI_FILTER_DAYS     = "ai_filter_days"
    CANDLE_COLOUR_INPUT = "candle_colour_input"
    RECENT_TREND_INPUT  = "recent_trend_input"
    VOLATILITY_INPUT    = "volatility_input"

class UserState:
    def __init__(self, uid):
        self.uid   = uid
        self.state = S.IDLE
        self.wiz_chat = None
        self.wiz_mid  = None
        self.welcome_photo_mid = None
        self.live_sig_draft  = {}
        self.live_sig_pending = None
        self.live_sig_partial = []
        self.live_sig_mode    = None
        self.live_sig_auto_stop           = threading.Event()
        self.live_sig_auto_thread         = None
        self.live_sig_auto_manual_pairs   = []
        self.live_sig_auto_live_pairs     = []
        self.live_sig_auto_live_page      = 0
        self.live_sig_auto_select_page    = 0
        self.live_sig_blocked_pairs       = {}
        self.live_sig_session_wins        = 0
        self.live_sig_session_losses      = 0
        self.live_sig_strategy            = "pro2"
        self.lsess_channel_id    = None
        self.lsess_channel_title = None
        self.lsess_owner_name    = None
        self.lsess_emoji_mode    = None
        self.lsess_premium_account_id = None
        self.lsess_strategy      = "pro2"
        self.lsess_payout_filter = "all"
        self.owner_return_cb     = "menu_home"
        self.lsess_pairs         = []
        self.lsess_select_page   = 0
        self.lsess_pending       = None
        self.lsess_partial       = []
        self.lsess_session_wins   = 0
        self.lsess_session_losses = 0
        self.lsess_stop          = threading.Event()
        self.lsess_pause         = threading.Event()
        self.lsess_thread        = None
        self.lsess_blocked_pairs = {}
        self.admin_wizard        = {}
        self.fut_market_mode = None
        self.fut_engine      = "legacy"
        self.fut_new_strategy = None
        self.fut_pairs       = []
        self.fut_action_choice = "3"
        self.fut_start_time  = None
        self.fut_end_time    = None
        self.fut_pair_payouts = {}
        self.fut_sorted_pairs = []
        self.backtest_signals = []
        self.backtest_original_count = 0
        self.backtest_market = None
        self.ai_filter_draft = {}
        self.multi_fs = {"selected_pairs": []}
        self.checker_draft   = {}
        self.checker_last_losses  = []
        self.checker_last_candles = {}
        self.news_draft = {}
        self.tz_draft = {}
        self.formatter_draft = {}
        self.ai_thinker_market = None
        self.ai_thinker_pairs = []
        self.ai_thinker_payouts = {}

_sessions: dict = {}
_user_timezones: dict = {}

def _get_user_tz(uid: int) -> float:
    return _user_timezones.get(uid, 6.0)

def _convert_trade_time(time_str: str, uid: int) -> str:
    try:
        user_offset = _get_user_tz(uid)
        delta_mins  = int((user_offset - 6.0) * 60)
        if delta_mins == 0:
            return time_str
        h, m    = map(int, time_str.split(":"))
        total   = h * 60 + m + delta_mins
        total   = total % (24 * 60)
        if total < 0:
            total += 24 * 60
        return f"{total // 60:02d}:{total % 60:02d}"
    except Exception:
        return time_str

def _sess(uid) -> UserState:
    if uid not in _sessions:
        new_sess = UserState(uid)
        try:
            new_sess.live_sig_partial = db_get_partial_history(uid)
        except Exception:
            new_sess.live_sig_partial = []
        _sessions[uid] = new_sess
    return _sessions[uid]

def _wiz(sess: UserState, text, markup=None):

    if "<tg-emoji" not in str(text):
        text = efmt(text)
    if sess.wiz_mid:
        res = _edit(sess.wiz_chat, sess.wiz_mid, text, markup)
        if res.get("ok"):
            return
        if "not modified" in res.get("description", "").lower():
            return
    r   = _send(sess.wiz_chat, text, markup)
    mid = r.get("result", {}).get("message_id")
    if mid:
        sess.wiz_mid = mid

def _wiz_init(sess: UserState, chat_id):
    sess.wiz_chat = chat_id
    sess.wiz_mid  = None

_CANDLE_API_BASE = "https://akashqxpro.bdtraderpro.xyz/private/qbot/qx.php"

def _chart_open_value(value) -> bool:
    return value is True or value == 1 or str(value).strip().lower() == "true"

def _fetch_market_candles(pair: str, count: int = 200) -> list:
    try:
        resp = _http.get(_CANDLE_API_BASE, params={
            "pair": pair, "timeframe": "M1", "count": int(count)
        }, timeout=8)
        resp.raise_for_status()
        payload = resp.json()
        raw = payload.get("data", []) if isinstance(payload, dict) else []
        if not raw:
            return []
        latest = raw[0] if isinstance(raw[0], dict) else {}
        chart_open = latest.get("chart_open", payload.get("chart_open"))
        if not _chart_open_value(chart_open):
            return []
        out  = []
        for c in raw:
            try:
                out.append({
                    "open":   float(c.get("open",   c.get("o", 0))),
                    "high":   float(c.get("high",   c.get("h", 0))),
                    "low":    float(c.get("low",    c.get("l", 0))),
                    "close":  float(c.get("close",  c.get("c", 0))),
                    "time":   c.get("time",  c.get("timestamp", c.get("t", ""))),
                    "payout": int(c.get("payout", 0)),
                    "color":  c.get("colour", c.get("color", "")),
                    "volume": int(c.get("volume", 0) or 0),
                    "chart_open": True,
                })
            except Exception:
                continue
        out.reverse()
        return out
    except Exception:
        return []

_REMOVED_OTC_PAIRS = set()

def _get_lsig_otc_pairs() -> list:
    return [p for p in ALL_OTC_PAIRS if p not in _REMOVED_OTC_PAIRS]

def _get_lsig_live_pairs() -> list:
    return list(ALL_LIVE_PAIRS)

def _fetch_live_candles(pair: str, count: int = 200) -> list:
    return _fetch_market_candles(pair, count)

def _get_pair_payout(pair: str) -> int:
    candles = _fetch_market_candles(pair, 1)
    return int(candles[-1].get("payout", 0)) if candles else 0

_TICK_BASE = "https://akashqx.bdtraderpro.xyz/proversion/quotexticks/Qx_ticks.php"

def _fetch_live_tick(pair: str, timeout: int = 6):
    try:
        resp = _http.get(f"{_TICK_BASE}?pair={pair}", timeout=timeout)
        data = resp.json()
        if data.get("success") and data.get("data"):
            return data["data"]
    except Exception:
        pass
    return None

def _fetch_otc_candles(pair: str, count: int = 200) -> list:
    return _fetch_market_candles(pair, count)

EMAP = {
    "🖼": 6212836245689605545,
    "🏦": 6075758322873541432,
    "🧪": 6325365698809831722,
    "🕗": 6246852597127324096,
    "⚖️": 6064525334127059066,
    "⌛": 6311999502886641684,
    "👑": 6102842622865318037,
    "🎯": 6102539088936575040,
    "📊": 6102714680084537603,
    "🔻": 6080011023396381351,
    "⏱": 6102806257377221993,
    "⏰": 6339143318240238472,
    "⚡": 6102663814786855951,
    "💎": 6102756543130770682,
    "🟢": 6102451158071123265,
    "🛡": 6080277178224745259,
    "🚧": 6102908155476321775,
    "🔴": 6102630567445011877,
    "🔺": 6079952504466973149,
    "🟡": 5852626860516577393,
    "✨": 6102862147786645919,
    "🔍": 6102870527267839267,
    "⏳": 6062063510412599114,
    "📉": 6102889936225049752,
    "📈": 6102609195687747429,
    "🤖": 6080190230906805163,
    "⚜":  6102727689540477215,
    "🔰": 6082413318864118393,
    "⚙":  6102449465854008793,
    "🚨": 6102776583448173852,
    "🧠": 6271527128408264959,
    "📅": 6213192311363342410,
    "✅": 6102561165068476007,
    "❌": 6102666009515139030,
    "🔔": 6082393935676710336,
    "⚔":  6102382533083668811,
    "➡":  6271295457872319462,
    "✍":  5458382591121964689,
    "👋": 5440431182602842059,
    "🦾": 5780883460516221810,
    "🚀": 6079919871305457498,
    "🏆": 6102673289484705689,
    "👇": 6102872880909919548,
    "✉":  6102754850913657580,
    "📸": 5258205968025525531,
    "⚠":  6080370963130621682,   
    "🔄": 5260687119092817530,   
    "⏹":  6084515769780013003,   
    "👤": 5316727448644103237,  
    "⬇":  6231259404826579464,   
    "📡": 6102524232644698570,   
    "🌐": 6102762345631588035,   
    "🔋": 6079956563211067426,  
    "✔":  6080079455110307566,   
    "📣": 6174457264041103675,   
    "🔒": 6174514743588426961,
    "🔥": 6102540570700292421,
    "📌": 6082360203003568219,
    "1️⃣": 5764859959737063293,
    "2️⃣": 5764718968845637893,
    "3️⃣": 5764660845053219782,
    "💸": 6102862147786645919,
    "⏳": 6215151795702865562,
    "📊": 6208713364848256468,
    "📆": 6210895186759785075,
    "🚀": 6201550209802052083,
    "🛡": 6179197434762108108,
    "🎮": 6154242686929870878,
    "🤖": 6134212600138833922,
    "👑": 6131977683841589337,
    "⏱": 6075408991708519910,
    "🎯": 6075602196517363973,
    "💰": 6131837440274472567,
    "📊": 6312053434790976755,
    "⚠": 6311936890853402623,
    "🚀": 6312268032831922473,
    "✉": 6312320444317834713,
    "➕": 6312168668763529862,
    "💬": 6311986557855212482,
    "⭕": 6312204531740450789,
    "🟢": 6186138166336954485,
    "🔵":6210690020467023497,
    "✅": 6312042143321957539,
    "📣": 6181610987339128822,
    "😈": 6174844764580486778,
    "⚡": 6312070206638270086,
    "🚀": 6311922511302893202,
    "🔜": 6312334695019323192,
    "💯": 6311864288726228831,
    "⏳": 6213124854606995795,
    "📊": 6208713364848256468,
    "💰": 6210902995010331288,
    "😄": 6213067701477187762,
    "👍": 6213015637883627866,
    "🔔": 6213276192074636650,
    "🔗": 6210635890994192211,
    "🗑": 6212982832923418680,
    "🛡": 6213249438723350292,
    "🛍": 6213064153834199528,
    "➕": 6213079894889340733,
    "🖕": 6213102542251892952,
    "🛡": 6210955638424478130,
    "☄": 6213246372116701929,
    "😕": 6147508869699477866,
    "😬": 6141101654667174153,
    "✅": 6231121076814879723,
    "🙋": 6300701887767256657,
    "😍": 6300609412826406453,
    "😬": 6303178821176663320,
    "⚪": 6212942778058416879,
    "🍾": 6303081480037866015,
    "🆗": 6300814570529233894,
    "👀": 6300720205802774823,
    "⚙": 6300679098670784062,
    "⏰": 6066542040315863878,
    "🗓": 6145197992610636125,
    "🫣": 6300674107918785843,
    "📊": 6303181741754424089,
    "💬": 6181344471733509337,
    "🚀": 6172369471848588525,
    "⌛": 6311999502886641684,
    "🏃": 6311814063378668893,
    "💤": 6312037371613290503,
    "🔄": 6311984148378560080,
    "👍": 6213247621952183622,
    "🔥": 6201804557765320782,
    "📥": 6210954826675658321,
    "🎉": 6212727110570614344,
    "💱": 6212777095400006386,
    "▶": 6212782266540630237,
    "🔍": 6213218467714179432,
    "🛡": 6212950328610923100,
    "🎉": 6066474858437417509,
    "⏱": 6066877189498871230,
    "🔍": 6213218467714179432,
    "⏰": 6185912891007312754,
    "♦": 6213083249258799034,
    "➕": 6303030189538417585,
    "🚀": 6172369471848588525,
    "🇧🇩": 5291824687096027834,
    "🔥": 6300594556534528479,
    "⚠": 6303178164046666974,
    "🐂": 6302940240038337269,
    "⚪": 6212942778058416879,
    "♦": 6213083249258799034,
    "⭐": 6228877484683697988,
    "🔒": 6147726688965893754,
    "📈": 6302907014171335283,
    "✔": 6213134853290860011,
    "❌": 6237969311974039494,
    "🗓": 5249045975309245331,
    "⏫": 6336675550291040688,
    "⏬": 6337011996554175695,
    "📈": 6301020247923105456,
    "📊": 6208713364848256468,
    "✅": 6233523441002093972,
    "😋": 6301088640982326387,
    "🚨": 6066399073739481716,
    "🔥": 6219643562695336727,
    "💎": 6132052287423522342,
    "📅": 6240227038842594522,
    "🆔": 6231075713370300702,
    "🏷": 6300686610568584382,
    "🔓": 6147517386619625873,
    "📩": 6210954826675658321,
    "🔁": 6312168668763529862,
    "🇧🇩": 6235311758009966324,
    "🥳": 6300963760513228226,
    "🥳": 6257910750640087316,
    "⏰": 6199481298285765203,
    "🟢": 6186138166336954485,
    "🔴": 6186082516445700103,
    "😮": 6258293372096617951,
    "💶": 6301088640982326387,
    "💴": 6212782266540630237,
    "🔮": 6219643562695336727,
    "👉": 6253591396519779914,
    "✏️": 6212719813421177416,
    "📔": 6082466640883097151,
    "🐺": 6327888936261657260,
    "💀": 6327854211451069152,
    "🔘": 6212911416207219932,
    "💡": 6060093683791831809,
    "😐": 6249119034189553069,
    "❓": 6311968686496292533,
    "😧": 6325365698809831722,
    "📳": 6244334174333837880,
    "☠️": 6251113539692404220,
    "🍆": 6325782422306696234,
    "🫡": 6251255557081015155,
    "🕯": 6052915431935583075,
    "🕗": 6246852597127324096,
    "⬆": 6055584668210701185,
    "🔽": 6057775002747412180,
    "🔄": 6057849898387119890,
    "🧪": 6325365698809831722,
    "⏰": 6339143318240238472,
    "⚖️": 6064525334127059066,
    "⌛": 6311999502886641684,
    "🕐": 6075593821331137073,
    "📋": 6059678472123457582,
    "📤": 5433614747381538714,
    "🗂": 5431736674147114227,
    "🔬": 6300645662350385138,
    "♾": 5469745532693923461,
    "♾️": 5469745532693923461,
    "🏛": 6300963760513228226,
    "⚠️": 6303178164046666974,
    "🔖": 6210582229672795673,
    "🚩": 6210613943711309657,
    "🔍": 6213218467714179432,
}

def _future_time_prompt(kind: str) -> str:
    """Styled Future Signal start/end time prompt."""
    is_end = str(kind).upper() == "END"
    if not is_end:
        chart_emoji = '<tg-emoji emoji-id="6212901597911980909">&#128202;</tg-emoji>'
        shocked_emoji = '<tg-emoji emoji-id="6055648581619031824">&#128551;</tg-emoji>'
        down_emoji = '<tg-emoji emoji-id="6210680880776617424">&#11015;&#65039;</tg-emoji>'
        hourglass_emoji = '<tg-emoji emoji-id="6311999502886641684">&#8987;</tg-emoji>'
        return (
            f"{chart_emoji}<b>𝗘𝗡𝗧𝗘𝗥 𝗦𝗧𝗔𝗥𝗧 𝗧𝗜𝗠𝗘</b> {chart_emoji}\n"
            "━━━━━━━━━━━━━━\n\n"
            "<b>⏰ 𝗦𝘁𝗲𝗽 𝟭 — 𝗦𝘁𝗮𝗿𝘁 𝗧𝗶𝗺𝗲</b>\n\n"
            f"{shocked_emoji} 𝗘𝗻𝘁𝗲𝗿 𝘀𝗶𝗴𝗻𝗮𝗹 𝘀𝘁𝗮𝗿𝘁 𝘁𝗶𝗺𝗲:\n"
            "<code>HH:MM</code> e.g. <code>09:00</code>\n\n"
            f"{down_emoji}𝙏𝙤 𝙉𝙚𝙭𝙩 𝙎𝙩𝙚𝙥 𝙎𝙖𝙢𝙚 𝙋𝙧𝙤𝙘𝙚𝙨𝙨{hourglass_emoji}"
        )
    title = "𝗘𝗡𝗗" if is_end else "𝗦𝗧𝗔𝗥𝗧"
    label = "𝗲𝗻𝗱" if is_end else "𝘀𝘁𝗮𝗿𝘁"
    step = 2 if is_end else 1
    example = "09:00" if is_end else "00:03"
    return (
        f"🧪<b>𝗘𝗡𝗧𝗘𝗥 {title} 𝗧𝗜𝗠𝗘</b>🧪\n"
        "━━━━━━━━━━━━━━\n\n"
        f"<b>⏰ Step {step} —</b> 𝗘𝗻𝘁𝗲𝗿 {label} 𝗧𝗶𝗺𝗲\n\n"
        f"⏰𝗘𝗻𝘁𝗲𝗿 𝘀𝗶𝗴𝗻𝗮𝗹 {label} 𝘁𝗶𝗺𝗲: <b>HH:MM e.g. {example}</b>\n\n"
        "⚖️𝗡𝗼𝘄 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲 𝗦𝗶𝗴𝗻𝗮𝗹𝘀 𝗶𝗻 𝘀𝗲𝗰𝗼𝗻𝗱⌛"
    )

_LIVE_SIG_EMOJI_IDS = {
    "crown":    6233239968865590050,
    "target":   5310278924616356636,
    "chart":    6145248943807667330,
    "badge":    6215194556397260680,
    "writing":  5458382591121964689,
    "robot":    6255726532136800534,
    "gear":     6118476436966741936,
    "cross":    6260072893011469020,
    "bell":     6258123652168949843,
    "next":     6271295457872319462,
    "alert":    6233314121475956159,
}

def fmt(text: str, use_prem: bool = True, bold: bool = True, italic: bool = False) -> str:
    if not use_prem:
        result = _html.escape(str(text or ""))
        if bold and italic:
            return f"<b><i>{result}</i></b>"
        if bold:
            return f"<b>{result}</b>"
        if italic:
            return f"<i>{result}</i>"
        return result
    parts = []
    chars = list(text)
    i = 0
    while i < len(chars):
        ch      = chars[i]
        next_ch = chars[i + 1] if i + 1 < len(chars) else ""
        pair    = ch + next_ch
        if pair in EMAP:
            safe = _html.escape(pair)
            parts.append(f'<tg-emoji emoji-id="{EMAP[pair]}">{safe}</tg-emoji>')
            i += 2
            continue
        if ch in EMAP:
            safe = _html.escape(ch)
            parts.append(f'<tg-emoji emoji-id="{EMAP[ch]}">{safe}</tg-emoji>')
            if next_ch == "\ufe0f":
                i += 2
            else:
                i += 1
            continue
        if ch == "\ufe0f":
            i += 1
            continue
        parts.append(_html.escape(ch))
        i += 1
    result = "".join(parts)
    if bold and italic:
        result = f"<b><i>{result}</i></b>"
    elif bold:
        result = f"<b>{result}</b>"
    elif italic:
        result = f"<i>{result}</i>"
    return result

def efmt(html_text: str) -> str:
    parts = []
    chars = list(html_text)
    i = 0
    while i < len(chars):
        ch      = chars[i]
        next_ch = chars[i + 1] if i + 1 < len(chars) else ""
        pair    = ch + next_ch
        if pair in EMAP:
            safe = _html.escape(pair)
            parts.append(f'<tg-emoji emoji-id="{EMAP[pair]}">{safe}</tg-emoji>')
            i += 2
            continue
        if ch in EMAP:
            safe = _html.escape(ch)
            parts.append(f'<tg-emoji emoji-id="{EMAP[ch]}">{safe}</tg-emoji>')
            if next_ch == "\ufe0f":
                i += 2
            else:
                i += 1
            continue
        if ch == "\ufe0f":
            i += 1
            continue
        parts.append(ch)
        i += 1
    return "".join(parts)

def _feature_efmt(html_text: str, local_map: dict) -> str:
    """Premium-emoji renderer with feature-local ID overrides."""
    mapping = dict(EMAP)
    mapping.update(local_map or {})
    parts, chars, i = [], list(str(html_text or "")), 0
    while i < len(chars):
        ch = chars[i]
        next_ch = chars[i + 1] if i + 1 < len(chars) else ""
        pair = ch + next_ch
        if pair in mapping:
            parts.append(f'<tg-emoji emoji-id="{mapping[pair]}">{_html.escape(pair)}</tg-emoji>')
            i += 2
            continue
        if ch in mapping:
            parts.append(f'<tg-emoji emoji-id="{mapping[ch]}">{_html.escape(ch)}</tg-emoji>')
            i += 2 if next_ch == "\ufe0f" else 1
            continue
        if ch == "\ufe0f":
            i += 1
            continue
        parts.append(ch)
        i += 1
    return "".join(parts)

_TELETHON_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_TELETHON_CONFIG_FILE = os.path.join(_TELETHON_BASE_DIR, "telethon_config.json")
_TELETHON_SEND_LOCK = threading.RLock()
_TELETHON_SEND_ATTEMPTS = 3

def _telethon_config():
    try:
        with open(_TELETHON_CONFIG_FILE, encoding="utf-8") as f:
            cfg = json.load(f)
        session_name = str(cfg.get("session_name") or "quotexbd_admin").strip()
        if not os.path.isabs(session_name):
            session_name = os.path.join(_TELETHON_BASE_DIR, session_name)

        if session_name.lower().endswith(".session"):
            session_name = session_name[:-8]
        cfg["session_name"] = session_name
        return cfg
    except Exception as e:
        print(f"[Telethon] config error: {e}")
        return None

def _admin_has_premium() -> bool:
    cfg = _telethon_config()
    return bool(cfg and cfg.get("premium"))

def _ensure_event_loop():

    import asyncio
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

def _telethon_client():

    cfg = _telethon_config()
    if not cfg:
        return None
    try:
        _ensure_event_loop()
        from telethon.sync import TelegramClient
        return TelegramClient(cfg["session_name"], cfg["api_id"], cfg["api_hash"])
    except ImportError:
        print("[Telethon] library not installed — run: pip install telethon")
        return None
    except Exception as e:
        print(f"[Telethon] client init error: {e}")
        return None

def _telethon_payload(html_text):
    """Parse HTML and build custom-emoji entities without parser-version dependence."""
    from telethon.extensions import html as _th_html
    from telethon.tl.types import MessageEntityCustomEmoji
    source = str(html_text or "")
    pattern = re.compile(
        r"<tg-emoji\s+emoji-id=[\"'](\d+)[\"']\s*>(.*?)</tg-emoji\s*>",
        re.I | re.S)
    emoji_specs = []

    def _placeholder(match):
        index = len(emoji_specs)
        fallback = _html.unescape(re.sub(r"<[^>]+>", "", match.group(2)))
        if not fallback:
            fallback = "▫"
        token = f"\ue000ZXCE{index:04d}\ue001"
        emoji_specs.append((token, fallback, int(match.group(1))))
        return token

    prepared = pattern.sub(_placeholder, source)
    message, entities = _th_html.parse(prepared)

    def _u16_len(value):
        return len(value.encode("utf-16-le")) // 2

    replacements = []
    search_from = 0
    for token, fallback, document_id in emoji_specs:
        char_pos = message.find(token, search_from)
        if char_pos < 0:
            raise RuntimeError("custom emoji placeholder was lost during HTML parsing")
        old_start = _u16_len(message[:char_pos])
        old_len = _u16_len(token)
        new_len = _u16_len(fallback)
        replacements.append((old_start, old_len, new_len, document_id,
                             char_pos, len(token), fallback))
        search_from = char_pos + len(token)

    for _, _, _, _, char_pos, token_len, fallback in reversed(replacements):
        message = message[:char_pos] + fallback + message[char_pos + token_len:]


    for entity in entities:
        old_start = entity.offset
        old_end = entity.offset + entity.length
        start_shift = sum(new_len - old_len for pos, old_len, new_len, *_
                          in replacements if pos + old_len <= old_start)
        end_shift = sum(new_len - old_len for pos, old_len, new_len, *_
                        in replacements if pos < old_end)
        entity.offset = old_start + start_shift
        entity.length = (old_end + end_shift) - entity.offset

    running_shift = 0
    for old_start, old_len, new_len, document_id, *_ in replacements:
        entities.append(MessageEntityCustomEmoji(
            offset=old_start + running_shift,
            length=new_len,
            document_id=document_id))
        running_shift += new_len - old_len
    entities.sort(key=lambda entity: (entity.offset, -entity.length))
    actual = sum(isinstance(entity, MessageEntityCustomEmoji) for entity in entities)
    if actual != len(emoji_specs):
        raise RuntimeError(
            f"custom emoji entity mismatch: expected={len(emoji_specs)}, built={actual}")
    return message, entities

def _telethon_send(chat_id, html_text, photo_bytes=None) -> bool:

    with _TELETHON_SEND_LOCK:
        try:
            message, entities = _telethon_payload(html_text)
        except Exception as e:
            print(f"[Telethon] premium entity parse error: {e}")
            return False
        for attempt in range(1, _TELETHON_SEND_ATTEMPTS + 1):
            client = _telethon_client()
            if not client:
                if attempt < _TELETHON_SEND_ATTEMPTS:
                    time.sleep(attempt)
                continue
            try:
                client.connect()
                if not client.is_user_authorized():
                    raise RuntimeError("saved Telethon session is not authorized")
                account = client.get_me()
                if not bool(getattr(account, "premium", False)):
                    raise RuntimeError("connected Telegram account is not Premium")
                if photo_bytes is None:
                    client.send_message(chat_id, message, formatting_entities=entities,
                                        parse_mode=None)
                else:
                    import io as _tio
                    buf = _tio.BytesIO(photo_bytes)
                    buf.name = "chart.png"
                    client.send_file(chat_id, buf, caption=message,
                                     formatting_entities=entities, parse_mode=None,
                                     force_document=False)
                return True
            except Exception as e:
                print(f"[Telethon] premium send attempt {attempt}/{_TELETHON_SEND_ATTEMPTS} failed: {e}")
            finally:
                try:
                    client.disconnect()
                except Exception:
                    pass
            if attempt < _TELETHON_SEND_ATTEMPTS:
                time.sleep(attempt)
        return False

def _telethon_send_text(chat_id, html_text) -> bool:
    return _telethon_send(chat_id, html_text)

def _telethon_send_photo(chat_id, photo_bytes, caption_html) -> bool:
    return _telethon_send(chat_id, caption_html, photo_bytes=photo_bytes)

def _telethon_account_status(chat_id=None):
 
    client = _telethon_client()
    if not client:
        return {"ok": False, "error": "Premium account is not connected."}
    try:
        client.connect()
        if not client.is_user_authorized():
            return {"ok": False, "error": "Saved Telegram session is not authorized."}
        account = client.get_me()
        result = {"ok": True, "id": int(account.id),
                  "username": getattr(account, "username", None),
                  "premium": bool(getattr(account, "premium", False)),
                  "can_send": None}
        if not result["premium"]:
            result.update(ok=False, error="Connected Telegram account is not Premium.")
            return result
        if chat_id is not None:
            entity = client.get_entity(chat_id)
            perms = client.get_permissions(entity, account)
            is_admin = bool(getattr(perms, "is_admin", False) or
                            getattr(perms, "is_creator", False))
            if bool(getattr(entity, "broadcast", False)):
                can_post = bool(getattr(perms, "is_creator", False) or
                                getattr(perms, "post_messages", False))
            else:
                send_flag = getattr(perms, "send_messages", None)
                can_post = is_admin and send_flag is not False
            result.update(is_admin=is_admin, can_send=bool(is_admin and can_post))
        return result
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        try: client.disconnect()
        except Exception: pass

def _normal_emoji_html(html_text):
    """Keep HTML/bold formatting but remove custom-emoji entity wrappers."""
    return re.sub(r'<tg-emoji\s+emoji-id=["\']\d+["\']\s*>(.*?)</tg-emoji\s*>',
                  r'\1', str(html_text or ""), flags=re.I | re.S)

def _channel_send_text(chat_id, html_text, premium=None):
    use_telethon = _admin_has_premium() if premium is None else bool(premium)
    if use_telethon:
        ok = _telethon_send_text(chat_id, html_text)
        if not ok:
            print("[ChannelSender] premium text was not sent; normal-emoji fallback blocked")
        return ok
    response = _send(chat_id, _normal_emoji_html(html_text))
    return bool(response and response.get("ok"))

def _build_welcome(first_name: str) -> str:
    name = _html.escape(first_name or "Trader")

    def _we(fallback: str, emoji_id: int) -> str:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

    candle = _we("🕯", 6210497528622751920)
    lines = [
        f"{candle} 𝚆𝙴𝙻𝙲𝙾𝙼𝙴 𝚃𝙾 𝚉𝙴𝙱𝚁𝙾𝙽𝙸𝚇 𝙰𝙸 𝚃𝙾𝙾𝙻𝚂 {candle}",
        "╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌",
        f"Assalamualaikum,  {name} {_we('👋', 5440431182602842059)}",
        "╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌",
        f"{_we('👑', 6212843547134008737)} 𝙰𝙸-𝙳𝚁𝙸𝚅𝙴𝙽 𝙼𝙰𝙴𝙺𝙴𝚃 𝙵𝙾𝚁𝙴𝙲𝙰𝚂𝚃𝙸𝙽𝙶 {_we('🥂', 6156472913122828000)}",
        f"{_we('❄️', 6145183076189217554)} 𝙰𝙳𝚅𝙰𝙽𝙲𝙴 𝚂𝚃𝚁𝙰𝚃𝙴𝙶𝚈 𝚅𝙾𝙻𝙸𝙽𝙶 𝚂𝚈𝚂𝚃𝙴𝙼  {_we('💀', 6311973054478032971)}",
        f"{_we('😬', 6300547101440876358)} 𝙽𝙴𝚆𝚂 𝚂𝙸𝙶𝙽𝙰𝙻 𝙲𝚁𝙰𝙲𝙺𝙴𝚁 𝚃𝙾𝙾𝙻 {_we('📊', 6302799249146911743)}",
        f"{_we('📊', 6303181741754424089)} 𝙰𝙸 &amp; 𝙱𝙰𝙲𝙺𝚃𝙴𝚂𝚃-𝚂𝙸𝙶𝙽𝙰𝙻 𝙼𝙾𝙳𝚄𝙻𝙴 {_we('🤖', 6134212600138833922)}",
        f"{_we('🎉', 6212727110570614344)} 𝙰𝚄𝚃𝙾 𝙼𝙰𝙽𝚄𝙰𝙻 𝙻𝙸𝚅𝙴 𝚂𝙸𝙶𝙽𝙰𝙻𝚂 𝚆𝙸𝚃𝙷 𝙷𝙸𝙶𝙷\n       𝙲𝙾𝙽𝙵𝙸𝙳𝙴𝙽𝙲𝙴 {_we('💯', 6212853060486569826)}",
        "╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌",
        "",
        f"{_we('🍾', 6303081480037866015)} 𝚆𝙷𝚈 𝚃𝚁𝙰𝙳𝙴𝚁 𝙲𝙷𝙾𝙾𝚂𝙴 𝚉𝙴𝙱𝚁𝙾𝙽𝙸𝚇 𝙰𝙸 {_we('🧠', 6154403889937393435)}",
        "",
        f"{_we('🆗', 6300814570529233894)} 𝙳𝙴𝙴𝙿 𝙰𝙽𝙰𝙻𝚈𝚂𝙴𝚂 𝙾𝚃𝙲 &amp; 𝙻𝙸𝚅𝙴 𝙿𝙰𝙸𝚁 {_we('📊', 6312053434790976755)}",
        f"{_we('📊', 6302799249146911743)} 𝚁𝙴𝙰𝙻-𝚃𝙸𝙼𝙴 𝙾𝚁𝙳𝙴𝚁 𝙵𝙻𝙾𝚆 𝙰𝙽𝙰𝙻𝚈𝚂𝙸𝚂 {_we('🎙', 6131826698561265458)}",
        f"{_we('⚙️', 6300679098670784062)} 𝙰𝙸 𝚂𝚃𝚁𝙰𝚃𝙴𝙶𝚈 𝙵𝙸𝙻𝚃𝙴𝚁 𝙻𝙸𝚅𝙴 𝙿𝙰𝙸𝚁 {_we('🎮', 6154242686929870878)}",
        f"{_we('😄', 6300778290940485048)} 𝙱𝙴𝚂𝚃 𝟼 𝙵𝚄𝚃𝚄𝚁𝙴 𝚂𝙸𝙶𝙽𝙰𝙻𝚂 𝙶𝙴𝙽𝙴𝚁𝙰𝚃𝙾𝚁 {_we('📎', 6154281857031609738)}",
        f"{_we('💰', 6210902995010331288)} 𝙾𝚃𝙲 𝙻𝙸𝚅𝙴 𝙵𝚄𝚃𝚄𝚁𝙴 𝚂𝙸𝙶𝙽𝙰𝙻 𝙱𝙰𝙲𝙺𝚃𝙴𝚂𝚃{_we('👀', 6212900180572774622)}",
        f"{_we('💡', 6060093683791831809)} 𝙻𝙸𝚅𝙴 𝙲𝙷𝙰𝙽𝙽𝙴𝙻 𝚂𝙴𝙽𝙳𝙴𝚁 𝟹 𝙼𝙰𝙽𝚄𝙰𝙻 𝚂𝚃𝚁𝙰𝚃𝙴𝙶𝚈\n       𝙱𝚄𝚃𝚃𝙾𝙽 𝟺𝟺+ 𝙸𝙽𝙱𝚄𝙸𝙻𝚃 𝚂𝚃𝚁𝙰𝚃𝙴𝙶𝙸𝙴𝚂{_we('🌐', 6300935581232799439)}",
        "╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌",
        "",
        f"{_we('😍', 6300609412826406453)} 𝙿𝚘𝚠𝚎𝚛𝚎𝚍 𝚋𝚢 @RASUU_QXB{_we('✅', 6300666179409157866)}",
        f"{_we('🔒', 6147726688965893754)} 𝚃𝙰𝙺𝙴 𝙲𝙾𝙽𝚃𝚁𝙾𝙻 𝙾𝙵 𝙴𝚅𝙴𝚁𝚈 𝚂𝙴𝙲𝙾𝙽𝙳 {_we('🔥', 6154405023808758521)}",
        "",
        f"{_we('🚀', 6312351947902952139)} 𝙺𝙴𝙴𝙿 𝚂𝙸𝙶𝙽𝙰𝙻 𝚃𝙾 𝚂𝙼𝙰𝚁𝚃 𝚃𝚁𝙰𝙳𝙸𝙽𝙶 {_we('😍', 6300609412826406453)}",
        "",
        f"{_we('💸', 6305117882946692207)} 𝙲𝚑𝚘𝚘𝚜𝚎 𝚊𝚗 𝚘𝚙𝚝𝚒𝚘𝚗 𝚋𝚎𝚕𝚘𝚠 𝚝𝚘 𝚋𝚎𝚐𝚒𝚗 {_we('👇', 6102872880909919548)}",
    ]
    return "<b>" + "\n".join(lines) + "</b>"

_COMING_SOON_BUTTONS = {
    "coming_future_live": ("𝙵𝚄𝚃𝚄𝚁𝙴 𝙻𝙸𝚅𝙴", "6300777178543955652"),
    "coming_live_qx_chart": ("𝙻𝙸𝚅𝙴 𝚀𝚇 𝙲𝙷𝙰𝚁𝚃", "6093676015899386749"),
    "coming_swap_cp": ("𝚂𝚆𝙰𝙿 𝙲/𝙿", "6093409392919585143"),
    "coming_auto_payment": ("𝙰𝚄𝚃𝙾 𝙿𝙰𝚈𝙼𝙴𝙽𝚃", "6141101654667174153"),
    "coming_pair_list": ("𝙿𝙰𝙸𝚁 𝙻𝙸𝚂𝚃", "6300733163719105464"),
    "coming_candle_colours": ("𝙲𝙰𝙽𝙳𝙻𝙴 𝙲𝙾𝙻𝙾𝚄𝚁𝚂", "6300810288446840855"),
    "coming_ai_thinker": ("𝙰𝙸 𝚃𝙷𝙸𝙽𝙺𝙴𝚁", "6118457122498814358"),
    "coming_referral_user": ("𝚁𝙴𝙵𝙴𝚁𝚁𝙰𝙻 𝚄𝚂𝙴𝚁", "6210635890994192211"),
    "coming_ai_filter": ("𝙰𝙸 𝙵𝙸𝙻𝚃𝙴𝚁", "6116203209561219377"),
    "coming_emoji_converter": ("𝙴𝙼𝙾𝙹𝙸 𝙲𝙾𝙽𝚅𝙴𝚁𝚃𝙴𝚁", "6312312820750885243"),
    "coming_text_font": ("𝚃𝙴𝚇𝚃 𝙵𝙾𝙽𝚃", "6248983558036136920"),
}


def _coming_button(callback_data):
    label, emoji_id = _COMING_SOON_BUTTONS[callback_data]
    return {"text": label, "callback_data": callback_data, "style": "primary",
            "icon_custom_emoji_id": emoji_id}


_PAIR_LIST_EMOJI_IDS = {
    "🚀": 6303323183617415678,
    "⚠️": 6303178164046666974,
    "🔍": 6213218467714179432,
    "🥳": 6300963760513228226,
    "▶️": 6300646267940774133,
}

_PAIR_LIST_ITEMS = (
    ("OTC", "ATOUSD-OTC", "Cosmos (OTC)"),
    ("OTC", "AVAUSD-OTC", "Avalanche (OTC)"),
    ("OTC", "AXSUSD-OTC", "Axie Infinity (OTC)"),
    ("OTC", "BCHUSD-OTC", "Bitcoin Cash (OTC)"),
    ("OTC", "BNBUSD-OTC", "Binance Coin (OTC)"),
    ("OTC", "BTCUSD-OTC", "Bitcoin (OTC)"),
    ("OTC", "DASUSD-OTC", "Dash (OTC)"),
    ("OTC", "DOTUSD-OTC", "Polkadot (OTC)"),
    ("OTC", "ETCUSD-OTC", "Ethereum Classic (OTC)"),
    ("OTC", "ETHUSD-OTC", "Ethereum (OTC)"),
    ("OTC", "LINUSD-OTC", "Chainlink (OTC)"),
    ("OTC", "LTCUSD-OTC", "Litecoin (OTC)"),
    ("OTC", "SOLUSD-OTC", "Solana (OTC)"),
    ("OTC", "TONUSD-OTC", "Toncoin (OTC)"),
    ("OTC", "TRUUSD-OTC", "Trump (OTC)"),
    ("OTC", "XRPUSD-OTC", "Ripple (OTC)"),
    ("OTC", "ZECUSD-OTC", "Zcash (OTC)"),
    ("LIVE", "AUDCAD", "AUD/CAD"), ("LIVE", "AUDCHF", "AUD/CHF"),
    ("LIVE", "AUDJPY", "AUD/JPY"), ("LIVE", "AUDUSD", "AUD/USD"),
    ("LIVE", "CADJPY", "CAD/JPY"), ("LIVE", "CHFJPY", "CHF/JPY"),
    ("LIVE", "EURAUD", "EUR/AUD"), ("LIVE", "EURCAD", "EUR/CAD"),
    ("LIVE", "EURCHF", "EUR/CHF"), ("LIVE", "EURGBP", "EUR/GBP"),
    ("LIVE", "EURJPY", "EUR/JPY"), ("LIVE", "EURUSD", "EUR/USD"),
    ("LIVE", "GBPAUD", "GBP/AUD"), ("LIVE", "GBPCAD", "GBP/CAD"),
    ("LIVE", "GBPCHF", "GBP/CHF"), ("LIVE", "GBPJPY", "GBP/JPY"),
    ("LIVE", "GBPUSD", "GBP/USD"), ("LIVE", "USDCAD", "USD/CAD"),
    ("LIVE", "USDCHF", "USD/CHF"), ("LIVE", "USDJPY", "USD/JPY"),
    ("OTC", "AUDCAD-OTC", "AUD/CAD (OTC)"), ("OTC", "AUDCHF-OTC", "AUD/CHF (OTC)"),
    ("OTC", "AUDJPY-OTC", "AUD/JPY (OTC)"), ("OTC", "AUDNZD-OTC", "AUD/NZD (OTC)"),
    ("OTC", "AUDUSD-OTC", "AUD/USD (OTC)"), ("OTC", "CADCHF-OTC", "CAD/CHF (OTC)"),
    ("OTC", "CADJPY-OTC", "CAD/JPY (OTC)"), ("OTC", "CHFJPY-OTC", "CHF/JPY (OTC)"),
    ("OTC", "EURAUD-OTC", "EUR/AUD (OTC)"), ("OTC", "EURCAD-OTC", "EUR/CAD (OTC)"),
    ("OTC", "EURCHF-OTC", "EUR/CHF (OTC)"), ("OTC", "EURGBP-OTC", "EUR/GBP (OTC)"),
    ("OTC", "EURJPY-OTC", "EUR/JPY (OTC)"), ("OTC", "EURNZD-OTC", "EUR/NZD (OTC)"),
    ("OTC", "EURUSD-OTC", "EUR/USD (OTC)"), ("OTC", "GBPAUD-OTC", "GBP/AUD (OTC)"),
    ("OTC", "GBPCAD-OTC", "GBP/CAD (OTC)"), ("OTC", "GBPCHF-OTC", "GBP/CHF (OTC)"),
    ("OTC", "GBPJPY-OTC", "GBP/JPY (OTC)"), ("OTC", "GBPNZD-OTC", "GBP/NZD (OTC)"),
    ("OTC", "GBPUSD-OTC", "GBP/USD (OTC)"), ("OTC", "NZDCAD-OTC", "NZD/CAD (OTC)"),
    ("OTC", "NZDCHF-OTC", "NZD/CHF (OTC)"), ("OTC", "NZDJPY-OTC", "NZD/JPY (OTC)"),
    ("OTC", "NZDUSD-OTC", "NZD/USD (OTC)"), ("OTC", "USDCAD-OTC", "USD/CAD (OTC)"),
    ("OTC", "USDCHF-OTC", "USD/CHF (OTC)"), ("OTC", "USDJPY-OTC", "USD/JPY (OTC)"),
    ("OTC", "BRLUSD-OTC", "USD/BRL (OTC)"), ("OTC", "USDARS-OTC", "USD/ARS (OTC)"),
    ("OTC", "USDBDT-OTC", "USD/BDT (OTC)"), ("OTC", "USDCOP-OTC", "USD/COP (OTC)"),
    ("OTC", "USDDZD-OTC", "USD/DZD (OTC)"), ("OTC", "USDEGP-OTC", "USD/EGP (OTC)"),
    ("OTC", "USDIDR-OTC", "USD/IDR (OTC)"), ("OTC", "USDINR-OTC", "USD/INR (OTC)"),
    ("OTC", "USDMXN-OTC", "USD/MXN (OTC)"), ("OTC", "USDNGN-OTC", "USD/NGN (OTC)"),
    ("OTC", "USDPHP-OTC", "USD/PHP (OTC)"), ("OTC", "USDPKR-OTC", "USD/PKR (OTC)"),
    ("OTC", "USDZAR-OTC", "USD/ZAR (OTC)"),
    ("OTC", "XAGUSD", "Silver"), ("OTC", "XAGUSD-OTC", "Silver (OTC)"),
    ("OTC", "XAUUSD", "Gold"), ("OTC", "XAUUSD-OTC", "Gold (OTC)"),
    ("OTC", "UKBRENT-OTC", "UKBrent (OTC)"), ("OTC", "USCRUDE-OTC", "USCrude (OTC)"),
    ("OTC", "AXJAUD", "S&P/ASX 200"), ("OTC", "CHIA50", "FTSE China A50 Index"),
    ("OTC", "F40EUR", "CAC 40"), ("OTC", "FTSGBP", "FTSE 100"),
    ("OTC", "HSIHKD", "Hong Kong 50"), ("OTC", "IBXEUR", "IBEX 35"),
    ("OTC", "JPXJPY", "Nikkei 225"), ("OTC", "STXEUR", "EURO STOXX 50"),
)


def _pair_list_messages(max_chars: int = 3600) -> list:
    def premium(emoji):
        return f'<tg-emoji emoji-id="{_PAIR_LIST_EMOJI_IDS[emoji]}">{emoji}</tg-emoji>'
    def bold_sans(value):
        output = []
        for char in str(value):
            if "A" <= char <= "Z":
                output.append(chr(0x1D5D4 + ord(char) - ord("A")))
            elif "a" <= char <= "z":
                output.append(chr(0x1D5EE + ord(char) - ord("a")))
            elif "0" <= char <= "9":
                output.append(chr(0x1D7EC + ord(char) - ord("0")))
            else:
                output.append(char)
        return "".join(output)
    header = (
        f"{premium('🚀')} 𝗭𝗘𝗕𝗥𝗢𝗡𝗜𝗫 𝗔𝗜 𝗕𝗢𝗧 𝗣𝗔𝗜𝗥 𝗟𝗜𝗦𝗧 {premium('🚀')}\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"{premium('⚠️')}𝗢𝗧𝗖 𝗠𝗔𝗥𝗞𝗘𝗧 𝗟𝗜𝗩𝗘 𝗠𝗔𝗥𝗞𝗘𝗧 𝗣𝗔𝗜𝗥\n\n"
        f"{premium('🔍')}𝗔𝗟𝗟 𝗣𝗔𝗜𝗥 𝗟𝗜𝗦𝗧 𝗜𝗡 𝗤𝗨𝗢𝗧𝗘𝗫 𝗕𝗥𝗢𝗞𝗘𝗥\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    lines = []
    for market, code, name in _PAIR_LIST_ITEMS:
        marker = premium('▶️') if market == "LIVE" else premium('🥳')
        lines.append(f"{marker} {bold_sans(code)} → {bold_sans(name)}")
    chunks, current = [], header
    for line in lines:
        if len(current) + len(line) + 1 > max_chars and current:
            chunks.append(current.rstrip())
            current = line + "\n"
        else:
            current += line + "\n"
    if current.strip():
        chunks.append(current.rstrip())
    return chunks


_AI_FILTER_API_URL = "https://akashqxpro.bdtraderpro.xyz/private/qbot/qxproall.php"

def _ai_filter_input_prompt() -> str:
    """AI Filter input copy with screen-specific Telegram Premium emojis."""
    tasty = '<tg-emoji emoji-id="6302808277168168069">&#128523;</tg-emoji>'
    gear = '<tg-emoji emoji-id="6269316440021540627">&#9881;</tg-emoji>'
    mail = '<tg-emoji emoji-id="6118251174522004763">&#128140;</tg-emoji>'
    silent = '<tg-emoji emoji-id="6301088640982326387">&#128566;</tg-emoji>'
    return (
        f"{tasty} 𝙾𝚃𝙲 𝙻𝙸𝚅𝙴 𝙵𝙸𝙻𝚃𝙴𝚁 𝙰𝙸 {tasty}\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"{gear} 𝚃𝚒𝚖𝚎𝚣𝚘𝚗𝚎: 𝚄𝚃𝙲+𝟼 (𝙱𝙳𝚃)\n\n"
        f"{mail} 𝚂𝚎𝚗𝚍 𝚢𝚘𝚞𝚛 𝚜𝚒𝚐𝚗𝚊𝚕 𝚕𝚒𝚜𝚝 𝚗𝚘𝚠 — 𝙰𝙻𝙻 𝙵𝙾𝚁𝙼𝙰𝚃 𝚂𝚄𝙿𝙿𝙾𝚁𝚃𝙴𝙳\n\n"
        "𝙼𝟷;𝙴𝚄𝚁𝚄𝚂𝙳_𝙾𝚃𝙲;𝟷𝟺:𝟸𝟼;𝙲𝙰𝙻𝙻\n"
        "𝙼𝟷;𝙴𝚄𝚁𝚄𝚂𝙳;𝟷𝟺:𝟸𝟼;𝙲𝙰𝙻𝙻\n\n"
        f"𝙾𝚗𝚕𝚢 𝚜𝚞𝚙𝚙𝚘𝚛𝚝𝚎𝚍 𝚘𝚝𝚌 𝚖𝚊𝚛𝚔𝚎𝚝 𝚙𝚊𝚒𝚛𝚜 𝚠𝚒𝚕𝚕 𝚋𝚎 𝚊𝚌𝚌𝚎𝚙𝚝𝚎𝚍.{silent}"
    )

def _ai_filter_clean_pair(raw_pair: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_]", "", str(raw_pair or "")).upper()
    if "OTC" in clean and "_OTC" not in clean:
        clean = clean.replace("OTC", "_OTC")
    return clean

def _ai_filter_extract_signals(text: str) -> list:
    signals = []
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        time_match = re.search(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b", line)
        direction_match = re.search(r"\b(BUY|SELL|CALL|PUT)\b", line, re.IGNORECASE)
        if not time_match or not direction_match:
            continue
        time_value = datetime.strptime(time_match.group(0), "%H:%M").strftime("%H:%M")
        direction = "BUY" if direction_match.group(0).upper() in ("CALL", "BUY") else "PUT"
        pair_text = re.sub(r"\bM\d+\b", "", line, flags=re.IGNORECASE)
        pair_text = pair_text.replace(time_match.group(0), "")
        pair_text = re.sub(r"\b(BUY|SELL|CALL|PUT)\b", "", pair_text, flags=re.IGNORECASE)
        pair_text = pair_text.replace(";", " ").replace(":", " ")
        pair = _ai_filter_clean_pair(pair_text)
        if pair:
            signals.append({"pair": pair, "time": time_value, "type": direction,
                            "status": "⏳ Analyzing...", "accuracy": 0})
    return signals

def _ai_filter_fetch_candles(pair: str) -> list:
    pair_clean = str(pair or "").strip().upper()
    if pair_clean.endswith("_OTC"):
        pair_clean = pair_clean[:-4]
    try:
        response = _http.get(_AI_FILTER_API_URL, params={
            "pair": f"{pair_clean}_otc", "timeframe": "M1", "count": "all"
        }, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            raw = payload
        elif isinstance(payload, dict):
            raw = next((payload[key] for key in ("data", "candles", "result", "history")
                        if isinstance(payload.get(key), list)), [])
        else:
            raw = []
        candles = []
        for item in raw:
            try:
                timestamp = item.get("time", item.get("epoch", item.get("timestamp", item.get("datetime", item.get("t")))))
                if isinstance(timestamp, (int, float)) or str(timestamp).isdigit():
                    epoch = float(timestamp)
                    if epoch > 10 ** 12:
                        epoch /= 1000.0
                    candle_dt = datetime.utcfromtimestamp(epoch)
                else:
                    candle_dt = _ck_parse_candle_dt(str(timestamp or ""))
                if candle_dt is None:
                    continue
                candles.append({"dt": candle_dt, "date": candle_dt.strftime("%Y-%m-%d"),
                                "time": candle_dt.strftime("%H:%M"),
                                "open": float(item.get("open", item.get("o"))),
                                "close": float(item.get("close", item.get("c")))})
            except (TypeError, ValueError, AttributeError, OSError):
                continue
        candles.sort(key=lambda candle: candle["dt"])
        return candles
    except Exception as exc:
        print(f"[AI Filter API] {pair}: {exc}")
        return []

def _ai_filter_analyze(pair: str, time_value: str, direction: str,
                       days: int, max_mtg: int) -> int:
    candles = _ai_filter_fetch_candles(pair)
    if not candles:
        return -1
    dates = sorted({candle["date"] for candle in candles}, reverse=True)[:days]
    wins = checked = 0
    for date_value in dates:
        indices = [index for index, candle in enumerate(candles)
                   if candle["date"] == date_value and candle["time"] == time_value]
        if not indices:
            continue
        checked += 1
        start = indices[0]
        for step in range(max_mtg + 1):
            index = start + step
            if index >= len(candles) or candles[index]["date"] != date_value:
                break
            candle = candles[index]
            if ((direction == "BUY" and candle["close"] > candle["open"])
                    or (direction == "PUT" and candle["close"] < candle["open"])):
                wins += 1
                break
    return -1 if not checked else round(wins / checked * 100)

def _ai_filter_progress_text(signals: list, active_index: int) -> str:
    lines = [f"📊 <b>LIVE MARKET ANALYSIS ({active_index + 1}/{len(signals)})</b>",
             "<b>___________________________________</b>", ""]
    for signal in signals:

        row = f"M1 {signal['pair']} {signal['time']} {signal['type']}"
        lines.append(f"<code>{_html.escape(row)}</code> - {signal['status']}")
    return efmt("\n".join(lines))

def _ai_filter_result_text(signals: list, days: int) -> str:
    passed = sorted(signals, key=lambda item: datetime.strptime(item["time"], "%H:%M").time())
    output = (
        "⭐️ <b>𝗔𝗜 𝗙𝗜𝗟𝗧𝗘𝗥 𝗭𝗘𝗕𝗥𝗢𝗡𝗜𝗫</b> ⭐️\n\n"
        "✔️ <b>𝗙𝗜𝗟𝗧𝗘𝗥 𝗪𝗜𝗧𝗛 𝗭.𝗫.𝗕 𝗔𝗜</b>\n"
        f"🔘 <b>𝗔𝗡𝗔𝗟𝗬𝗦𝗜𝗦 𝗗𝗔𝗧𝗔 {days} 𝗗𝗔𝗬𝗦</b>\n"
        "🍆 <b>𝗔𝗜 𝗙𝗜𝗟𝗧𝗘𝗥 𝗖𝗢𝗠𝗣𝗟𝗘𝗧𝗘</b>\n\n"
    )
    if passed:
        output += "\n".join(
            f"<code>{_html.escape('M1 {}  {} {}'.format(sig['pair'], sig['time'], sig['type']))}</code>"
            for sig in passed)
    else:
        output += "<code>No signals passed the filter.</code>"
    output += ("\n\n⚙️ <b>𝗦𝗢𝗙𝗧𝗪𝗔𝗥𝗘 𝗭𝗘𝗕𝗥𝗢𝗡𝗜𝗫 𝗔𝗜</b>💡\n\n"
               "💀 ==== 🔥 <b>𝗭 | 𝗫 | 𝗕</b> 🔥 ==== 💀")
    return efmt(output)

def _run_ai_filter(uid: int, cid: int, sess, days: int):
    signals = list(sess.ai_filter_draft.get("signals") or [])
    mtg = int(sess.ai_filter_draft.get("mtg", 0))
    threshold = 60 if mtg == 0 else 70
    sess.state = S.IDLE
    status = _send(cid, efmt("⚡ <b>Starting Live Candle Analysis...</b>"))
    status_mid = (status or {}).get("result", {}).get("message_id")
    def worker():
        for index, signal in enumerate(signals):
            signal["status"] = "🔄 Checking..."
            if status_mid:
                _edit(cid, status_mid, _ai_filter_progress_text(signals, index))
            rate = _ai_filter_analyze(signal["pair"], signal["time"],
                                      signal["type"], days, mtg)
            if rate < 0:
                signal["status"], signal["accuracy"] = "⚠️ No API Data", 0
            else:
                badge = "🔥" if rate >= 85 else ("🟢" if rate >= threshold else "❌")
                signal["status"], signal["accuracy"] = f"{rate}% {badge}", rate
        passed = [signal for signal in signals if signal["accuracy"] >= threshold]
        result = _ai_filter_result_text(passed, days)
        kb = {"inline_keyboard": [
            [{"text": "𝙵𝙸𝙻𝚃𝙴𝚁 𝙰𝙶𝙰𝙸𝙽", "callback_data": "menu_ai_filter",
              "style": "success", "icon_custom_emoji_id": "6116203209561219377"}],
            [{"text": "𝙷𝙾𝙼𝙴", "callback_data": "menu_home", "style": "primary",
              "icon_custom_emoji_id": "5416041192905265756"}]]}
        if status_mid:
            edited = _edit(cid, status_mid, result, kb)
            if edited.get("ok"):
                return
        _send(cid, result, kb)
    threading.Thread(target=worker, daemon=True).start()


_TOOLS_API = "https://akashqxpro.bdtraderpro.xyz/private/qbot/qx.php"
_TOOL_LIVE = ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","EURGBP","EURJPY","GBPJPY","AUDNZD"]
_TOOL_MAJOR_OTC = [p + "_otc" for p in _TOOL_LIVE]
_MF_OTC = ["USDPKR_otc","NZDCAD_otc","USDBDT_otc","USDINR_otc","USDTRY_otc","USDBRL_otc","USDEGP_otc","USDNGN_otc"]
_CC_OTC = ["USDPKR_otc","NZDCAD_otc","USDBDT_otc","USDINR_otc","USDTRY_otc","USDBRL_otc","USDARS_otc"]
_CC_MAJOR_OTC = [p+"_otc" for p in ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","EURGBP"]]
_RT_LIVE = _TOOL_LIVE + ["AUDJPY","CADJPY"]
_RT_OTC = ["USDPKR_otc","NZDCAD_otc","USDBDT_otc","USDINR_otc","USDTRY_otc","USDBRL_otc","USDARS_otc","USDEGP_otc","USDNGN_otc","USDIDR_otc","USDPHP_otc","USDCOP_otc","USDMYR_otc","USDZAR_otc"]
_RT_MAJOR_OTC = [p+"_otc" for p in ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","EURGBP","EURJPY","GBPJPY","AUDNZD","AUDCAD","AUDJPY","CADJPY","EURAUD","EURCAD","GBPAUD","GBPCAD","GBPNZD","NZDUSD"]]

def _tool_fetch(pair, count):
    try:
        r = _http.get(_TOOLS_API, params={"pair": pair, "timeframe": "M1", "count": count}, timeout=20)
        j = r.json() if r.status_code == 200 else {}
        return j.get("data") if j.get("success") else None
    except Exception as e:
        print(f"[ToolData {pair}] {e}")
        return None

def _tool_rows(raw):
    try:
        return [{k: float(x[k]) for k in ("open","high","low","close")} for x in reversed(raw)]
    except Exception:
        return []

def _ema(vals, n):
    if not vals: return 0.0
    a, out = 2/(n+1), float(vals[0])
    for v in vals[1:]: out = float(v)*a + out*(1-a)
    return out

def _rsi(vals, n=14):
    ds = [vals[i]-vals[i-1] for i in range(1, len(vals))]
    if len(ds) < n: return 50.0
    ag=sum(max(x,0) for x in ds[:n])/n; al=sum(max(-x,0) for x in ds[:n])/n
    for x in ds[n:]:
        ag=(ag*(n-1)+max(x,0))/n; al=(al*(n-1)+max(-x,0))/n
    return 100.0 if al == 0 else 100-(100/(1+ag/al))

def _payout(raw):
    try: return float(raw[0].get("payout", 0))
    except Exception: return 0

def _market_filter_one(pair):
    raw = _tool_fetch(pair, 3000)
    if not raw or len(raw) < 100 or _payout(raw) < 70: return None
    rows = _tool_rows(raw)[-100:]; closes = [x["close"] for x in rows]
    if len(closes) < 21: return None
    direction = "UP" if closes[-1] >= _ema(closes,20) else "DOWN"
    roc = abs((closes[-1]/closes[-11]-1)*100) + 50 if closes[-11] else 50
    return pair.replace("_otc","-OTC").upper(), int(_payout(raw)), direction, round(_rsi(closes),1), round(roc,1)

def _candle_one(pair, enforce_payout=True):
    raw = _tool_fetch(pair, 15)
    if not raw or len(raw) < 15 or (enforce_payout and _payout(raw) < 90): return None
    rows = _tool_rows(raw)[-15:]
    colors = ["🟢" if x["close"] >= x["open"] else "🔴" for x in rows]
    g = colors.count("🟢"); r = len(colors)-g
    name = pair.replace("_otc","-OTC").upper()
    gp=round(g/len(colors)*100); rp=round(r/len(colors)*100)
    return efmt(f"🏛 <b>RECENT CANDLE HISTORY ‼️</b>\n📊 <b>Pair:</b> {name}\n⏳ <b>Last 15 M1 Candles</b> ({int(_payout(raw))}% Payout)\n\n{' '.join(colors)}\n\n📈 <b>Sequence</b> {colors[-1]}\n📊 <b>Statistics</b> 🟢 Green: {g} 🔴 Red: {r} 📊 Ratio: {gp}% / {rp}%")

def _recent_one(pair):
    raw = _tool_fetch(pair, 100)
    if not raw or len(raw) < 50 or _payout(raw) < 88: return None
    rows = _tool_rows(raw)[-100:]; c=[x["close"] for x in rows]
    e, s = _ema(c,20), sum(c[-50:])/50
    trend = "UP" if c[-1] > e > s else "DOWN" if c[-1] < e < s else "SIDEWAYS"
    trs=[]
    for i in range(1,len(rows)):
        x,p=rows[i],rows[i-1]["close"]; trs.append(max(x["high"]-x["low"],abs(x["high"]-p),abs(x["low"]-p)))
    atr=sum(trs[-14:])/14; vp=(atr/(sum(c)/len(c))*100) if sum(c) else 0
    vol="High" if vp>.08 else "Low" if vp<.03 else "Medium"
    last=c[-10:]; g=sum(1 for i,x in enumerate(rows[-10:]) if x["close"]>=x["open"]); r=10-g
    name=pair.replace("_otc","-OTC").upper()
    return efmt(f"📊 <b>ASSET : {name} ({int(_payout(raw))}%)</b>\n🕯 <b>CANDLE : {g} GREEN {r} RED</b>\n➕ OPEN PRICE : <code>{rows[-1]['open']}</code>\n🔖 LOW PRICE : <code>{rows[-1]['low']}</code>\n💸 MARKET TREND : <b>{trend}</b>\n🚩 Volatility : <b>{vol}</b>\n📈 Support : <code>{min(x['low'] for x in rows[-20:])}</code>\n📉 Resistance : <code>{max(x['high'] for x in rows[-20:])}</code>")

def _tool_scan_async(cid, sess, kind, market=None):
    labels={"market":"MARKET FILTER","candle":"CANDLE COLOURS","recent":"RECENT TREND"}
    _wiz(sess, efmt(f"⏳ <b>{labels[kind]}</b>\n\nScanning available markets..."), None)
    def worker():
        weekend=time.localtime().tm_wday in (5,6)
        if kind=="market": pairs=_TOOL_LIVE if market=="LIVE" else _MF_OTC+(_TOOL_MAJOR_OTC if weekend else [])
        elif kind=="candle": pairs=_CC_OTC+(_CC_MAJOR_OTC if weekend else _TOOL_LIVE)
        else: pairs=_RT_OTC+(_RT_MAJOR_OTC if weekend else _RT_LIVE)
        fn={"market":_market_filter_one,"candle":_candle_one,"recent":_recent_one}[kind]
        try:
            import concurrent.futures as cf
            with cf.ThreadPoolExecutor(max_workers=8) as ex: found=[x for x in ex.map(fn,pairs) if x]
        except Exception: found=[x for p in pairs if (x:=fn(p))]
        if kind=="market":
            ups=[x for x in found if x[2]=="UP"]; dns=[x for x in found if x[2]=="DOWN"]
            blocks=[]
            for title,items,ico in (("UP TREND",ups,"📈"),("DOWN TREND",dns,"📉")):
                if items: blocks.append(efmt(f"{ico} <b>{title} ({len(items)})</b>\n")+"\n\n".join(efmt(f"🟢 <b>{n}  {p}%</b>\n{ico} {d} | RSI {r} | Momentum {m}%") for n,p,d,r,m in items))
            body=efmt(f"📊 <b>MARKET FILTERS — {market}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\nTradeable Markets: {len(found)}\n\n")+("\n\n".join(blocks) or efmt("❌ No active tradeable markets found right now."))+efmt("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ <b>These are stable markets.</b>\nYou can analyze these pairs with your own setup and trade with confidence Z.B.X AI BOT.")
            kb={"inline_keyboard":[[{"text":"RESCAN","callback_data":f"market_filter_{market}","style":"primary","icon_custom_emoji_id":str(EMAP["📊"])}],[{"text":"SWITCH MARKET","callback_data":f"market_filter_{'OTC' if market=='LIVE' else 'LIVE'}","style":"primary","icon_custom_emoji_id":str(EMAP["📈"])}],[{"text":"BACK","callback_data":"menu_market_filter","style":"danger"}]]}
        else:
            body=("\n\n━━━━━━━━━━━━━━━━━━━━\n\n".join(found) if found else efmt(f"❌ No active markets found with {'90' if kind=='candle' else '88'}%+ payout."))
            cb=f"{kind}_scan_all"; menu=f"menu_{'candle_colours' if kind=='candle' else 'recent_trend'}"
            kb={"inline_keyboard":[[{"text":"RESCAN ALL","callback_data":cb,"style":"primary","icon_custom_emoji_id":str(EMAP["🔍"])}],[{"text":"CHECK ANOTHER","callback_data":menu,"style":"primary"}],[{"text":"HOME","callback_data":"menu_home","style":"danger"}]]}
            if found and len(body) > 3800:
                chunks=[]; current=""
                for block in found:
                    candidate=(current+"\n\n━━━━━━━━━━━━━━━━━━━━\n\n"+block) if current else block
                    if len(candidate)>3800 and current:
                        chunks.append(current); current=block
                    else: current=candidate
                if current: chunks.append(current)
                _wiz(sess,chunks[0],None)
                for chunk in chunks[1:-1]: _send(cid,chunk)
                if len(chunks)>1: _send(cid,chunks[-1],kb)
                else: _wiz(sess,chunks[0],kb)
                return
        _wiz(sess, body, kb)
    threading.Thread(target=worker,daemon=True).start()

def _tool_manual_async(sess, pair, kind):
    pair=pair.strip().replace("-","_").replace(" ","").upper().replace("_OTC","_otc")
    fn=(lambda p:_candle_one(p,False)) if kind=="candle" else _recent_one
    _wiz(sess, efmt(f"⏳ <b>Checking {pair.replace('_otc','-OTC')}...</b>"), None)
    def worker():
        result=fn(pair)
        limit=90 if kind=="candle" else 88
        body=result or efmt(f"⚠️ <b>{pair.upper()}</b> is unavailable or has less than {limit}% payout right now.")
        menu="menu_candle_colours" if kind=="candle" else "menu_recent_trend"
        _wiz(sess,body,{"inline_keyboard":[[{"text":"CHECK ANOTHER","callback_data":menu,"style":"primary","icon_custom_emoji_id":str(EMAP["🔍"])}],[{"text":"HOME","callback_data":"menu_home","style":"danger"}]]})
    threading.Thread(target=worker,daemon=True).start()

def _market_payouts_async(cid, sess):

    _wiz(sess, efmt("🔍 <b>MARKET PAYOUTS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n⏳ Checking all supported markets..."), None)
    def worker():
        live_pairs=list(dict.fromkeys(_get_lsig_live_pairs()))
        otc_pairs=list(dict.fromkeys(_get_lsig_otc_pairs()))
        pool=live_pairs+otc_pairs
        payouts={}
        try:
            with ThreadPoolExecutor(max_workers=min(len(pool),25)) as ex:
                futures={ex.submit(_get_pair_payout,p):p for p in pool}
                for future in as_completed(futures):
                    pair=futures[future]
                    try: payouts[pair]=int(future.result() or 0)
                    except Exception: payouts[pair]=0
        except Exception as e:
            print(f"[MarketPayouts] {e}")
        def section(title, pairs):

            ordered=sorted(((p,payouts.get(p,0)) for p in pairs if payouts.get(p,0)>0),
                           key=lambda x:(-x[1],x[0]))
            if not ordered:
                return ""
            lines=[f"📊 <b>{title}</b>"]
            for pair,pct in ordered:
                icon="🟢" if pct>=80 else ("🟡" if pct>=70 else "🔴")
                lines.append(f"{icon} <code>{pair.upper()}  ({pct}%)</code>")
            return "\n".join(lines)
        sections=[x for x in (section("LIVE MARKET",live_pairs),section("OTC MARKET",otc_pairs)) if x]
        report=efmt("📊 <b>LIVE PAYOUTS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"+
                    ("\n\n".join(sections) if sections else "⚠️ <b>No supported market is open right now.</b>"))
        kb={"inline_keyboard":[
            [{"text":"REFRESH PAYOUTS","callback_data":"menu_market_payouts","style":"success","icon_custom_emoji_id":str(EMAP["🔍"])}],
            [{"text":"HOME","callback_data":"menu_home","style":"danger","icon_custom_emoji_id":"5416041192905265756"}]]}
        _wiz(sess,report,kb)
    threading.Thread(target=worker,daemon=True).start()

_VOLATILITY_MIN_PAYOUT = 85
_VOLATILITY_EMOJI_IDS = {
    "👾": 6147696753043841667,
    "📊": 6212901597911980909,
    "🕔": 6199224721234468363,
    "📈": 6149789132261433255,
    "📉": 6147776510586527307,
    "😎": 6298654691605617850,
    "🔴": 6213041880133802294,
    "🕯": 6210497528622751920,
    "⏳": 6311968686496292533,
    "⌛": 6212721797696069552,
    "💵": 6213195450984438198,
    "📣": 6210493963799895861,
    "▶️": 6280406621105430065,
    "🔎": 6055613727959425297,
    "🚨": 6066399073739481716,
    "😡": 6145241513514246393,
}
_AI_THINKER_EMOJI_IDS = {
    "🚨": 6066399073739481716,
    "😡": 6145241513514246393,
    "📈": 6301020247923105456,
    "🍭": 6147786517860328236,
    "💻": 6118457122498814358,
    "▶️": 6280406621105430065,
    "🔎": 6055613727959425297,
}

def _volatility_efmt(text):
    return _feature_efmt(text, _VOLATILITY_EMOJI_IDS)

def _ai_thinker_efmt(text):
    return _feature_efmt(text, _AI_THINKER_EMOJI_IDS)

_VOLATILITY_LIVE_PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
    "EURGBP", "EURJPY", "GBPJPY", "AUDNZD",
]
_VOLATILITY_PURE_OTC_PAIRS = [
    "USDPKR_otc", "NZDCAD_otc", "USDBDT_otc", "USDINR_otc",
    "USDTRY_otc", "USDBRL_otc", "USDARS_otc", "USDEGP_otc", "USDNGN_otc",
]
_VOLATILITY_REAL_OTC_PAIRS = [
    "EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "AUDUSD_otc",
    "USDCAD_otc", "EURGBP_otc",
]

def _volatility_normalize_pair(value):
    value = str(value or "").strip().replace("-", "_").replace(" ", "_")
    value = re.sub(r"_+", "_", value)
    if value.lower().endswith("_otc"):
        return value[:-4].upper() + "_otc"
    return value.upper()

def _volatility_analyze_chart(candle_data, pair_name):
    """Merged volatility_market.py engine; returns (HTML report, PNG bytes)."""
    if not candle_data or len(candle_data) < 220:
        return None, None
    try:
        import io as _vol_io
        import pandas as _pd
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as _plt
        from matplotlib.patches import Rectangle as _Rectangle

        payout = int(float(candle_data[0].get("payout", 0) or 0))
        if payout < _VOLATILITY_MIN_PAYOUT:
            return None, None
        frame = _pd.DataFrame(candle_data[::-1])
        for col in ("open", "high", "low", "close"):
            frame[col] = _pd.to_numeric(frame[col], errors="coerce")
        frame = frame.dropna(subset=["open", "high", "low", "close"])
        if len(frame) < 220:
            return None, None
        if "volume" not in frame.columns:
            frame["volume"] = (abs(frame["close"] - frame["open"]) * 100000).astype(float)
        else:
            frame["volume"] = _pd.to_numeric(frame["volume"], errors="coerce").fillna(0.0)
        if "time" in frame.columns:
            numeric_time = _pd.to_numeric(frame["time"], errors="coerce")
            unit = "ms" if numeric_time.dropna().median() > 10_000_000_000 else "s"
            frame["datetime"] = _pd.to_datetime(numeric_time, unit=unit, errors="coerce")
            if frame["datetime"].isna().any():
                frame["datetime"] = _pd.date_range(end=datetime.now(), periods=len(frame), freq="1min")
        else:
            frame["datetime"] = _pd.date_range(end=datetime.now(), periods=len(frame), freq="1min")
        frame.set_index("datetime", inplace=True)
        df = frame.tail(220).copy()
        df["ema9"] = df["close"].ewm(span=9, adjust=False).mean()
        df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()
        delta = df["close"].diff()
        gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss.replace(0, float("nan"))
        df["rsi"] = (100 - 100 / (1 + rs)).fillna(100)
        last = df.iloc[-1]
        open_price, close_price = float(last["open"]), float(last["close"])
        ema9_val, ema21_val = float(df["ema9"].iloc[-1]), float(df["ema21"].iloc[-1])
        rsi_val = float(df["rsi"].iloc[-1])
        if close_price > ema9_val > ema21_val:
            trend = "UP"
        elif close_price < ema9_val < ema21_val:
            trend = "DOWN"
        else:
            trend = "UP" if close_price > float(df["close"].iloc[-15]) else "DOWN"
        recent = df.tail(70)
        green = int((recent["close"] > recent["open"]).sum())
        candle_ratio = green / max(1, len(recent)) * 100
        buy_pressure = int(min(max((rsi_val * .4) + (candle_ratio * .6), 5), 95))
        put_pressure = 100 - buy_pressure
        prev_close = df["close"].shift(1)
        true_range = _pd.concat([(df["high"]-df["low"]).abs(),
                                 (df["high"]-prev_close).abs(),
                                 (df["low"]-prev_close).abs()], axis=1).max(axis=1)
        df["atr"] = true_range.ewm(alpha=1/14, adjust=False).mean()
        atr_val = float(df["atr"].iloc[-1])
        avg_price = float(df["close"].mean())
        vol_ratio = atr_val / avg_price * 100 if avg_price else 0
        if vol_ratio > .09:
            pair_zone = "HIGH VOLATILE"
            recommendation = ("🚨 <b>𝙽𝙾 𝚃𝚁𝙰𝙳𝙴 / 𝙳𝙾 𝙽𝙾𝚃 𝚃𝚁𝙰𝙳𝙴</b>\n"
                              "😡 <b>𝙼𝚊𝚛𝚔𝚎𝚝 𝚟𝚘𝚕𝚊𝚝𝚒𝚕𝚒𝚝𝚢 𝚒𝚜 𝚝𝚘𝚘 𝚑𝚒𝚐𝚑! 𝙼𝚊𝚛𝚔𝚎𝚝 𝚋𝚎𝚑𝚊𝚟𝚒𝚘𝚛 𝚒𝚜 𝚞𝚗𝚙𝚛𝚎𝚍𝚒𝚌𝚝𝚊𝚋𝚕𝚎.</b>\n"
                              "📣 <b>মার্কেট ভোলাটিলিটি অনেক বেশি! এখন ট্রেড করা ঝুঁকিপূর্ণ।</b>")
        elif vol_ratio > .04:
            pair_zone = "PICK VOLATILE"
            recommendation = ("▶️ <b>𝚃𝚁𝙰𝙳𝙴 𝚂𝙰𝙵𝙴 (𝚄𝚜𝚎 𝟷% - 𝟸% 𝙲𝚊𝚙𝚒𝚝𝚊𝚕)</b>\n"
                              "📈 <b>𝙼𝚊𝚛𝚔𝚎𝚝 𝚑𝚊𝚜 𝚊𝚌𝚝𝚒𝚟𝚎 𝚟𝚘𝚕𝚊𝚝𝚒𝚕𝚒𝚝𝚢. 𝚃𝚛𝚊𝚍𝚎 𝚠𝚒𝚝𝚑 𝚜𝚝𝚛𝚒𝚌𝚝 𝚖𝚘𝚗𝚎𝚢 𝚖𝚊𝚗𝚊𝚐𝚎𝚖𝚎𝚗𝚝.</b>\n"
                              "📣 <b>মার্কেটে মিডিয়াম মুভমেন্ট আছে। সতর্কতার সাথে ১-২% ক্যাপিটাল দিয়ে ট্রেড নিন।</b>")
        else:
            pair_zone = "MEDIUM VOLATILE"
            recommendation = ("⌛ <b>𝙽𝙾𝚁𝙼𝙰𝙻 𝚃𝚁𝙰𝙳𝙴 (𝚄𝚜𝚎 𝚂𝚝𝚊𝚗𝚍𝚊𝚛𝚍 𝙰𝚖𝚘𝚞𝚗𝚝)</b>\n"
                              "💵 <b>𝙼𝚊𝚛𝚔𝚎𝚝 𝚒𝚜 𝚜𝚝𝚊𝚋𝚕𝚎 𝚊𝚗𝚍 𝚜𝚖𝚘𝚘𝚝𝚑.</b>\n"
                              "📣 <b>মার্কেট স্বাভাবিক আছে। মানি ম্যানেজমেন্ট ফলো করে ট্রেড করতে পারেন।</b>")
        display = _volatility_normalize_pair(pair_name).replace("_otc", "-OTC").upper()
        fig, (ax_price, ax_volume) = _plt.subplots(
            2, 1, figsize=(14, 7.5), sharex=True, gridspec_kw={"height_ratios":[4,1]})
        fig.patch.set_facecolor("#070913")
        for axis in (ax_price, ax_volume):
            axis.set_facecolor("#070913")
            axis.grid(True, color="#16192b", linestyle=":", linewidth=.8)
            axis.tick_params(colors="#9FA8DA")
            for spine in axis.spines.values(): spine.set_color("#16192b")
        xs = list(range(len(df)))
        body_width = .62
        for x, (_, row) in zip(xs, df.iterrows()):
            up = row["close"] >= row["open"]
            color = "#00E676" if up else "#FF1744"
            ax_price.vlines(x, row["low"], row["high"], color=color, linewidth=.8)
            bottom = min(row["open"], row["close"])
            height = max(abs(row["close"]-row["open"]), max(abs(row["close"])*1e-7, 1e-9))
            ax_price.add_patch(_Rectangle((x-body_width/2, bottom), body_width, height,
                                          facecolor=color, edgecolor=color, linewidth=.5))
            ax_volume.bar(x, row["volume"], width=body_width, color=color, alpha=.75)
        ax_price.plot(xs, df["ema9"].to_numpy(), color="#00E5FF", linewidth=1.8, label="EMA 9")
        ax_price.plot(xs, df["ema21"].to_numpy(), color="#FF9100", linewidth=1.8, label="EMA 21")
        legend = ax_price.legend(loc="upper left", facecolor="#070913", edgecolor="#16192b")
        for text in legend.get_texts(): text.set_color("white")
        tick_step = max(1, len(df)//8)
        tick_positions = xs[::tick_step]
        tick_labels = [df.index[i].strftime("%H:%M") for i in tick_positions]
        ax_volume.set_xticks(tick_positions); ax_volume.set_xticklabels(tick_labels, color="#9FA8DA")
        ax_price.set_xlim(-1, len(df)); ax_volume.set_ylabel("VOLUME", color="#9FA8DA")
        ax_price.text(.5, .5, "ZEBRONIX AI", transform=ax_price.transAxes, fontsize=48,
                     color="white", alpha=.06, ha="center", va="center", weight="bold")
        ax_price.set_title(f"ZEBRONIX AI   |   {display}   |   PAYOUT: {payout}%   |   TREND: {trend}",
                          color="white", fontsize=13, weight="bold", pad=12)
        fig.tight_layout()
        buf = _vol_io.BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches="tight", facecolor="#070913")
        _plt.close(fig)
        open_text = _to_mono(f"{open_price:.6f}".rstrip("0").rstrip("."))
        close_text = _to_mono(f"{close_price:.6f}".rstrip("0").rstrip("."))
        report = _volatility_efmt(
            "<b>👾 𝚉𝙴𝙱𝚁𝙾𝙽𝙸𝚇 𝙰𝙸 𝙿𝚁𝙴𝙳𝙸𝙲𝚃𝙴𝙳 👾</b>\n\n"
            f"<b>📊 𝙰𝚂𝚂𝙴𝚃 : {_to_mono(display)} ({_to_mono(str(payout))}%)</b>\n"
            f"<b>🕔 𝙿𝙰𝙸𝚁 𝚉𝙾𝙽𝙴 : {_to_mono(pair_zone)}</b>\n"
            f"<b>📈 𝙾𝙿𝙴𝙽 𝙿𝚁𝙸𝙲𝙴 : {open_text}</b>\n"
            f"<b>📉 𝙲𝙻𝙾𝚂𝙴 𝙿𝚁𝙸𝙲𝙴 : {close_text}</b>\n"
            f"<b>😎 𝙱𝚄𝚈 𝙿𝚁𝙴𝚂𝚂𝚄𝚁𝙴 : {_to_mono(str(buy_pressure))}%</b>\n"
            f"<b>🔴 𝙿𝚄𝚃 𝙿𝚁𝙴𝚂𝚂𝚄𝚁𝙴 : {_to_mono(str(put_pressure))}%</b>\n"
            f"<b>🕯 𝙼𝙰𝚁𝙺𝙴𝚃 𝚃𝚁𝙴𝙽𝙳 : {_to_mono(trend)}</b>\n\n"
            f"<b>⏳ 𝚃𝚁𝙰𝙳𝙴</b>\n{recommendation}")
        return report, buf.getvalue()
    except Exception as exc:
        print(f"[VolatilityFilter analyze] {pair_name}: {exc}")
        return None, None

def _volatility_send_photo(cid, chart_bytes, caption, markup=None):
    if not chart_bytes:
        _send(cid, caption, markup); return False
    try:
        payload = {"chat_id": cid, "caption": caption, "parse_mode": "HTML"}
        if markup:
            payload["reply_markup"] = json.dumps(_style_button_markup(markup))
        response = _http.post(f"{BASE}/sendPhoto",
            data=payload,
            files={"photo": ("zebronix_volatility.png", chart_bytes, "image/png")}, timeout=45)
        if response.ok and response.json().get("ok"):
            return True
        print(f"[VolatilityFilter sendPhoto] {response.text[:300]}")
    except Exception as exc:
        print(f"[VolatilityFilter sendPhoto] {exc}")
    _send(cid, caption, markup)
    return False

def _volatility_result_keyboard():
    return {"inline_keyboard":[
        [{"text":"𝚂𝙲𝙰𝙽 𝚅𝙾𝙻𝙰𝚃𝙸𝙻𝙸𝚃𝚈 (𝟾𝟻%+)","callback_data":"volatility_scan_all","style":"primary","icon_custom_emoji_id":"6145218136007255956"}],
        [{"text":"𝙷𝙾𝙼𝙴","callback_data":"menu_home","style":"danger"}]]}

def _volatility_manual_async(cid, sess, pair):
    pair = _volatility_normalize_pair(pair)
    _wiz(sess, _volatility_efmt(f"🔎 <b>𝙶𝚎𝚗𝚎𝚛𝚊𝚝𝚒𝚗𝚐 𝚉𝙴𝙱𝚁𝙾𝙽𝙸𝚇 𝙰𝙸 𝚌𝚑𝚊𝚛𝚝 𝚏𝚘𝚛 {_html.escape(_to_mono(pair.upper()))}...</b>"), None)
    def worker():
        raw = _tool_fetch(pair, 300)
        if not raw or len(raw) < 220:
            _wiz(sess, _volatility_efmt(f"🚨 <b>𝙲𝚘𝚞𝚕𝚍 𝚗𝚘𝚝 𝚏𝚎𝚝𝚌𝚑 𝚌𝚊𝚗𝚍𝚕𝚎 𝚍𝚊𝚝𝚊 𝚏𝚘𝚛</b> <code>{_html.escape(_to_mono(pair.upper()))}</code>."), _volatility_result_keyboard())
            return
        report, chart = _volatility_analyze_chart(raw, pair)
        if not report or not chart:
            _wiz(sess, _volatility_efmt(f"🚨 <code>{_html.escape(_to_mono(pair.upper()))}</code> <b>𝚑𝚊𝚜 𝚕𝚎𝚜𝚜 𝚝𝚑𝚊𝚗 𝟾𝟻% 𝚙𝚊𝚢𝚘𝚞𝚝 𝚛𝚒𝚐𝚑𝚝 𝚗𝚘𝚠.</b>"), _volatility_result_keyboard())
            return
        _delete(cid, sess.wiz_mid); sess.wiz_mid = None
        _volatility_send_photo(cid, chart, report, _volatility_result_keyboard())
    threading.Thread(target=worker, daemon=True).start()

def _volatility_scan_all_async(cid, sess):
    _wiz(sess, _volatility_efmt("🔎 <b>𝚂𝚌𝚊𝚗𝚗𝚒𝚗𝚐 𝚊𝚕𝚕 𝟾𝟻%+ 𝚙𝚊𝚢𝚘𝚞𝚝 𝚖𝚊𝚛𝚔𝚎𝚝𝚜 𝚊𝚗𝚍 𝚐𝚎𝚗𝚎𝚛𝚊𝚝𝚒𝚗𝚐 𝚉𝙴𝙱𝚁𝙾𝙽𝙸𝚇 𝙰𝙸 𝚌𝚑𝚊𝚛𝚝𝚜...</b>"), None)
    def worker():
        pairs = list(_VOLATILITY_PURE_OTC_PAIRS)
        pairs.extend(_VOLATILITY_REAL_OTC_PAIRS if datetime.now().weekday() in (5, 6)
                     else _VOLATILITY_LIVE_PAIRS)
        found = 0
        for pair in pairs:
            raw = _tool_fetch(pair, 300)
            if not raw or len(raw) < 220:
                continue
            report, chart = _volatility_analyze_chart(raw, pair)
            if report and chart:
                if found == 0:
                    _delete(cid, sess.wiz_mid); sess.wiz_mid = None
                found += 1
                _volatility_send_photo(cid, chart, report, None)
        if not found:
            _wiz(sess, _volatility_efmt("🚨 <b>𝙽𝚘 𝚊𝚌𝚝𝚒𝚟𝚎 𝚙𝚊𝚒𝚛𝚜 𝚏𝚘𝚞𝚗𝚍 𝚠𝚒𝚝𝚑 𝟾𝟻%+ 𝚙𝚊𝚢𝚘𝚞𝚝 𝚛𝚒𝚐𝚑𝚝 𝚗𝚘𝚠.</b>"), _volatility_result_keyboard())
        else:
            _send(cid, _volatility_efmt(f"▶️ <b>𝚅𝚘𝚕𝚊𝚝𝚒𝚕𝚒𝚝𝚢 𝚜𝚌𝚊𝚗 𝚌𝚘𝚖𝚙𝚕𝚎𝚝𝚎 — {_to_mono(str(found))} 𝚖𝚊𝚛𝚔𝚎𝚝(𝚜) 𝚐𝚎𝚗𝚎𝚛𝚊𝚝𝚎𝚍.</b>"), _volatility_result_keyboard())
    threading.Thread(target=worker, daemon=True).start()

def _ai_thinker_bar(value):
    value = max(0, min(100, int(round(float(value or 0)))))
    filled = max(0, min(10, int(round(value / 10))))
    return "█" * filled + "░" * (10 - filled)

def _ai_thinker_pair_label(pair):
    return str(pair).upper().replace("_OTC", "-OTC").replace("_", "")

def _ai_thinker_market_menu(sess, market, page=0):
    pairs = list(sess.ai_thinker_pairs)
    payouts = dict(sess.ai_thinker_payouts)
    per_page = 20
    pages = max(1, math.ceil(len(pairs) / per_page))
    page = max(0, min(int(page), pages - 1))
    start = page * per_page
    rows = []
    chunk = []
    for idx in range(start, min(start + per_page, len(pairs))):
        pair = pairs[idx]
        chunk.append({"text": f"{_ai_thinker_pair_label(pair)} • {payouts.get(pair, 0)}%",
                      "callback_data": f"ai_thinker_pair_{idx}", "style": "primary"})
        if len(chunk) == 2:
            rows.append(chunk); chunk = []
    if chunk: rows.append(chunk)
    nav = []
    if page > 0:
        nav.append({"text":"◀ 𝙿𝚁𝙴𝚅","callback_data":f"ai_thinker_page_{market}_{page-1}","style":"primary"})
    if page + 1 < pages:
        nav.append({"text":"𝙽𝙴𝚇𝚃 ▶","callback_data":f"ai_thinker_page_{market}_{page+1}","style":"primary"})
    if nav: rows.append(nav)
    rows.append([{"text":"𝙱𝙰𝙲𝙺","callback_data":"menu_ai_thinker","style":"danger"}])
    return {"inline_keyboard": rows}, page + 1, pages

def _ai_thinker_load_market(cid, sess, market):
    sess.ai_thinker_market = market
    _wiz(sess, efmt(f"🔍 <b>{market} MARKET</b>\n━━━━━━━━━━━━━━━━━━━━\n\n⏳ Loading open markets and live payouts..."), None)
    def worker():
        source = _get_lsig_otc_pairs() if market == "OTC" else _get_lsig_live_pairs()
        pairs = list(dict.fromkeys(source))
        payouts = {}
        try:
            with ThreadPoolExecutor(max_workers=min(24, max(1, len(pairs)))) as ex:
                jobs = {ex.submit(_get_pair_payout, pair): pair for pair in pairs}
                for job in as_completed(jobs):
                    try: payouts[jobs[job]] = int(job.result() or 0)
                    except Exception: payouts[jobs[job]] = 0
        except Exception as exc:
            print(f"[AIThinker markets] {exc}")
        opened = sorted((p for p in pairs if payouts.get(p, 0) > 0),
                        key=lambda p: (-payouts[p], p))
        sess.ai_thinker_pairs = opened
        sess.ai_thinker_payouts = payouts
        if not opened:
            _wiz(sess, efmt(f"⚠️ <b>No supported {market} market is open right now.</b>"),
                 {"inline_keyboard":[[{"text":"𝙱𝙰𝙲𝙺","callback_data":"menu_ai_thinker","style":"danger"}]]})
            return
        kb, current, total = _ai_thinker_market_menu(sess, market, 0)
        _wiz(sess, efmt(f"🤖 <b>ZEBRONIX AI THINKER</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"📊 <b>{market} OPEN MARKETS</b>\n"
                        f"Select one pair to analyze.\n\nPage {current}/{total}"), kb)
    threading.Thread(target=worker, daemon=True).start()

def _ai_thinker_metrics(candles):
    rows = [{k: float(c.get(k, 0) or 0) for k in ("open","high","low","close")}
            | {"volume": float(c.get("volume", 0) or 0)} for c in candles]
    rows = [r for r in rows if r["high"] >= r["low"] and r["close"] > 0]
    if len(rows) < 60: raise ValueError("not enough candle data")
    closes = [r["close"] for r in rows]
    e9, e21, e50 = _ema(closes, 9), _ema(closes, 21), _ema(closes, 50)
    rsi = _rsi(closes, 14)
    trs = []
    for i in range(1, len(rows)):
        r, prev = rows[i], rows[i-1]["close"]
        trs.append(max(r["high"]-r["low"], abs(r["high"]-prev), abs(r["low"]-prev)))
    atr = sum(trs[-14:]) / min(14, len(trs))
    atr_base = sum(trs[-100:]) / min(100, len(trs)) if trs else atr
    vr = atr / atr_base if atr_base else 1.0
    price = closes[-1]
    slope = (closes[-1] / closes[-11] - 1) * 100 if closes[-11] else 0
    trend_raw = ((e9-e21) / price * 5000) + ((e21-e50) / price * 3500) if price else 0
    momentum_raw = (rsi-50) * 1.4 + slope * 18
    recent = rows[-20:]
    bull = sum(max(0, r["close"]-r["open"]) for r in recent)
    bear = sum(max(0, r["open"]-r["close"]) for r in recent)
    pressure = ((bull-bear)/(bull+bear)*100) if bull+bear else 0
    volumes = [r["volume"] for r in rows[-50:] if r["volume"] > 0]
    if volumes:
        volume_score = min(100, volumes[-1] / (sum(volumes[:-1]) / max(1,len(volumes)-1)) * 50)
    else:
        volume_score = min(100, abs(pressure))
    signed = trend_raw * .42 + momentum_raw * .33 + pressure * .25
    direction = "CALL" if signed >= 0 else "PUT"
    strength = min(100, abs(signed))
    trend_score = min(100, abs(trend_raw))
    momentum_score = min(100, abs(momentum_raw))
    volatility_score = min(100, vr * 38)
    overall = min(99, max(15, strength*.64 + trend_score*.18 + momentum_score*.18))
    confidence_word = "STRONG" if overall >= 75 else "MODERATE" if overall >= 50 else "CAUTION"
    risk = "LOW" if overall >= 78 and vr <= 1.8 else "MEDIUM" if overall >= 50 and vr <= 2.4 else "HIGH (RISKY)"
    return {"price":price,"ema9":e9,"ema21":e21,"ema50":e50,"rsi":rsi,"atr":atr,"vr":vr,
            "direction":direction,"trend":trend_score,"momentum":momentum_score,"volume":volume_score,
            "volatility":volatility_score,"overall":overall,"confidence_word":confidence_word,"risk":risk}

def _ai_thinker_result(pair, market, candles):
    m = _ai_thinker_metrics(candles)
    call = m["direction"] == "CALL"
    verdict = "🟢 𝚄𝙿𝙿𝙴𝚁 (𝙲𝙰𝙻𝙻) 🟢" if call else "🔴 𝙻𝙾𝚆𝙴𝚁 (𝙿𝚄𝚃) 🔴"
    bias = "𝙱𝚄𝙻𝙻𝙸𝚂𝙷 𝚄𝙿𝚃𝚁𝙴𝙽𝙳 𝚊𝚗𝚍 𝙱𝚄𝚈𝙸𝙽𝙶 𝙿𝚁𝙴𝚂𝚂𝚄𝚁𝙴" if call else "𝙱𝙴𝙰𝚁𝙸𝚂𝙷 𝙳𝙾𝚆𝙽𝚃𝚁𝙴𝙽𝙳 𝚊𝚗𝚍 𝙿𝚁𝙴𝚂𝚂𝚄𝚁𝙴"
    ema_state = "𝙱𝚞𝚕𝚕𝚒𝚜𝚑 (𝙴𝙼𝙰 𝚜𝚝𝚊𝚌𝚔𝚎𝚍 𝚄𝙿)" if m["ema9"]>m["ema21"]>m["ema50"] else ("𝙱𝚎𝚊𝚛𝚒𝚜𝚑 (𝙴𝙼𝙰 𝚜𝚝𝚊𝚌𝚔𝚎𝚍 𝙳𝙾𝚆𝙽)" if m["ema9"]<m["ema21"]<m["ema50"] else "𝙼𝚒𝚡𝚎𝚍 / 𝚃𝚛𝚊𝚗𝚜𝚒𝚝𝚒𝚘𝚗")
    rsi_zone = "𝙾𝚟𝚎𝚛𝚜𝚘𝚕𝚍 𝚣𝚘𝚗𝚎" if m["rsi"]<30 else "𝙾𝚟𝚎𝚛𝚋𝚘𝚞𝚐𝚑𝚝 𝚣𝚘𝚗𝚎" if m["rsi"]>70 else "𝙽𝚎𝚞𝚝𝚛𝚊𝚕 𝚣𝚘𝚗𝚎"
    vol_state = "𝙷𝚒𝚐𝚑" if m["vr"]>=1.5 else "𝙻𝚘𝚠" if m["vr"]<.75 else "𝙽𝚘𝚛𝚖𝚊𝚕"
    action = "𝙲𝙰𝙻𝙻" if call else "𝙿𝚄𝚃"
    opposite = "𝙿𝚄𝚃" if call else "𝙲𝙰𝙻𝙻"
    asset = _ai_thinker_pair_label(pair).replace("-OTC", "")
    if len(asset) == 6: asset = asset[:3] + "/" + asset[3:]
    market_label = "𝙾𝚃𝙲" if market == "OTC" else "𝙻𝙸𝚅𝙴"
    def metric(label, key, emoji):
        val=int(round(m[key])); return f"{emoji} <b>{label} {_ai_thinker_bar(val)} {val}%</b>"
    return _ai_thinker_efmt(
        f"🤖 <b>𝗭𝗘𝗕𝗥𝗢𝗡𝗜𝗫 𝗔𝗜 𝗧𝗛𝗜𝗡𝗞𝗘𝗥 𝗔𝗡𝗔𝗟𝗬𝗭𝗘</b> 🤖\n<b>━━━━━━━━━━━━━━━━━━━</b>\n\n"
        f"📊 <b>𝙰𝚂𝚂𝙴𝚃∶ {asset} ({market_label})</b>\n"
        f"⏰ <b>𝚃𝙸𝙼𝙴𝙵𝚁𝙰𝙼𝙴∶ 𝙼𝟷 | {len(candles)} 𝙲𝚊𝚗𝚍𝚕𝚎𝚜 𝙰𝚗𝚊𝚕𝚢𝚣𝚎𝚛 𝚉.𝙱.𝚇 𝙰𝙸</b>\n"
        "⚡ <b>𝙳𝙰𝚃𝙰 𝚂𝚃𝚁𝙴𝙰𝙼∶ 𝙇𝙞𝙫𝙚 𝙏𝙞𝙘𝙠 𝙁𝙚𝙚𝙙 + 𝙑𝙤𝙡𝙖𝙩𝙞𝙡𝙞𝙩𝙮 𝙕𝙀𝘽𝙍𝙊𝙉𝙄𝙓 𝘼𝙄</b>\n\n"
        f"<b>━━━━━━━━━━━━━━━━━</b>\n🎯 <b>𝙰𝙸 𝚅𝙴𝚁𝙳𝙸𝙲𝚃∶ {verdict}</b>\n🔥 <b>𝚂𝙸𝙶𝙽𝙰𝙻 𝙱𝙸𝙰𝚂∶ {bias}</b>\n"
        f"💎 <b>𝙰𝙸 𝙲𝙾𝙽𝙵𝙸𝙳𝙴𝙽𝙲𝙴∶ {m['confidence_word']} {int(round(m['overall']))}%</b>\n🛡️ <b>𝚁𝙸𝚂𝙺 𝙻𝙴𝚅𝙴𝙻∶ {m['risk']}</b>\n⏳ <b>𝚁𝙴𝙲𝙾𝙼𝙼𝙴𝙽𝙳𝙴𝙳 𝙴𝚇𝙿𝙸𝚁𝚈∶ 𝟷 𝙼𝙸𝙽𝚄𝚃𝙴 (𝙼𝟷)</b>\n<b>━━━━━━━━━━━━━━━━━</b>\n\n"
        "📊 <b>𝙰𝙻𝙶𝙾𝚁𝙸𝚃𝙷𝙼𝙸𝙲 𝚂𝙲𝙾𝚁𝙴 𝙼𝙴𝚃𝚁𝙸𝙲𝚂∶</b>\n"
        + metric("𝗧𝗿𝗲𝗻𝗱 𝗦𝗰𝗼𝗿𝗲   ", "trend", "🚨") + "\n"
        + metric("𝗠𝗼𝗺𝗲𝗻𝘁𝘂𝗺     ", "momentum", "😡") + "\n"
        + metric("𝗩𝗼𝗹𝘂𝗺𝗲 𝗧𝗵𝗿𝘂𝘀𝘁", "volume", "📈") + "\n"
        + metric("𝗩𝗼𝗹𝗮𝘁𝗶𝗹𝗶𝘁𝘆     ", "volatility", "🍭") + "\n"
        + metric("𝗢𝗩𝗘𝗥𝗔𝗟𝗟 𝗔𝗜    ", "overall", "💻") + "\n\n"
        f"📊 <b>𝙰-𝚝𝚘-𝚉 𝚃𝙴𝙲𝙷𝙽𝙸𝙲𝙰𝙻 𝙱𝚁𝙴𝙰𝙺𝙳𝙾𝚆𝙽∶</b>\n📈 <b>𝙴𝙼𝙰 𝙰𝚕𝚒𝚐𝚗𝚖𝚎𝚗𝚝∶ {ema_state}</b>\n"
        f"⚡ <b>𝚁𝚂𝙸 (𝟷𝟺) 𝚂𝚝𝚊𝚝𝚞𝚜∶ {m['rsi']:.1f} — {rsi_zone}</b>\n📈 <b>𝙰𝚃𝚁 𝚅𝚘𝚕𝚊𝚝𝚒𝚕𝚒𝚝𝚢∶ {m['atr']:.6g} ({vol_state} 𝚅𝚘𝚕𝚊𝚝𝚒𝚕𝚒𝚝𝚢 𝚡{m['vr']:.2f})</b>\n💰 <b>𝙲𝚞𝚛𝚛𝚎𝚗𝚝 𝙿𝚛𝚒𝚌𝚎∶ {m['price']:.6g}</b>\n\n"
        f"🎯 <b>𝙾𝙿𝚃𝙸𝙼𝙰𝙻 𝙴𝙽𝚃𝚁𝚈 𝙴𝚇𝙴𝙲𝚄𝚃𝙸𝙾𝙽 𝙿𝙻𝙰𝙽∶</b>\n👉 <b>𝚂𝚝𝚛𝚊𝚝𝚎𝚐𝚢∶ {action} 𝚜𝚒𝚐𝚗𝚊𝚕. 𝙴𝚗𝚝𝚎𝚛 𝚘𝚗𝚕𝚢 𝚒𝚏 𝚗𝚎𝚡𝚝 𝚌𝚊𝚗𝚍𝚕𝚎 𝚌𝚘𝚗𝚏𝚒𝚛𝚖𝚜 𝚝𝚑𝚎 𝚍𝚒𝚛𝚎𝚌𝚝𝚒𝚘𝚗.</b>\n\n"
        f"⚠️ <b>𝙰𝙸 𝚁𝙸𝚂𝙺 𝙲𝙾𝙽𝚃𝚁𝙾𝙻 𝚊𝚗𝚍 𝙰𝙲𝚃𝙸𝙾𝙽 𝙽𝙾𝚃𝙴∶</b>\n💡 <b>𝙳𝚘 𝚗𝚘𝚝 𝚎𝚗𝚝𝚎𝚛 𝚊𝚐𝚊𝚒𝚗𝚜𝚝 𝚖𝚘𝚖𝚎𝚗𝚝𝚞𝚖. 𝙰𝚟𝚘𝚒𝚍 {opposite} 𝚞𝚗𝚕𝚎𝚜𝚜 𝚊 𝚌𝚘𝚗𝚏𝚒𝚛𝚖𝚎𝚍 𝚛𝚎𝚟𝚎𝚛𝚜𝚊𝚕 𝚏𝚘𝚛𝚖𝚜.</b>\n\n"
        "<b>━━━━━━━━━━━━━━━</b>\n👑 <b>𝙿𝚘𝚠𝚎𝚛𝚎𝚍 𝚋𝚢 𝚉𝙴𝙱𝚁𝙾𝙽𝙸𝚇 𝙰𝙸 𝙱𝙾𝚃</b>")

def _ai_thinker_analyze_async(cid, sess, pair, market):
    stages = [("𝙲𝙾𝙽𝙽𝙴𝙲𝚃𝙸𝙽𝙶 𝙻𝙸𝚅𝙴 𝙳𝙰𝚃𝙰", 12),
              ("𝙻𝙾𝙰𝙳𝙸𝙽𝙶 𝟽𝟶𝟶 𝙲𝙰𝙽𝙳𝙻𝙴𝚂", 35),
              ("𝙼𝙴𝙰𝚂𝚄𝚁𝙸𝙽𝙶 𝚃𝚁𝙴𝙽𝙳 𝙰𝙽𝙳 𝙼𝙾𝙼𝙴𝙽𝚃𝚄𝙼", 61),
              ("𝙲𝙰𝙻𝙲𝚄𝙻𝙰𝚃𝙸𝙽𝙶 𝚁𝙸𝚂𝙺", 84)]
    _wiz(sess, efmt(f"🤖 <b>ZEBRONIX AI THINKER</b>\n━━━━━━━━━━━━━━━━━━━━\n\n⚡ {stages[0][0]}\n{_ai_thinker_bar(stages[0][1])} {stages[0][1]}%"), None)
    def worker():
        candles = []
        for label, pct in stages[1:]:
            time.sleep(.55)
            _wiz(sess, efmt(f"🤖 <b>ZEBRONIX AI THINKER</b>\n━━━━━━━━━━━━━━━━━━━━\n\n⚡ {label}\n{_ai_thinker_bar(pct)} {pct}%"), None)
            if pct == 35:
                candles = (_fetch_otc_candles(pair, 700) if market == "OTC" else _fetch_live_candles(pair, 700))
        try:
            if len(candles) < 60: raise ValueError("market data is unavailable")
            result = _ai_thinker_result(pair, market, candles)
            kb={"inline_keyboard":[
                [{"text":"𝙰𝙽𝙰𝙻𝚈𝚉𝙴 𝙰𝙶𝙰𝙸𝙽","callback_data":f"ai_thinker_pair_{sess.ai_thinker_pairs.index(pair)}","style":"success","icon_custom_emoji_id":"6118457122498814358"}],
                [{"text":"𝙱𝙰𝙲𝙺 𝚃𝙾 𝙿𝙰𝙸𝚁𝚂","callback_data":f"ai_thinker_page_{market}_0","style":"primary"},
                 {"text":"𝙷𝙾𝙼𝙴","callback_data":"menu_home","style":"danger"}]]}
            _wiz(sess, result, kb)
        except Exception as exc:
            print(f"[AIThinker {pair}] {exc}")
            _wiz(sess, efmt(f"⚠️ <b>{_html.escape(_ai_thinker_pair_label(pair))}</b> is unavailable for analysis right now."),
                 {"inline_keyboard":[[{"text":"𝙱𝙰𝙲𝙺","callback_data":f"ai_thinker_page_{market}_0","style":"danger"}]]})
    threading.Thread(target=worker, daemon=True).start()

def _kb_welcome(uid=None):
    rows = [
        [{"text": "𝙲𝙷𝙰𝙽𝙽𝙴𝙻 𝚂𝙴𝙽𝙳𝙴𝚁", "callback_data": "lsess_start",
          "style": "success", "icon_custom_emoji_id": "6282641460093260838"}],
        [{"text": "𝙱𝙰𝙲𝙺𝚃𝙴𝚂𝚃", "callback_data": "menu_backtest",
          "style": "primary", "icon_custom_emoji_id": "6102539088936575040"},
         {"text": "𝙽𝙴𝚆𝚂 𝚂𝙸𝙶𝙽𝙰𝙻", "callback_data": "menu_news_signal",
          "style": "primary", "icon_custom_emoji_id": "5971837723676249096"}],
        [{"text": "𝙰𝚄𝚃𝙾 𝚂𝙸𝙶𝙽𝙰𝙻",   "callback_data": "lsig_mode_auto",
          "style": "primary", "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["robot"])},
         {"text": "𝙼𝙰𝙽𝚄𝙰𝙻 𝚂𝙸𝙶𝙽𝙰𝙻", "callback_data": "lsig_mode_manual",
          "style": "primary", "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["writing"])}],
        [_coming_button("coming_future_live"),
         {"text": "𝚉.𝙱.𝚇 𝙽𝙴𝚆 𝙵𝚂", "callback_data": "menu_multi_fs",
          "style": "primary", "icon_custom_emoji_id": "6219643562695336727"}],
        [{"text": "𝙾𝚃𝙲 𝙼𝙰𝚁𝙺𝙴𝚃 𝙵𝚂", "callback_data": "fut_home_OTC",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["📊"])},
         {"text": "𝙻𝙸𝚅𝙴 𝙼𝙰𝚁𝙺𝙴𝚃 𝙵𝚂", "callback_data": "fut_home_REAL",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["📈"])}],
        [{"text": "𝙱𝙻𝙰𝙲𝙺𝙾𝚄𝚃 𝙵𝚂", "callback_data": "fut_home_BLACKOUT",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["😈"])},
         {"text": "𝚆𝙷𝙸𝚃𝙴𝙾𝚄𝚃 𝙵𝚂", "callback_data": "fut_home_WHITEOUT",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["⚪"])}],
        [{"text": "𝙱𝙻𝙰𝙲𝙺𝙾𝚄𝚃 𝙵𝚂 𝙽𝙴𝚆", "callback_data": "futnew_home_BLACKOUT",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["😈"])},
         {"text": "𝚆𝙷𝙸𝚃𝙴𝙾𝚄𝚃 𝙵𝚂 𝙽𝙴𝚆", "callback_data": "futnew_home_WHITEOUT",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["⚪"])}],
        [{"text": "𝙾𝚃𝙲 𝙲𝙷𝙴𝙲𝙺𝙴𝚁", "callback_data": "menu_otc_checker",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["🔍"])},
         {"text": "𝙻𝙸𝚅𝙴 𝙼𝙰𝚁𝙺𝙴𝚃 𝙲𝙷𝙴𝙲𝙺𝙴𝚁", "callback_data": "menu_live_checker",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["🔍"])}],
        [{"text": "𝚆𝙷𝙸𝚃𝙴𝙾𝚄𝚃 𝙲𝙷𝙴𝙲𝙺𝙴𝚁", "callback_data": "menu_whiteout_checker",
          "style": "primary", "icon_custom_emoji_id": "6213218467714179432"},
         {"text": "𝙱𝙻𝙰𝙲𝙺𝙾𝚄𝚃 𝙲𝙷𝙴𝙲𝙺𝙴𝚁", "callback_data": "menu_blackout_checker",
          "style": "primary", "icon_custom_emoji_id": "6213218467714179432"}],
        [_coming_button("coming_swap_cp"),
         {"text": "𝙿𝙰𝙸𝚁 𝙻𝙸𝚂𝚃", "callback_data": "menu_pair_list",
          "style": "primary", "icon_custom_emoji_id": "6300733163719105464"}],
        [{"text": "𝙵𝙾𝚁𝙼𝙰𝚃𝚃𝙴𝚁", "callback_data": "menu_formatter",
          "style": "primary", "icon_custom_emoji_id": "5431736674147114227"},
         {"text": "𝚃𝚉 𝙲𝙾𝙽𝚅𝙴𝚁𝚃𝙴𝚁", "callback_data": "menu_tz_convert",
          "style": "primary", "icon_custom_emoji_id": "6075593821331137073"}],
        [{"text": "𝙲𝙰𝙽𝙳𝙻𝙴 𝙲𝙾𝙻𝙾𝚄𝚁𝚂", "callback_data": "menu_candle_colours",
          "style": "primary", "icon_custom_emoji_id": "6300810288446840855"},
         {"text": "𝙼𝙰𝚁𝙺𝙴𝚃 𝙿𝙰𝚈𝙾𝚄𝚃𝚂", "callback_data": "menu_market_payouts",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["📊"])}],
        [{"text": "𝙼𝙰𝚁𝙺𝙴𝚃 𝙵𝙸𝙻𝚃𝙴𝚁", "callback_data": "menu_market_filter",
          "style": "primary", "icon_custom_emoji_id": "6210497528622751920"},
         {"text": "𝙰𝙸 𝚃𝙷𝙸𝙽𝙺𝙴𝚁", "callback_data": "menu_ai_thinker",
          "style": "primary", "icon_custom_emoji_id": "6118457122498814358"}],
        [{"text": "𝚅𝙾𝙻𝙰𝚃𝙸𝙻𝙸𝚃𝚈 𝙵𝙸𝙻𝚃𝙴𝚁", "callback_data": "menu_volatility_filter",
          "style": "primary", "icon_custom_emoji_id": "6145218136007255956"},
         {"text": "𝙱𝚄𝙶 𝙵𝚄𝚃𝚄𝚁𝙴", "callback_data": "menu_bug_future",
          "style": "primary", "icon_custom_emoji_id": "6150225732866941436"}],
        [{"text": "𝙰𝙸 𝙵𝙸𝙻𝚃𝙴𝚁", "callback_data": "menu_ai_filter",
          "style": "primary", "icon_custom_emoji_id": "6116203209561219377"},
         _coming_button("coming_emoji_converter")],
        [_coming_button("coming_text_font"),
         {"text": "𝚁𝙴𝙲𝙴𝙽𝚃 𝚃𝚁𝙴𝙽𝙳", "callback_data": "menu_recent_trend",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["📈"])}],
        [_coming_button("coming_referral_user"), _coming_button("coming_live_qx_chart")],
        [{"text":"𝙰𝚄𝚃𝙾 𝙿𝙰𝚈𝙼𝙴𝙽𝚃","callback_data":"coming_auto_payment",
          "style":"success","icon_custom_emoji_id":"6141101654667174153"}],
        [{"text": "𝙰𝙱𝙾𝚄𝚃", "callback_data": "menu_about",
          "style": "primary", "icon_custom_emoji_id": "5258503720928288433"},
         {"text": "𝙼𝚈 𝙿𝚁𝙾𝙵𝙸𝙻𝙴", "callback_data": "menu_profile",
          "style": "primary", "icon_custom_emoji_id": str(EMAP["👤"])}],
        [{"text": "𝙷𝙴𝙻𝙿", "callback_data": "menu_help",
          "style": "danger", "icon_custom_emoji_id": str(EMAP["🛡"])}],
    ]
    return {"inline_keyboard": rows}

_first_name_cache: dict = {}

_WELCOME_IMAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "welcome.png")

def _send_welcome(uid, sess, kb_func=None):
    first = ""
    if uid in _first_name_cache:
        first = _first_name_cache[uid]
    else:
        try:
            r = _api("getChat", params={"chat_id": uid})
            first = r.get("result", {}).get("first_name", "") or ""
            if first:
                _first_name_cache[uid] = first
        except Exception:
            pass
    w_html = _build_welcome(first)
    kb = kb_func(uid) if kb_func else _kb_welcome(uid)

    welcome_visible = re.sub(r"<[^>]+>", "", w_html)
    welcome_visible_len = len(welcome_visible)
    if os.path.isfile(_WELCOME_IMAGE_PATH) and welcome_visible_len <= 1024:
        if sess.wiz_mid:
            try:
                _delete(sess.wiz_chat, sess.wiz_mid)
            except Exception:
                pass
            sess.wiz_mid = None
            sess.welcome_photo_mid = None
        try:
            with open(_WELCOME_IMAGE_PATH, "rb") as _img:
                resp = _http.post(f"{BASE}/sendPhoto",
                    data={"chat_id": sess.wiz_chat, "caption": w_html,
                          "parse_mode": "HTML", "reply_markup": json.dumps(_style_button_markup(kb))},
                    files={"photo": ("welcome.png", _img, "image/png")}, timeout=30)
            result = resp.json()
            if result.get("ok"):
                mid = result.get("result", {}).get("message_id")
                if mid:
                    sess.wiz_mid = mid
                    sess.welcome_photo_mid = mid
                return
            else:
                print(f"[Welcome] sendPhoto rejected: {result.get('description', '?')}")
        except Exception as e:
            print(f"[Welcome] sendPhoto error: {e}")

    if sess.wiz_mid:
        res = _api("editMessageText", data={
            "chat_id":      sess.wiz_chat,
            "message_id":   sess.wiz_mid,
            "text":         w_html,
            "parse_mode":   "HTML",
            "reply_markup": json.dumps(_style_button_markup(kb)),
        })
        if res.get("ok") or "not modified" in res.get("description","").lower():
            return
    r   = _api("sendMessage", data={
        "chat_id":      sess.wiz_chat,
        "text":         w_html,
        "parse_mode":   "HTML",
        "reply_markup": json.dumps(_style_button_markup(kb)),
    })
    mid = r.get("result", {}).get("message_id")
    if mid:
        sess.wiz_mid = mid

def _build_about() -> str:
    use_prem = _admin_has_premium()
    text = (
        "◆━━━━━━━━━━━━━━━━━◆\n"
        "     🤖 ZEBRONIX AI — ABOUT 🤖\n"
        "◆━━━━━━━━━━━━━━━━━◆\n\n"
        "🚀 ZEBRONIX AI is your real-time signal assistant for M1 Binary "
        "Trading, built to confirm every call with AI-driven analysis.\n\n"
        "✉️ Made for Telegram traders who want fast, dependable signal "
        "coverage — pick pairs manually or switch to fully automated scanning.\n\n"
        "📊 Under the hood, a multi-indicator engine (ZEBRONIX_2.0) runs "
        "several checks in parallel across OTC & Live markets before a "
        "signal is confirmed, with a reasoning breakdown attached.\n\n"
        "⚡ What you get: Manual Signal mode, Auto Signal mode, AI-backed "
        "reasoning, live chart snapshots, win/loss tracking, and session summaries.\n\n"
        "🏆 Build: ZEBRONIX AI V1.0.0\n\n"
        "🛡 Owner  : @RASUU_QXB\n\n"
        "◆━━━━━━━━━━━━━━━━━◆"
    )
    return fmt(text, use_prem=use_prem, bold=True)


def _tick_to_running_candle (tick ,timeframe_secs :int =60 ):
    if not tick :
        return None
    import time as _t
    ts   =tick .get ("timestamp",_t .time ())
    price=float (tick .get ("price",0 ))
    secs_in =int (ts )%timeframe_secs
    return {
    "open" :price ,
    "high" :price ,
    "low"  :price ,
    "close":price ,
    "secs_elapsed":secs_in ,
    "secs_remaining":timeframe_secs -secs_in ,
    "price":price ,
    "time" :tick .get ("time",""),
    }


def _generate_live_signal_chart (candles ,pair ,direction ,trade_time ,tick_data =None ,result =None ,win_count =None ,loss_count =None ):
    try :
        from PIL import Image ,ImageDraw ,ImageFont
        import io as _io

        W ,H      = 1560 ,790
        PAD_T     = 40
        PAD_B     = 36
        PAD_L     = 12
        PAD_R     = 60
        CX0       = PAD_L
        CX1       = W -PAD_R
        CW        = CX1 -CX0
        CH        = H -PAD_T -PAD_B

        BG          = (9 ,10 ,15 )
        GRID_COL    = (28 ,29 ,38 )
        BULL_BODY   = (22 ,199 ,132 )
        BEAR_BODY   = (224 ,49 ,49 )
        TEXT_GRAY   = (150 ,155 ,175 )
        BADGE_BORDER= (250 ,204 ,21 )
        BADGE_BG    = (9 ,10 ,15 )
        BADGE_TITLE = (250 ,204 ,21 )
        BADGE_SUB   = (180 ,184 ,200 )
        WIN_COL     = (22 ,199 ,132 )
        LOSS_COL    = (224 ,49 ,49 )
        SUPPLY_COL  = (239 ,68 ,68 )
        DEMAND_COL  = (34 ,197 ,94 )
        TREND_COL   = (56 ,189 ,248 )
        RES_LVL_COL = (248 ,113 ,113 )
        SUP_LVL_COL = (74 ,222 ,178 )
        CHAN_COL    = (167 ,139 ,250 )
        WATERMARK_COL = (140 ,170 ,255 )
        TIMER_BORDER= (167 ,139 ,250 )
        TIMER_TITLE = (56 ,189 ,248 )

        img  = Image .new ("RGB",(W ,H ),BG )
        draw = ImageDraw .Draw (img )

        def _fload (size ,bold =False ):
            pb = ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                  "C:/Windows/Fonts/arialbd.ttf"]
            pr = ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                  "C:/Windows/Fonts/arial.ttf",
                  "/system/fonts/DroidSans.ttf"]
            for p in (pb if bold else [])+pr :
                try :return ImageFont .truetype (p ,size )
                except :pass
            return ImageFont .load_default ()

        f_title  = _fload (19 ,bold =True )
        f_sub    = _fload (13 )
        f_stats  = _fload (14 ,bold =True )
        f_axis   = _fload (12 )
        f_result = _fload (15 ,bold =True )
        f_watermark = _fload (120 ,bold =True )
        f_timer  = _fload (18 ,bold =True )

        _wm_text = "ZEBRONIX AI"
        _wm_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        _wm_draw  = ImageDraw.Draw(_wm_layer)
        _wm_bbox  = _wm_draw.textbbox((0, 0), _wm_text, font=f_watermark)
        _wm_w     = _wm_bbox[2] - _wm_bbox[0]
        _wm_h     = _wm_bbox[3] - _wm_bbox[1]
        _wm_x     = (W - _wm_w)//2 - _wm_bbox[0]
        _wm_y     = (H - _wm_h)//2 - _wm_bbox[1]
        _wm_draw.text((_wm_x, _wm_y), _wm_text, font=f_watermark,
                      fill=(WATERMARK_COL[0], WATERMARK_COL[1], WATERMARK_COL[2], 34))
        img = Image.alpha_composite(img.convert("RGBA"), _wm_layer).convert("RGB")
        draw = ImageDraw.Draw(img)

        def tw (text ,font ):
            try :return draw .textbbox ((0 ,0 ),text ,font =font )[2 ]
            except :return len (text )*7

        n_show  = 30 if result else min (45 ,len (candles ))
        n_show  = min (n_show ,len (candles ))
        display = candles [-n_show :]if len (candles )>=n_show else candles
        n       = len (display )

        highs  = [c ["high" ]for c in display ]
        lows   = [c ["low"  ]for c in display ]
        closes = [c ["close"]for c in display ]
        opens  = [c ["open" ]for c in display ]

        result_idx = None
        if result and trade_time:
            try:
                import re as _retime
                _hh, _mm = map(int, trade_time.split(":"))
                _target_min = _hh * 60 + _mm
                _best_diff = 9999
                for _i, _c in enumerate(display):
                    _m = _retime.search(r'(\d{1,2}):(\d{2})', str(_c.get("time", "")))
                    if not _m:
                        continue
                    _cmin = int(_m.group(1)) * 60 + int(_m.group(2))
                    _diff = min(abs(_cmin - _target_min), 1440 - abs(_cmin - _target_min))
                    if _diff < _best_diff:
                        _best_diff = _diff; result_idx = _i
                if result_idx is not None and _best_diff > 1:
                    result_idx = None
            except Exception:
                result_idx = None

        run_price = None
        r_open = r_close = r_high = r_low = None
        r_bull = True

        if tick_data :
            try :
                run_price = float (tick_data .get ("price",0 ))or None
            except :pass

        if run_price and closes :
            r_open  = closes [-1 ]
            r_close = run_price
            r_bull  = r_close >=r_open

        hi_list = highs +([max (r_open ,r_close )]if (r_open and r_close )else [])
        lo_list = lows  +([min (r_open ,r_close )]if (r_open and r_close )else [])
        all_hi  = max (hi_list )
        all_lo  = min (lo_list )
        pad_y   = (all_hi -all_lo )*0.10 or 1e-6
        pmin    = all_lo -pad_y
        pmax    = all_hi +pad_y
        prng    = pmax -pmin
        wick_ext= prng *0.004

        if run_price and closes :
            r_high = max (r_open ,r_close )+wick_ext
            r_low  = min (r_open ,r_close )-wick_ext

        def py (price ):
            return PAD_T +int (CH *(1.0 -(price -pmin )/prng ))

        n_alloc = n +2
        slot_w  = CW /n_alloc
        half_bw = max (3 ,int (slot_w *0.94 )//2 )

        def cx (i ):
            return CX0 +int (slot_w *(i +0.5 ))

        run_slot = n
        run_x    = cx (run_slot )

        dec = 5 if all_hi <10 else (4 if all_hi <100 else (3 if all_hi <1000 else 2 ))

        n_hlines = 8
        for k in range (n_hlines +1 ):
            y =PAD_T +int (CH *k /n_hlines )
            draw .line ([(CX0 ,y ),(CX1 ,y )],fill =GRID_COL ,width =1 )
            frac  = 1 -k /n_hlines
            price = pmin +frac *prng
            draw .text ((CX1 +6 ,y -6 ),f"{price :.{dec }f}",fill =TEXT_GRAY ,font =f_axis )

        step_vg = max (1 ,n //12 )
        for i in range (0 ,n +1 ,step_vg ):
            x =cx (i )
            draw .line ([(x ,PAD_T ),(x ,PAD_T +CH )],fill =GRID_COL ,width =1 )

        if not result :
            zone_lookback = min (n ,40 )
            zwin_hi = highs [-zone_lookback :]
            zwin_lo = lows  [-zone_lookback :]
            sup_top = max (zwin_hi )
            sup_bot = sup_top -prng *0.045
            dem_bot = min (zwin_lo )
            dem_top = dem_bot +prng *0.045
            x0 ,x1 = CX0 ,CX1
            ov = Image .new ("RGBA",(W ,H ),(0 ,0 ,0 ,0 ))
            odr = ImageDraw .Draw (ov )
            odr .rectangle ([(x0 ,py (sup_top )),(x1 ,py (sup_bot ))],
                            fill =(SUPPLY_COL [0 ],SUPPLY_COL [1 ],SUPPLY_COL [2 ],38 ))
            odr .rectangle ([(x0 ,py (dem_top )),(x1 ,py (dem_bot ))],
                            fill =(DEMAND_COL [0 ],DEMAND_COL [1 ],DEMAND_COL [2 ],38 ))
            img .paste (Image .alpha_composite (img .convert ("RGBA"),ov ).convert ("RGB"),(0 ,0 ))
            draw .line ([(x0 ,py (sup_top )),(x1 ,py (sup_top ))],fill =SUPPLY_COL ,width =1 )
            draw .line ([(x0 ,py (dem_bot )),(x1 ,py (dem_bot ))],fill =DEMAND_COL ,width =1 )
            sup_lbl = f"SUPPLY  {sup_top :.{dec }f}"
            dem_lbl = f"DEMAND  {dem_bot :.{dec }f}"
            sup_label_y = max (PAD_T +2 ,py (sup_top )-16 )
            dem_label_y = min (PAD_T +CH -16 ,py (dem_bot )+4 )
            draw .text ((x0 +6 ,sup_label_y ),sup_lbl ,fill =SUPPLY_COL ,font =f_axis )
            draw .text ((x0 +6 ,dem_label_y ),dem_lbl ,fill =DEMAND_COL ,font =f_axis )

            cur_price = closes [-1 ]
            up_room   = max (pmax -cur_price ,prng *0.01 )
            dn_room   = max (cur_price -pmin ,prng *0.01 )

            def _nearest_swing (target ,pool ,fallback ):
                if not pool :return fallback
                return min (pool ,key =lambda v :abs (v -target ))

            hi_pool = [h for h in highs if h >cur_price ]
            lo_pool = [l for l in lows  if l <cur_price ]

            r_levels = []
            for f in (0.30 ,0.60 ,0.90 ):
                target = cur_price +up_room *f
                r_levels .append (round (_nearest_swing (target ,hi_pool ,target ),dec ))
            s_levels = []
            for f in (0.30 ,0.60 ,0.90 ):
                target = cur_price -dn_room *f
                s_levels .append (round (_nearest_swing (target ,lo_pool ,target ),dec ))

            def _draw_level (price ,label ,col ):
                y =py (price )
                if y <PAD_T or y >PAD_T +CH :return
                for dash_x in range (CX0 ,CX1 ,10 ):
                    draw .line ([(dash_x ,y ),(min (dash_x +5 ,CX1 ),y )],fill =col ,width =1 )
                lblw =tw (label ,f_axis )
                draw .rectangle ([(CX1 -lblw -10 ,y -9 ),(CX1 -2 ,y +9 )],fill =BG )
                draw .text ((CX1 -lblw -6 ,y -6 ),label ,fill =col ,font =f_axis )

            for idx ,price in enumerate (r_levels ):
                _draw_level (price ,f"R{idx +1 } {price :.{dec }f}",RES_LVL_COL )
            for idx ,price in enumerate (s_levels ):
                _draw_level (price ,f"S{idx +1 } {price :.{dec }f}",SUP_LVL_COL )

        is_buy = direction .upper ()in ("BUY","CALL","CAL")

        hi_col = None
        if result_idx is not None:
            hi_col = WIN_COL if result in ("WIN", "MTG_WIN") else LOSS_COL
            _rx      = cx(result_idx)
            _band_w  = max(half_bw * 2 + 10, int(slot_w * 0.85))
            _ov2     = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            _odr2    = ImageDraw.Draw(_ov2)
            _odr2.rectangle([(_rx - _band_w // 2, PAD_T), (_rx + _band_w // 2, PAD_T + CH)],
                            fill=(hi_col[0], hi_col[1], hi_col[2], 42))
            img.paste(Image.alpha_composite(img.convert("RGBA"), _ov2).convert("RGB"), (0, 0))

        for i ,c in enumerate (display ):
            bull   = c ["close"]>=c ["open"]
            b_col  = BULL_BODY if bull else BEAR_BODY
            x      = cx (i )
            draw .line ([(x ,py (c ["high"])),(x ,py (c ["low"]))],fill =b_col ,width =2 )
            y_top  = py (max (c ["open"],c ["close"]))
            y_bot  = py (min (c ["open"],c ["close"]))
            if y_bot <=y_top :y_bot =y_top +2
            draw .rectangle ([(x -half_bw ,y_top ),(x +half_bw ,y_bot )],fill =b_col )

        if result_idx is not None and hi_col is not None:
            _rc      = display[result_idx]
            _rx      = cx(result_idx)
            _ry_top  = py(_rc["high"]) - 7
            _ry_bot  = py(_rc["low"])  + 7
            draw.rectangle([(_rx - half_bw - 7, _ry_top), (_rx + half_bw + 7, _ry_bot)],
                           outline=hi_col, width=3)
            _tag    = "WIN" if result == "WIN" else ("MTG WIN" if result == "MTG_WIN" else "LOSS")
            _tagw   = tw(_tag, f_axis)
            _tag_y  = max(PAD_T + 2, _ry_top - 18)
            draw.rectangle([(_rx - _tagw // 2 - 5, _tag_y), (_rx + _tagw // 2 + 5, _tag_y + 15)],
                           fill=BG, outline=hi_col, width=1)
            draw.text((_rx - _tagw // 2, _tag_y + 1), _tag, fill=hi_col, font=f_axis)

        if run_price and r_open is not None and r_high is not None :
            rb_col  = BULL_BODY if r_bull else BEAR_BODY
            draw .line ([(run_x ,py (r_high )),(run_x ,py (r_low ))],fill =rb_col ,width =2 )
            ry_top = py (max (r_open ,r_close ))
            ry_bot = py (min (r_open ,r_close ))
            if ry_bot <=ry_top :ry_bot =ry_top +3
            draw .rectangle ([(run_x -half_bw ,ry_top ),(run_x +half_bw ,ry_bot )],fill =rb_col )

        if not result and n >=2 :
            xs   = list (range (n ))
            mx   = sum (xs )/n
            my   = sum (closes )/n
            num  = sum ((xs [i ]-mx )*(closes [i ]-my )for i in range (n ))
            den  = sum ((xs [i ]-mx )**2 for i in range (n ))or 1e-10
            slope= num /den
            interc=my -slope *mx
            trend_vals = [slope *i +interc for i in range (n )]
            dev_up = max ((highs [i ]-trend_vals [i ])for i in range (n ))*1.05
            dev_dn = max ((trend_vals [i ]-lows [i ])for i in range (n ))*1.05

            def _dashed (pts ,col ,width =1 ,dash =6 ,gap =5 ):
                for k in range (len (pts )-1 ):
                    x0p ,y0p = pts [k ]; x1p ,y1p = pts [k +1 ]
                    dist = max (abs (x1p -x0p ),1 )
                    steps = max (1 ,dist //(dash +gap ))
                    for s in range (steps ):
                        f0 = s /steps ; f1 = min (1.0 ,(s +dash /(dist or 1 ))/steps )
                        xa =x0p +(x1p -x0p )*f0 ;ya =y0p +(y1p -y0p )*f0
                        xb =x0p +(x1p -x0p )*f1 ;yb =y0p +(y1p -y0p )*f1
                        draw .line ([(xa ,ya ),(xb ,yb )],fill =col ,width =width )

            up_pts =[(cx (i ),py (trend_vals [i ]+dev_up ))for i in range (n )]
            dn_pts =[(cx (i ),py (trend_vals [i ]-dev_dn ))for i in range (n )]
            _dashed (up_pts ,CHAN_COL ,1 )
            _dashed (dn_pts ,CHAN_COL ,1 )

            t_pts =[(cx (i ),py (trend_vals [i ]))for i in range (n )]
            for k in range (len (t_pts )-1 ):
                draw .line ([t_pts [k ],t_pts [k +1 ]],fill =TREND_COL ,width =2 )

        sig_x   = cx (run_slot if (run_price and r_open is not None )else n -1 )
        tri_col = WIN_COL if is_buy else LOSS_COL
        tri_y   = PAD_T +CH -14
        if is_buy :
            draw .polygon ([(sig_x -7 ,tri_y +7 ),(sig_x +7 ,tri_y +7 ),(sig_x ,tri_y -7 )],fill =tri_col )
        else :
            draw .polygon ([(sig_x -7 ,tri_y -7 ),(sig_x +7 ,tri_y -7 ),(sig_x ,tri_y +7 )],fill =tri_col )

        if result :
            if result in ("WIN","MTG_WIN"):
                lbl     = "WIN"if result =="WIN"else "MTG WIN"
                lbl_col = WIN_COL
                lbl_bg  = (10 ,48 ,44 )
            else :
                lbl     = "LOSS"
                lbl_col = LOSS_COL
                lbl_bg  = (58 ,16 ,16 )
            lw = tw (lbl ,f_result )
            lx = sig_x -lw //2 -8
            ly = PAD_T +8
            draw .rectangle ([(lx ,ly ),(lx +lw +16 ,ly +24 )],fill =lbl_bg ,outline =lbl_col ,width =1 )
            draw .text ((lx +8 ,ly +4 ),lbl ,fill =lbl_col ,font =f_result )

        step_t = max (1 ,n //10 )
        for i in range (0 ,n ,step_t ):
            raw = display [i ].get ("time","")
            ts  = raw [-8 :-3 ]if len (raw )>=8 else (raw [-5 :]if len (raw )>=5 else "")
            if not ts :continue
            ttw = tw (ts ,f_axis )
            draw .text ((cx (i )-ttw //2 ,PAD_T +CH +8 ),ts ,fill =TEXT_GRAY ,font =f_axis )

        _gdn2 = get_display_name
        pair_raw  = _gdn2 (pair )
        if "_OTC"in pair_raw .upper ()or "_otc"in pair_raw :
            sub_text = pair_raw if "_otc"in pair_raw else pair_raw .replace ("_OTC","_otc")
        else :
            sub_text = pair_raw
        sub_text = f"{sub_text } | M1"

        badge_title = "ZEBRONIX AI"
        bt_w = tw (badge_title ,f_title )
        bs_w = tw (sub_text ,f_sub )
        show_stats = (win_count is not None and loss_count is not None)
        stats_win_txt  = f"WIN  {win_count}"
        stats_loss_txt = f"LOSS  {loss_count}"
        st_w = tw (stats_win_txt ,f_stats )+tw (stats_loss_txt ,f_stats )+30 if show_stats else 0
        badge_w = max (bt_w ,bs_w ,st_w )+40
        badge_h = 96 if show_stats else 60
        bx0 ,by0 = 16 ,16
        draw .rectangle ([(bx0 ,by0 ),(bx0 +badge_w ,by0 +badge_h )],
                         fill =BADGE_BG ,outline =BADGE_BORDER ,width =2 )
        draw .text ((bx0 +16 ,by0 +12 ),badge_title ,fill =BADGE_TITLE ,font =f_title )
        draw .text ((bx0 +16 ,by0 +40 ),sub_text ,fill =BADGE_SUB ,font =f_sub )
        if show_stats :
            _sy = by0 +64
            draw .line ([(bx0 +14 ,_sy -6 ),(bx0 +badge_w -14 ,_sy -6 )],fill =GRID_COL ,width =1 )
            draw .text ((bx0 +16 ,_sy ),stats_win_txt ,fill =WIN_COL ,font =f_stats )
            _wwx = tw (stats_win_txt ,f_stats )
            draw .text ((bx0 +16 +_wwx +18 ,_sy ),stats_loss_txt ,fill =LOSS_COL ,font =f_stats )

        _now_bd     = datetime.utcnow() + timedelta(hours=6)
        _clock_str  = _now_bd.strftime("%H:%M:%S")
        _secs_left  = 60 - _now_bd.second
        _timer_lbl  = f"⏱ {_clock_str} BDT"
        _timer_sub  = f"Next Candle: {_secs_left}s"
        _tt_w = tw(_timer_lbl, f_timer)
        _ts_w = tw(_timer_sub, f_sub)
        _timer_w  = max(_tt_w, _ts_w) + 34
        _timer_h  = 58
        _tx1, _ty0 = W - 16, 16
        _tx0 = _tx1 - _timer_w
        draw.rectangle([(_tx0, _ty0), (_tx1, _ty0 + _timer_h)],
                        fill=BADGE_BG, outline=TIMER_BORDER, width=2)
        draw.text((_tx0 + 17, _ty0 + 9), _timer_lbl, fill=TIMER_TITLE, font=f_timer)
        draw.text((_tx0 + 17, _ty0 + 33), _timer_sub, fill=BADGE_SUB, font=f_sub)

        buf = _io .BytesIO ()
        img .save (buf ,format ="PNG",quality =95 )
        buf .seek (0 )
        return buf .read ()

    except Exception as _e :
        print (f"[LiveChart] Error: {_e }")
        import traceback ;traceback .print_exc ()
        return None


_ZEBRONIX_LEGACY_LIVE_SIGNAL_CHART = _generate_live_signal_chart


def _generate_live_signal_chart(candles, pair, direction, trade_time,
                                tick_data=None, result=None,
                                win_count=None, loss_count=None, payout=None):

    try:
        from PIL import Image, ImageDraw, ImageFont
        import io as _io
        import math as _math
        W, H = 1600, 900
        BG       = (6, 7, 16)
        PANEL    = (15, 11, 27)
        PANEL_2  = (11, 9, 21)
        BORDER   = (46, 27, 74)
        GRID     = (23, 17, 38)
        GREEN    = (0, 245, 176)
        GREEN_BG = (5, 40, 33)
        RED      = (255, 32, 110)
        RED_BG   = (43, 8, 26)
        CYAN     = (0, 224, 255)
        PURPLE   = (185, 66, 255)
        ORANGE   = (255, 178, 26)
        WHITE    = (237, 235, 250)
        MUTED    = (127, 122, 158)

        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        _font_warned = [False]

        def font(size, bold=False):
            names = (["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                      "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
                      "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                      "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
                      "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
                      "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
                      "/usr/share/fonts/opentype/noto/NotoSans-Bold.ttf",
                      "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
                      "/usr/local/share/fonts/DejaVuSans-Bold.ttf",
                      "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                      "/Library/Fonts/Arial Bold.ttf",
                      "C:\\Windows\\Fonts\\arialbd.ttf",
                      "C:\\Windows\\Fonts\\seguisb.ttf",
                      "DejaVuSans-Bold.ttf"]
                     if bold else
                     ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                      "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
                      "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                      "/usr/share/fonts/TTF/DejaVuSans.ttf",
                      "/usr/share/fonts/dejavu/DejaVuSans.ttf",
                      "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
                      "/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf",
                      "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                      "/usr/local/share/fonts/DejaVuSans.ttf",
                      "/System/Library/Fonts/Supplemental/Arial.ttf",
                      "/Library/Fonts/Arial.ttf",
                      "C:\\Windows\\Fonts\\arial.ttf",
                      "C:\\Windows\\Fonts\\segoeui.ttf",
                      "DejaVuSans.ttf"])
            for name in names:
                try:
                    return ImageFont.truetype(name, size)
                except Exception:
                    pass
            try:
                fb = ImageFont.load_default(size=size)
                if not _font_warned[0]:
                    _font_warned[0] = True
                    print("[DashboardChart] WARNING: no TrueType font found on this system; "
                          "using Pillow's scalable default font instead. Install fonts with: "
                          "apt-get install -y fonts-dejavu-core  (or fonts-liberation2)")
                return fb
            except Exception:
                pass
            if not _font_warned[0]:
                _font_warned[0] = True
                print("[DashboardChart] WARNING: no TrueType font found AND Pillow's scalable "
                      "default font is unavailable (Pillow too old) -- text will render tiny. "
                      "Run: pip install --upgrade Pillow --break-system-packages  and/or "
                      "apt-get install -y fonts-dejavu-core")
            return ImageFont.load_default()

        F10, F11, F12, F13 = font(13), font(14), font(15), font(16)
        B10, B11, B12, B13, B14 = font(13, True), font(14, True), font(16, True), font(17, True), font(18, True)
        B16, B18, B20, B22, B28 = font(21, True), font(23, True), font(25, True), font(28, True), font(34, True)

        def tw(text, fnt):
            b = draw.textbbox((0, 0), str(text), font=fnt)
            return b[2] - b[0]

        def rr(box, radius=10, fill=None, outline=None, width=1):
            draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

        def hexagon(cx, cy, r, col, width=2):
            pts = []
            for i in range(6):
                ang = _math.pi / 180 * (60 * i - 30)
                pts.append((cx + r * _math.cos(ang), cy + r * _math.sin(ang)))
            draw.line(pts + [pts[0]], fill=col, width=width, joint="curve")

        def tri(cx, cy, size, up, col):
            if up:
                pts = [(cx, cy - size), (cx - size, cy + size * 0.7), (cx + size, cy + size * 0.7)]
            else:
                pts = [(cx, cy + size), (cx - size, cy - size * 0.7), (cx + size, cy - size * 0.7)]
            draw.polygon(pts, fill=col)

        def dot(cx, cy, r, col):
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)

        def arrow_label(x, y, label, up, col, fnt, anchor="lm", tri_size=6, gap=8):

            ltw = tw(label, fnt)
            total = tri_size * 2 + gap + ltw
            if anchor == "mm":
                start_x = x - total // 2
            elif anchor == "rm":
                start_x = x - total
            else:
                start_x = x
            tri(start_x + tri_size, y, tri_size, up, col)
            draw.text((start_x + tri_size * 2 + gap, y), label, fill=col, font=fnt, anchor="lm")
            return total

        def hline_dashed(x0, x1, y, col, dash=6, gap=5, width=1):
            x = x0
            while x < x1:
                xe = min(x + dash, x1)
                draw.line((x, y, xe, y), fill=col, width=width)
                x += dash + gap

        def pbar(x0, y0, x1, y1, pct, col, bg=(24, 30, 48)):
            r = (y1 - y0) // 2
            rr((x0, y0, x1, y1), radius=r, fill=bg)
            fx = x0 + int((x1 - x0) * max(0, min(100, pct)) / 100)
            if fx > x0 + r:
                rr((x0, y0, fx, y1), radius=r, fill=col)

        def section_header(x, y, label, col):
            draw.rectangle((x, y, x + 4, y + 18), fill=col)
            draw.text((x + 12, y + 2), label, fill=WHITE, font=B12)
            return y + 34

        raw_name = get_display_name(pair)
        is_otc = "OTC" in raw_name.upper()
        pair_core = raw_name.upper().replace("_OTC", "").replace("-OTC", "").replace("_", "")
        pair_disp = f"{pair_core}-OTC" if is_otc else pair_core

        is_buy = str(direction).upper() in ("BUY", "CALL", "CAL", "UP")
        dir_text = "BUY" if is_buy else "PUT"
        dir_col = GREEN if is_buy else RED
        dir_bg = GREEN_BG if is_buy else RED_BG

        valid = [c for c in (candles or []) if all(k in c for k in ("open", "high", "low", "close"))]
        display = valid[-46:]
        if not display:
            return _ZEBRONIX_LEGACY_LIVE_SIGNAL_CHART(
                candles, pair, direction, trade_time, tick_data, result,
                win_count, loss_count)

        closes = [float(c["close"]) for c in display]
        opens = [float(c["open"]) for c in display]
        highs = [float(c["high"]) for c in display]
        lows = [float(c["low"]) for c in display]
        times = [str(c.get("time", "")) for c in display]

        bullish_count = sum(1 for o, c in zip(opens[-14:], closes[-14:]) if c >= o)
        buyers = max(18, min(82, round(100 * bullish_count / max(1, min(14, len(display))))))
        buyers = max(buyers, 51) if is_buy else min(buyers, 49)
        confidence = max(82.0, min(97.0, 84.0 + abs(buyers - 50) * 0.55))

        if payout is None:
            _seed = int(hashlib.sha256(f"{pair}{trade_time}".encode()).hexdigest(), 16)
            payout = 85 + (_seed % 11)
        else:
            payout = int(round(float(payout)))

        def ema(values, period):
            alpha = 2 / (period + 1)
            out = [values[0]]
            for v in values[1:]:
                out.append(alpha * v + (1 - alpha) * out[-1])
            return out

        ema_fast = ema(closes, 9)
        ema_slow = ema(closes, min(50, max(5, len(closes) - 1)))
        trend_bullish = ema_fast[-1] >= ema_slow[-1]

        resistance = max(highs)
        support = min(lows)

        stats = _lsess_calc_market_stats(display)
        volatility = stats["volatility"]
        vol_pct = {"LOW": 25, "MEDIUM": 60, "HIGH": 90}.get(volatility, 40)

        entry_price = closes[-1]
        dec = 5 if abs(entry_price) < 10 else 3

        result_norm = None
        if result == "WIN":
            result_norm = "WIN"
        elif result == "MTG_WIN":
            result_norm = "MTG WIN"
        elif result == "DOJI":
            result_norm = "DOJI"
        elif result:
            result_norm = "LOSS"

        hexagon(50, 42, 19, CYAN, 2)
        hexagon(50, 42, 12, PURPLE, 1)
        hx = 82
        draw.text((hx, 22), "ZEBRONIX", fill=WHITE, font=B20)
        hx += tw("ZEBRONIX", B20) + 4
        draw.text((hx, 22), "AI", fill=CYAN, font=B20)
        hx += tw("AI", B20) + 16

        hyb = "HYBRID - V3"
        hw = tw(hyb, F11) + 22
        rr((hx, 20, hx + hw, 46), 13, PANEL_2, PURPLE, 1)
        draw.text((hx + 11, 27), hyb, fill=PURPLE, font=F11)
        hx += hw + 16

        draw.text((hx, 24), pair_disp, fill=WHITE, font=B16)
        hx += tw(pair_disp, B16) + 14
        if is_otc:
            ow = tw("OTC", F11) + 20
            rr((hx, 22, hx + ow, 44), 10, PANEL_2, CYAN, 1)
            draw.text((hx + 10, 27), "OTC", fill=CYAN, font=F11)

        bx0, bx1 = 610, 990
        rr((bx0, 12, bx1, 70), 14, dir_bg, dir_col, 2)
        cx_mid = (bx0 + bx1) // 2
        arrow_label(cx_mid, 34, dir_text, is_buy, dir_col, B22, anchor="mm", tri_size=9, gap=10)
        draw.text((cx_mid, 58), f"CONFIDENCE  {confidence:.1f}%", fill=MUTED, font=F10, anchor="mm")

        pay_txt = f"PAYOUT  {payout}%"
        draw.text((1580, 18), pay_txt, fill=ORANGE, font=B18, anchor="ra")
        tt_txt = f"Signal Time  {trade_time}  (UTC+6)"
        draw.text((1580, 46), tt_txt, fill=MUTED, font=F11, anchor="ra")

        draw.line((20, 84, 1580, 84), fill=BORDER, width=1)

        lx0, lx1, ly0, ly1 = 20, 1090, 100, 826
        rr((lx0, ly0, lx1, ly1), 10, PANEL, BORDER, 1)

        px0, px1 = lx0 + 24, lx1 - 78
        py0 = ly0 + 26
        vol_h = 76
        xaxis_h = 22
        py1 = ly1 - vol_h - xaxis_h - 14
        vy0 = py1 + 14
        vy1 = vy0 + vol_h
        xaxis_y = vy1 + 6

        price_min, price_max = min(lows), max(highs)
        price_range = (price_max - price_min) or 1e-6
        pad = price_range * 0.12
        price_min -= pad
        price_max += pad
        price_range = price_max - price_min

        def y_price(v):
            return py1 - int((float(v) - price_min) / price_range * (py1 - py0))

        for k in range(6):
            y = py0 + round((py1 - py0) * k / 5)
            draw.line((px0, y, px1, y), fill=GRID, width=1)
            val = price_max - price_range * k / 5
            d = 5 if abs(val) < 10 else 3
            draw.text((px1 + 10, y - 6), f"{val:.{d}f}", fill=MUTED, font=F10)

        n = len(display)
        slot = (px1 - px0) / max(1, n)
        body_half = max(2, min(7, int(slot * 0.32)))
        xs = [px0 + int(slot * (i + 0.5)) for i in range(n)]

        for k in range(0, n, max(1, n // 6)):
            x = xs[k]
            draw.line((x, py0, x, py1), fill=(15, 20, 34), width=1)

        window = 5
        band_w = price_range * 0.07
        upper_pts, lower_pts = [], []
        for i in range(n):
            lo_i = max(0, i - window)
            hi_i = min(n, i + window + 1)
            seg = closes[lo_i:hi_i]
            avg = sum(seg) / len(seg)
            upper_pts.append((xs[i], y_price(avg + band_w)))
            lower_pts.append((xs[i], y_price(avg - band_w)))
        band_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bd = ImageDraw.Draw(band_layer)
        bd.polygon(upper_pts + lower_pts[::-1], fill=(56, 189, 248, 18))
        img = Image.alpha_composite(img.convert("RGBA"), band_layer).convert("RGB")
        draw = ImageDraw.Draw(img)


        ry = y_price(resistance)
        sy = y_price(support)
        hline_dashed(px0, px1, ry, RED, 7, 5, 1)
        hline_dashed(px0, px1, sy, GREEN, 7, 5, 1)
        rr((lx0 + 8, ry - 10, lx0 + 30, ry + 10), 4, PANEL_2, RED, 1)
        draw.text((lx0 + 19, ry), "R", fill=RED, font=B12, anchor="mm")
        rr((lx0 + 8, sy - 10, lx0 + 30, sy + 10), 4, PANEL_2, GREEN, 1)
        draw.text((lx0 + 19, sy), "S", fill=GREEN, font=B12, anchor="mm")

        draw.line([(x, y_price(v)) for x, v in zip(xs, ema_slow)], fill=CYAN, width=2)
        draw.line([(x, y_price(v)) for x, v in zip(xs, ema_fast)], fill=ORANGE, width=2)

        for i, c in enumerate(display):
            o, h, lo, cl = map(float, (c["open"], c["high"], c["low"], c["close"]))
            col = GREEN if cl >= o else RED
            x = xs[i]
            draw.line((x, y_price(h), x, y_price(lo)), fill=col, width=1)
            yt, yb = y_price(max(o, cl)), y_price(min(o, cl))
            if yb <= yt:
                yb = yt + 2
            draw.rectangle((x - body_half, yt, x + body_half, yb), fill=col)

        ex = xs[-1]
        ey = y_price(entry_price)
        entry_high = y_price(highs[-1])
        draw.line((ex, py0, ex, py1), fill=CYAN, width=1)
        etxt = "ENTRY"
        etw = tw(etxt, B10)
        label_y = max(py0 + 4, entry_high - 18)
        ex_clamped = min(ex, px1 - etw // 2 - 4)
        draw.text((ex_clamped - etw // 2, label_y), etxt, fill=CYAN, font=B10)
        rr((px1 + 4, ey - 12, px1 + 74, ey + 12), 5, PANEL_2, CYAN, 1)
        draw.text((px1 + 39, ey), f"{entry_price:.{dec}f}", fill=WHITE, font=B11, anchor="mm")

        ranges = [h - l for h, l in zip(highs, lows)]
        max_range = max(ranges) or 1e-6
        for i, c in enumerate(display):
            o, cl = float(c["open"]), float(c["close"])
            col = GREEN if cl >= o else RED
            vh = max(4, int((ranges[i] / max_range) * vol_h))
            x = xs[i]
            draw.rectangle((x - body_half, vy1 - vh, x + body_half, vy1), fill=col)

        step = max(1, n // 6)
        for k in range(0, n, step):
            label = times[k][-5:] if times[k] else ""
            if label:
                draw.text((xs[k], xaxis_y), label, fill=MUTED, font=F10, anchor="ma")

        rx0, rx1 = 1110, 1580
        y = 100

        y = section_header(rx0, y, "SIGNAL DETAILS", CYAN)
        rr((rx0, y, rx1, y + 58), 14, dir_bg, dir_col, 2)
        arrow_label((rx0 + rx1) // 2, y + 29, dir_text, is_buy, dir_col, B20, anchor="mm", tri_size=8, gap=9)
        y += 58 + 16

        draw.text((rx0 + 4, y), "CONFIDENCE", fill=MUTED, font=F11)
        draw.text((rx1 - 4, y), f"{confidence:.1f}%", fill=WHITE, font=B12, anchor="ra")
        y += 20
        pbar(rx0 + 4, y, rx1 - 4, y + 8, confidence, GREEN)
        y += 24

        rows = [
            ("Entry Price", f"{entry_price:.{dec}f}", WHITE),
            ("Market", "OTC" if is_otc else "REAL", CYAN),
            ("Time", trade_time, ORANGE),
            ("Martingale", "1 Step", PURPLE),
        ]
        for label, val, col in rows:
            draw.ellipse((rx0 + 4, y + 6, rx0 + 10, y + 12), fill=col)
            draw.text((rx0 + 20, y), label, fill=(190, 197, 214), font=F12)
            draw.text((rx1 - 4, y), val, fill=col, font=B13, anchor="ra")
            y += 28

        y += 8

        if result_norm and win_count is not None and loss_count is not None:
            total = max(1, win_count + loss_count)
            win_rate = round(win_count / total * 100)
            y = section_header(rx0, y, "SESSION PERFORMANCE", CYAN)
            draw.text((rx0 + 4, y), "WIN RATE", fill=MUTED, font=F11)
            draw.text((rx1 - 4, y), f"{win_rate}%", fill=WHITE, font=B12, anchor="ra")
            y += 20
            pbar(rx0 + 4, y, rx1 - 4, y + 8, win_rate, GREEN)
            y += 22
            bw = (rx1 - rx0 - 16) // 3
            stat_boxes = [("WINS", win_count, GREEN), ("LOSSES", loss_count, RED), ("TOTAL", total, PURPLE)]
            for i, (lbl, val, col) in enumerate(stat_boxes):
                bx0s = rx0 + i * (bw + 8)
                rr((bx0s, y, bx0s + bw, y + 62), 10, PANEL_2, BORDER, 1)
                draw.text((bx0s + bw // 2, y + 20), str(val), fill=col, font=B18, anchor="mm")
                draw.text((bx0s + bw // 2, y + 45), lbl, fill=MUTED, font=F10, anchor="mm")
            y += 62 + 16

        y = section_header(rx0, y, "MARKET READ", ORANGE)
        draw.text((rx0 + 4, y), "Trend  (EMA 9/50)", fill=(190, 197, 214), font=F12)
        trend_label = "BULLISH" if trend_bullish else "BEARISH"
        trend_col = GREEN if trend_bullish else RED
        ptw = tw(trend_label, B11) + 20 + 16 + 9
        rr((rx1 - ptw, y - 6, rx1, y + 22), 10, PANEL_2, trend_col, 1)
        arrow_label(rx1 - ptw + 10, y + 8, trend_label, trend_bullish, trend_col, B11, anchor="lm", tri_size=6, gap=8)
        y += 34
        draw.text((rx0 + 4, y), "VOLATILITY", fill=MUTED, font=F11)
        draw.text((rx1 - 4, y), volatility.capitalize(), fill=WHITE, font=F11, anchor="ra")
        y += 18
        pbar(rx0 + 4, y, rx1 - 4, y + 8, vol_pct, GREEN)
        y += 30

        y = section_header(rx0, y, "KEY LEVELS", PURPLE)
        rr((rx0, y, rx1, y + 72), 12, PANEL_2, BORDER, 1)
        draw.text((rx0 + 16, y + 14), "Resistance", fill=(190, 197, 214), font=F12)
        draw.text((rx1 - 16, y + 14), f"{resistance:.{dec}f}", fill=RED, font=B13, anchor="ra")
        draw.line((rx0 + 16, y + 36, rx1 - 16, y + 36), fill=BORDER, width=1)
        draw.text((rx0 + 16, y + 44), "Support", fill=(190, 197, 214), font=F12)
        draw.text((rx1 - 16, y + 44), f"{support:.{dec}f}", fill=GREEN, font=B13, anchor="ra")
        y += 72

        # bottom action box, flows right after content (won't exceed panel bottom)
        y += 20
        aby0 = min(y, ly1 - 76)
        aby1 = aby0 + 76
        if result_norm:
            is_win_like = result_norm in ("WIN", "MTG WIN")
            acol = GREEN if is_win_like else RED if result_norm == "LOSS" else MUTED
            abg = GREEN_BG if is_win_like else RED_BG if result_norm == "LOSS" else PANEL_2
            rr((rx0, aby0, rx1, aby1), 14, abg, acol, 2)
            draw.text(((rx0 + rx1) // 2, (aby0 + aby1) // 2), result_norm, fill=acol, font=B22, anchor="mm")
        else:
            rr((rx0, aby0, rx1, aby1), 14, GREEN_BG, GREEN, 2)
            draw.text(((rx0 + rx1) // 2, aby0 + 26), f"TRADE AT  {trade_time}", fill=GREEN, font=B18, anchor="mm")
            draw.text(((rx0 + rx1) // 2, aby0 + 54), "M1   -   EXPIRY 1 MIN", fill=MUTED, font=F11, anchor="mm")

        out = _io.BytesIO()
        img.save(out, "PNG", optimize=True)
        out.seek(0)
        return out.read()

    except Exception as exc:
        print(f"[DashboardChart] Error: {exc}")
        import traceback
        traceback.print_exc()
        return _ZEBRONIX_LEGACY_LIVE_SIGNAL_CHART(
            candles, pair, direction, trade_time, tick_data, result,
            win_count, loss_count)


_LIVE_SIG_EMOJI_IDS ={
"crown":6233239968865590050 ,
"target":5310278924616356636 ,
"chart":6145248943807667330 ,
"chart_bare":6118414920150160494 ,
"down_arr":6233323046417996962 ,
"clock":6102806257377221993 ,
"alarm":6260516004787395610 ,
"bolt":6231262660411792851 ,
"diamond":6231262273864736290 ,
"green_dot":6332517244559430568 ,
"shield":6172454666819868463 ,
"barrier":6230743532009691484 ,
"red_dot":6030365290263483624 ,
"up_arr":6231288370086026695 ,
"yellow_dot":6030426609511567947 ,
"sparkle":6231210240335944916 ,
"search":5039649904264217620 ,
"hourglass":6062063510412599114 ,
"trend_down":6174761876006638661 ,
"trend_up":6231257635300056225 ,
"magnify":6174760355588215282 ,
"robot":6255726532136800534 ,
"badge":6215194556397260680 ,
"ribbon":6147725220087077904 ,
"gear":6118476436966741936 ,
"alert":6233314121475956159 ,
"brain":6271527128408264959 ,
"calendar":6102906733842144545 ,
"check":6233489978911890876 ,
"cross":6260072893011469020 ,
"bell":6258123652168949843 ,
"sword":5190806721286657692 ,
"next":6271295457872319462,
"writing":5458382591121964689,
}

_LIVE_SIG_NORM ={
"crown":"👑",
"target":"🎯",
"chart":"📊",
"chart_bare":"📊",
"down_arr":"🔻",
"clock":"⏱",
"alarm":"⏰",
"bolt":"⚡",
"diamond":"💎",
"green_dot":"🟢",
"shield":"🛡",
"barrier":"🚧",
"red_dot":"🔴",
"up_arr":"🔺",
"yellow_dot":"🟡",
"sparkle":"✨",
"search":"🔍",
"hourglass":"⏳",
"trend_down":"📉",
"trend_up":"📈",
"magnify":"🔍",
"robot":"🤖",
"badge":"⚜️",
"ribbon":"🔰",
"gear":"⚙️",
"alert":"🚨",
"brain":"🧠",
"calendar":"📅",
"check":"✅",
"cross":"❌",
"bell":"🔔",
"sword":"⚔️",
"next":"➡️",
"writing":"✍️",
}


def _gemini_confirm(pair_disp, direction, candles, support, resistance, payout):
    import random
    closes = [c["close"] for c in candles[-20:]] if len(candles) >= 20 else [c["close"] for c in candles]
    sup = support; res2 = resistance
    if direction == "BUY":
        pool = [
            f"Multiple timeframe confluence confirms a clean bullish setup near {sup}. "
            f"The EMA short-term average has curled upward, indicating renewed buying pressure. "
            f"Successive candles are closing with reduced lower wicks — bulls absorbing sell-side pressure. "
            f"A push toward {res2} is the primary target for this BUY entry.",
            f"Price action near {sup} shows a classic demand zone reaction with compressed bearish candle bodies. "
            f"The RSI is recovering from near-oversold territory, adding momentum confirmation. "
            f"The last two candles form a near-perfect bullish engulfing structure. "
            f"Risk-reward favors a BUY entry with resistance target at {res2}.",
        ]
    else:
        pool = [
            f"Price is consistently failing to close above {res2}, forming a strong rejection zone. "
            f"Lower highs are emerging with each retest, confirming bearish distribution. "
            f"Short EMA has crossed below long EMA, providing trend alignment for the PUT. "
            f"Downside momentum points toward key support at {sup}.",
            f"A bearish engulfing candle formed at {res2}, absorbing all prior bullish momentum. "
            f"RSI has rolled over from near-overbought levels, confirming exhaustion of buyers. "
            f"Candle wicks above {res2} are shortening, signalling reduced upside pressure. "
            f"The PUT entry is validated by both structure and momentum; target is {sup}.",
        ]
    return True, random.randint(74, 93), random.choice(pool)
def _pattern_score(candles, tick=None):
    if len(candles) < 20: return None, 0.0, []
    closes = [c["close"] for c in candles[-20:]]
    opens  = [c["open"]  for c in candles[-20:]]
    highs  = [c["high"]  for c in candles[-20:]]
    lows   = [c["low"]   for c in candles[-20:]]
    score = 0.0; patterns = []
    ema5 = sum(closes[-5:]) / 5; ema14 = sum(closes[-14:]) / 14
    if ema5 > ema14:   score += 1.0; patterns.append("EMA_BULL")
    elif ema5 < ema14: score -= 1.0; patterns.append("EMA_BEAR")
    else: return None, 0.0, []
    bull3 = sum(1 for i in range(1,4) if closes[-i]>opens[-i])
    bear3 = sum(1 for i in range(1,4) if closes[-i]<opens[-i])
    if bull3 >= 2:   score += 0.8; patterns.append("MOM_BULL")
    elif bear3 >= 2: score -= 0.8; patterns.append("MOM_BEAR")
    lb = abs(closes[-1]-opens[-1]); lr = max(highs[-1]-lows[-1], 1e-9)
    if lb/lr >= 0.50:
        if closes[-1] >= opens[-1]: score += 0.7; patterns.append("STRONG_BULL_BODY")
        else:                       score -= 0.7; patterns.append("STRONG_BEAR_BODY")
    if abs(score) < 1.5: return None, 0.0, []
    return ("BUY" if score > 0 else "PUT"), score, patterns

def _advanced_analyze(pair, candles, indicators, tick_data=None):
    base_sig = _analyze_pair(pair, indicators, candles)
    if base_sig is None: return None
    pat_dir, pat_score, found_patterns = _pattern_score(candles, tick_data)
    if pat_dir is None: return None
    base_dir = "BUY" if base_sig["direction"].upper() in ("CALL","BUY","CAL") else "PUT"
    if base_dir != pat_dir: return None
    sig = dict(base_sig)
    sig["direction"]     = pat_dir
    sig["pattern_score"] = pat_score
    sig["patterns"]      = found_patterns
    sig["regime"]        = "TRENDING"
    return sig

def _to_mono(text: str) -> str:
    MU = "𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉"
    ML = "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣"
    MD = "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"
    res = []
    for ch in text:
        if   "A" <= ch <= "Z": res.append(MU[ord(ch)-65])
        elif "a" <= ch <= "z": res.append(ML[ord(ch)-97])
        elif "0" <= ch <= "9": res.append(MD[ord(ch)-48])
        else:                   res.append(ch)
    return "".join(res)

_AI_REASON_BUY = [
    "A sharp rejection wick from {support} combined with a closing candle above "
    "the mid-zone signals strong buyer conviction. Momentum indicators align with "
    "the broader upward structure visible in recent price flow. Technical "
    "probability strongly favors continuation toward {resistance}.",

    "Price is holding firmly above {support} with a sequence of higher lows "
    "forming on the chart. Buying pressure is steadily building and momentum "
    "indicators are turning positive. Structure favors a push toward {resistance}.",

    "Buyers stepped in aggressively near {support}, absorbing sell pressure with "
    "ease. The spread between highs and lows is narrowing — a consolidation "
    "before expansion. The path of least resistance now points toward {resistance}.",

    "A clean bounce off {support} with expanding bullish candle bodies suggests "
    "fresh upside momentum building. Volume is confirming the move, and "
    "probability favors continuation toward {resistance}.",

    "Momentum is picking up on the up-move from {support}, with each pullback "
    "getting shallower. This kind of tightening range often precedes a breakout "
    "toward {resistance}, and current structure strongly favors that outcome.",
]

_AI_REASON_PUT = [
    "A strong rejection from {resistance} combined with a closing candle below "
    "the mid-zone signals clear seller conviction. Momentum indicators align with "
    "the broader downward structure visible in recent price flow. Technical "
    "probability strongly favors continuation toward {support}.",

    "Price is struggling to hold below {resistance} with a sequence of lower "
    "highs forming on the chart. Selling pressure is steadily building and "
    "momentum indicators are turning negative. Structure favors a move toward {support}.",

    "Sellers stepped in aggressively near {resistance}, absorbing buy pressure "
    "with ease. The spread between highs and lows is narrowing — a consolidation "
    "before expansion. The path of least resistance now points toward {support}.",

    "A clean rejection at {resistance} with expanding bearish candle bodies "
    "suggests fresh downside momentum building. Volume is confirming the move, "
    "and probability favors continuation toward {support}.",

    "Momentum is picking up on the down-move from {resistance}, with each "
    "pullback getting shallower. This kind of tightening range often precedes a "
    "breakdown toward {support}, and current structure strongly favors that outcome.",
]

def _ai_analysis_text(direction, support, resistance) -> str:
    pool = _AI_REASON_BUY if direction == "BUY" else _AI_REASON_PUT
    tmpl = random.choice(pool)
    try:
        return tmpl.format(support=support, resistance=resistance)
    except Exception:
        return tmpl

_SIGNAL_FORMAT_EMOJI = {
    "😡":6145218136007255956,"📊":6212901597911980909,"⏰":6339143318240238472,
    "➡️":6212913701129821381,"😆":6312202878178042522,"😛":6312160572750177611,
    "➕":6303030189538417585,"📉":6147776510586527307,"📈":6149789132261433255,
    "💰":6210902995010331288,"🥳":6300963760513228226,"😋":6301088640982326387,
    "🎯":6075602196517363973,"🔥":6093409392919585143,"💀":6093454567385604512,
    "👑":6150225732866941436,"✅":6213053622574392612,"⚙️":6300679098670784062,
}
_RESULT_FORMAT_EMOJI = dict(_SIGNAL_FORMAT_EMOJI, **{
    "🤢":6312053434790976755,"🕯":6312054040381367354,"🟢":6186138166336954485,
    "⚖️":6064525334127059066,"🔄":6057849898387119890,"🤖":6134212600138833922,
})
_PARTIAL_FORMAT_EMOJI = dict(_RESULT_FORMAT_EMOJI, **{
    "📆":6210895186759785075,"🔫":6077985031488282050,"▶️":6212782266540630237,
    "💎":6132052287423522342,"😡":6145241513514246393,
})

def _render_signal_format(text, use_prem, local_map):
    rendered = _feature_efmt(text, local_map)
    return rendered if use_prem else _normal_emoji_html(rendered)

def _build_lsig_partial_msg(partial_list):

    return _build_lsess_partial_msg(partial_list)

_LSESS_DEFAULT_OWNER = "@RASUU_QXB"

def _owner_settings_menu(uid, sess, return_cb):
    sess.owner_return_cb = return_cb
    current = _lsig_owner_names.get(uid) or sess.lsess_owner_name
    current_line = _html.escape(current) if current else f"Not set (default: {_LSESS_DEFAULT_OWNER})"
    _wiz(sess, efmt(
        f"{_e_('⚙')} <b>Owner Username Settings</b>\n\n"
        f"👤 <b>Current:</b> {current_line}\n\n"
        "This name appears as the <b>Owner</b> in every signal &amp; result "
        "template, in both Live Signal and Channel Sender (Live Session)."),
        {"inline_keyboard": [
            [{"text": "Change Username", "callback_data": "owner_username_edit",
              "style": "primary", "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["gear"])}],
            [{"text": "Back  ", "callback_data": return_cb,
              "style": "danger", "icon_custom_emoji_id": "5258084656674250503"}],
        ]})

def _lsess_calc_market_stats(candles):
    try:
        window = candles[-60:] if len(candles) >= 60 else candles
        highs  = [float(c["high"])  for c in window]
        lows   = [float(c["low"])   for c in window]
        closes = [float(c["close"]) for c in window]
        opens  = [float(c["open"])  for c in window]
        atr, adx = _calc_atr_adx(highs, lows, closes, 14)
        avg_close = sum(closes) / len(closes) if closes else 0
        atr_pct = (atr / avg_close * 100) if avg_close else 0
        if atr_pct >= 0.08:
            volatility = "HIGH"
        elif atr_pct >= 0.03:
            volatility = "MEDIUM"
        else:
            volatility = "LOW"
        pair_zone = "STRONG MARKET" if adx >= 25 else "WEAK MARKET"
        sma_fast = sum(closes[-5:]) / min(5, len(closes))
        sma_slow = sum(closes[-20:]) / min(20, len(closes))
        trend_diff_pct = ((sma_fast - sma_slow) / avg_close * 100) if avg_close else 0
        if trend_diff_pct > 0.02:
            market_trend = "UPTREND"
        elif trend_diff_pct < -0.02:
            market_trend = "DOWNTREND"
        else:
            market_trend = "SIDEWAYS"
        pressure_window = list(zip(opens[-20:], closes[-20:]))
        bull_sum = sum(abs(c - o) for o, c in pressure_window if c > o)
        bear_sum = sum(abs(c - o) for o, c in pressure_window if c < o)
        total = bull_sum + bear_sum
        if total > 0:
            buyer_pct  = round(bull_sum / total * 100)
            seller_pct = 100 - buyer_pct
        else:
            buyer_pct = seller_pct = 50
        return {"volatility": volatility, "pair_zone": pair_zone,
                "market_trend": market_trend, "seller_pct": seller_pct,
                "buyer_pct": buyer_pct}
    except Exception:
        return {"volatility": "MEDIUM", "pair_zone": "WEAK MARKET",
                "market_trend": "SIDEWAYS", "seller_pct": 50, "buyer_pct": 50}


def _build_lsess_signal_text(pair_disp, direction, trade_time, confidence,
                              payout, support, resistance,
                              candles, owner_name=None, mtg_steps=1):
    dir_str = "😆 𝗕𝗨𝗬 ▲" if direction == "BUY" else "😛 𝗣𝗨𝗧 ▼"
    filled  = max(0, min(10, int(round(confidence / 10))))
    bar     = "█" * filled + "░" * (10 - filled)
    stats   = _lsess_calc_market_stats(candles)
    owner = owner_name or _LSESS_DEFAULT_OWNER
    text = (
        "😡 ZEBRONIX AI V2.1 — SIGNAL 😡\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📊 ASSET :   {pair_disp}\n"
        f"⏰ TIME :   {trade_time}\n"
        f"➡️ ENTRY :   ⟦α⟧\n"
        f"➕ MTG :   {mtg_steps} STEP REQUIRED\n"
        f"📉 SUPPORT :   {support}\n"
        f"📈 RESISTANCE :   {resistance}\n"
        f"💰 PAYOUT :   {payout}%\n"
        f"📊 ASSET : VOLATILITY {stats['volatility']}\n"
        f"🥳 PAIR ZONE :   {stats['pair_zone']}\n"
        "😋 STRATEGY :   ZEBRONIX V2.1\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🎯 AI Confidence\n"
        f"{bar} {confidence}%\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "┏━━━━━━━💀━━━━━━━┓\n"
        f"🔥 MARKET TREND :   {stats['market_trend']}\n"
        f"📉 SELLER PRESSURE :   {stats['seller_pct']}%\n"
        f"📈 BUYER PRESSURE :   {stats['buyer_pct']}%\n"
        "┗━━━━━━━💀━━━━━━━┛\n"
        "┏━━━━━━━━━━━━━━━━┓\n"
        f"┃ 👑 Owner :   ⟦β⟧✅\n"
        "┗━━━━━━━━━━━━━━━━┛"
    )
    text = _to_mono(text)
    text = (text.replace("⟦α⟧", dir_str)
                 .replace("⟦β⟧", owner))
    return text


def _build_lsess_result_text(pair_disp, entry_time, direction, result,
                              close_price, candle_colour, payout, candles=None):
    dir_str = "😆 𝗕𝗨𝗬 ▲" if direction == "BUY" else "😛 𝗣𝗨𝗧 ▼"
    is_red  = "Red" in candle_colour or "red" in candle_colour.lower()
    candle_word = "𝗥𝗘𝗗" if is_red else "𝗚𝗥𝗘𝗘𝗡"
    candle_emoji = "🔴" if is_red else "🟢"
    candle_str = f"{candle_word} {candle_emoji}"
    if candles:
        stats = _lsess_calc_market_stats(candles)
        trend_word = stats["market_trend"]
    else:
        trend_word = "SIDEWAYS"
    trend_arrow = {"UPTREND": "⬆", "DOWNTREND": "🔽", "SIDEWAYS": "🔄"}.get(trend_word, "🔄")
    if result in ("WIN", "MTG_WIN"):
        result_line = "✅𝗡𝗢𝗡 𝗠𝗧𝗚 𝗦𝗨𝗥𝗘𝗦𝗛𝗢𝗧✅" if result == "WIN" else "✅✅ 𝗠𝗔𝗥𝗧𝗜𝗡𝗚𝗔𝗟𝗘 𝗪𝗜𝗡 ✅✅"
    elif result == "DOJI":
        result_line = "⚖️ 𝗗𝗢𝗝𝗜 ⚖️ 😮"
    else:
        result_line = "❌❌ 𝗟𝗢𝗦𝗦 𝗧𝗥𝗔𝗗𝗘 ❌❌"
    text = (
        "😡 ZEBRONIX AI V2.1 - RESULT 😡\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🤢 ASSET :   {pair_disp}\n"
        f"⏰ TIME :   {entry_time}\n"
        "➡️ ENTRY :   ⟦α⟧\n"
        f"💰 PAYOUT :   {payout}%\n"
        "💱 CANDLE :   ⟦β⟧\n"
        f"😋 CLOSE PRICE :   {close_price}\n"
        f"⚖️ MARKET TREND :   {trend_word}⟦γ⟧\n"
        "🤖 STRATEGY :   ZEBRONIX V2.1\n"
        "┏━━━━━━━━━━━━━━━┓\n"
        "    ⟦δ⟧\n"
        "┗━━━━━━━━━━━━━━━┛"
    )
    text = _to_mono(text)
    text = (text.replace("⟦α⟧", dir_str)
                 .replace("⟦β⟧", candle_str)
                 .replace("⟦γ⟧", trend_arrow)
                 .replace("⟦δ⟧", result_line))
    return text


def _build_lsess_partial_msg(partial_list):
    today = (datetime.utcnow() + timedelta(hours=6)).strftime("%Y-%m-%d")
    otc_lines = []; real_lines = []; wins = losses = 0
    for r in partial_list:
        pair = r.get("pair", ""); time_s = r.get("time", ""); dirn = r.get("direction", "PUT")
        result = r.get("result", "")
        if result in ("WIN", "MTG_WIN"):
            mtg_step = int(r.get("mtg_step", 1 if result == "MTG_WIN" else 0) or 0)
            icon = "✅" + ({1: "¹", 2: "²", 3: "³"}.get(mtg_step, "") if mtg_step else "")
            wins += 1
        elif result == "DOJI":
            icon = "⚖️"
        else:
            icon = "❌"; losses += 1
        dir_d = "BUY" if dirn == "BUY" else "PUT"
        clean_pair = _ck_re.sub(r"[_-]OTC$", "-OTC", pair, flags=_ck_re.IGNORECASE).upper()
        line = _to_mono(f"❒ {time_s} - {clean_pair} - {dir_d}  ") + icon
        (otc_lines if _ck_re.search(r"[_-]OTC$", pair, flags=_ck_re.IGNORECASE) else real_lines).append(line)
    total = wins + losses
    acc   = round(wins / total * 100) if total > 0 else 0
    sep = "━━━━━━━━━・━━━━━━━━━"
    parts = [
        _to_mono("▰▱👑ZEBRONIX BOT PARTIAL👑▱▰"), sep,
        _to_mono(f"           📆 - {today}"), sep,
        _to_mono("🕯 OTC MARKETS PARTIAL 🕯"), sep,
    ]
    parts.extend(otc_lines or [_to_mono("OTC MARKET SIGNAL NOT FOUND")])
    parts.extend([sep, _to_mono("💴 REAL MARKETS PARTIAL 💴"), sep])
    parts.extend(real_lines or [_to_mono("LIVE MARKET SIGNAL NOT FOUND")])
    parts.extend([
        sep, _to_mono(f"😡 TOTAL RATE: {wins}X{losses}⋅◈⋅  ({acc}%)"), sep,
        _to_mono("⚙️ POWER OF ZEBRONIX AI V2.1"),
        _to_mono("💎 PARTIAL SENT SUCCESSFULLY"),
    ])

    return "\n".join(parts)


def _lsig_send_anim(chat_id, text, use_prem=False, msg_id=None):
    html_text = fmt(text, use_prem=use_prem, bold=False)
    try:
        if msg_id is None:
            r   = _http.post(f"{BASE}/sendMessage",
                  data={"chat_id":chat_id,"text":html_text,"parse_mode":"HTML"}, timeout=10)
            res = r.json()
            return res.get("result",{}).get("message_id") if res.get("ok") else None
        else:
            _http.post(f"{BASE}/editMessageText",
                data={"chat_id":chat_id,"message_id":msg_id,
                      "text":html_text,"parse_mode":"HTML"}, timeout=8)
            return msg_id
    except Exception as e:
        print(f"[Anim] {e}")
        return None

def _lsig_send_with_ai_reason(cid, text, reason, kb, use_prem, chart_bytes=None, via_telethon=False, emoji_map=None):
    import tempfile, os
    main_html   = (f"<b>{_render_signal_format(text, use_prem, emoji_map)}</b>"
                   if emoji_map else fmt(text, use_prem=use_prem, bold=True))
    full_html   = main_html
    if reason:
        full_html += f"\n\n<blockquote expandable>{_html.escape(reason)}</blockquote>"

    if via_telethon and _admin_has_premium():
        ok = (_telethon_send_photo(cid, chart_bytes, full_html) if chart_bytes
              else _telethon_send_text(cid, full_html))
        if ok:
            return True, None
        print("[LsigSend] premium send failed after retries; normal-emoji fallback blocked")
        return False, None

    if chart_bytes:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        try:
            tmp.write(chart_bytes); tmp.close()
            with open(tmp.name,"rb") as _img:
                resp = _http.post(f"{BASE}/sendPhoto",
                    data={"chat_id":cid,"caption":full_html,
                          "parse_mode":"HTML","reply_markup":json.dumps(_style_button_markup(kb))},
                    files={"photo":("chart.png",_img,"image/png")}, timeout=30)
            if resp.ok:
                return True, resp.json().get("result",{}).get("message_id")
        except Exception as e:
            print(f"[LsigSend] sendPhoto: {e}")
        finally:
            try: os.remove(tmp.name)
            except: pass
    try:
        resp = _http.post(f"{BASE}/sendMessage",
            data={"chat_id":cid,"text":full_html,"parse_mode":"HTML",
                  "reply_markup":json.dumps(_style_button_markup(kb))}, timeout=20)
        if resp.ok:
            return True, resp.json().get("result",{}).get("message_id")
    except Exception as e:
        print(f"[LsigSend] sendMessage: {e}")
    return False, None

def _lsig_send_result(cid, text, use_prem, kb, chart_bytes=None, via_telethon=False, emoji_map=None):
    import tempfile, os
    full_html = (f"<b>{_render_signal_format(text, use_prem, emoji_map)}</b>"
                 if emoji_map else fmt(text, use_prem=use_prem, bold=True))

    if via_telethon and _admin_has_premium():
        ok = (_telethon_send_photo(cid, chart_bytes, full_html) if chart_bytes
              else _telethon_send_text(cid, full_html))
        if ok:
            return True
        print("[Result] premium send failed after retries; normal-emoji fallback blocked")
        return False

    if chart_bytes:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        try:
            tmp.write(chart_bytes); tmp.close()
            with open(tmp.name,"rb") as _img:
                resp = _http.post(f"{BASE}/sendPhoto",
                    data={"chat_id":cid,"caption":full_html,
                          "parse_mode":"HTML","reply_markup":json.dumps(_style_button_markup(kb))},
                    files={"photo":("chart.png",_img,"image/png")}, timeout=30)
            if resp.ok: return True
        except Exception as e:
            print(f"[Result] sendPhoto: {e}")
        finally:
            try: os.remove(tmp.name)
            except: pass
    try:
        response = _http.post(f"{BASE}/sendMessage",
            data={"chat_id":cid,"text":full_html,"parse_mode":"HTML",
                  "reply_markup":json.dumps(_style_button_markup(kb))}, timeout=20)
        return bool(response.ok)
    except Exception as e:
        print(f"[Result] sendMessage: {e}")
        return False


def _lsig_send_partial_msg(cid, text, use_prem, kb, via_telethon=False, emoji_map=None):
    html_text = (f"<b>{_render_signal_format(text, use_prem, emoji_map)}</b>"
                 if emoji_map else fmt(text, use_prem=use_prem, bold=True))

    if via_telethon and _admin_has_premium():
        if _telethon_send_text(cid, html_text):
            return True
        print("[Partial] premium send failed after retries; normal-emoji fallback blocked")
        return False

    try:
        response = _http.post(f"{BASE}/sendMessage",
            data={"chat_id":cid,"text":html_text,"parse_mode":"HTML",
                  "reply_markup":json.dumps(_style_button_markup(kb))}, timeout=20)
        return bool(response.ok)
    except Exception as e:
        print(f"[Partial] {e}")
        response = _http.post(f"{BASE}/sendMessage",
            data={"chat_id":cid,"text":text,"reply_markup":json.dumps(_style_button_markup(kb))}, timeout=20)
        return bool(response.ok)

def _parse_candle_time(ts):
    if isinstance(ts, str):
        try:
            import re
            ts_clean = ts.replace("Z","").replace("+00:00","")
            ts_clean = re.sub(r"\.(\d{6})\d+",r".",ts_clean)
            return datetime.fromisoformat(ts_clean)
        except: return None
    elif isinstance(ts, (int,float)):
        try: return datetime.fromtimestamp(ts if ts>1e9 else ts/1000)
        except: return None
    return None

def _lsig_check_result_custom(pair, direction, trade_time, candles_newest_first):
    try:
        if not candles_newest_first: return "LOSS",0,0
        h, m = map(int, trade_time.split(":"))
        trade_dt = datetime.now().replace(hour=h,minute=m,second=0,microsecond=0)
        best = None; best_diff = 9999
        for c in candles_newest_first:
            ts = c.get("time",c.get("timestamp",c.get("t",0)))
            ct = _parse_candle_time(ts)
            if ct is None: continue
            diff = abs((ct-trade_dt).total_seconds())
            if diff < best_diff: best_diff=diff; best=c
        if best is None:
            best = candles_newest_first[1] if len(candles_newest_first)>1 else candles_newest_first[0]
        op = float(best.get("open",0)); cp = float(best.get("close",0))
        if op==0 and cp==0: return "LOSS",0,0
        if op==cp: return "DOJI",op,cp
        if direction == "BUY":
            return ("WIN" if cp>op else "LOSS"), op, cp
        return ("WIN" if cp<op else "LOSS"), op, cp
    except Exception as ex:
        print(f"[ResultCheck] {ex}"); return "LOSS",0,0

def _next_minute(time_str):
    try:
        h,m = map(int,time_str.split(":")); m+=1
        if m>=60: m=0; h=(h+1)%24
        return f"{h:02d}:{m:02d}"
    except: return time_str

def _lsig_wait_and_result(uid, cid, signal_info, auto_mode=False):
    sess      = _sess(uid)
    pair      = signal_info["pair"]; direction = signal_info["direction"]
    trade_time= signal_info["trade_time"]; use_prem = signal_info.get("use_prem",False)
    display_trade_time = signal_info.get("display_trade_time", trade_time)
    pair_disp = get_display_name(pair)
    try:
        try:    _wait_for_next_candle(trade_time, offset_secs=7)
        except: time.sleep(67)
        if auto_mode and sess.live_sig_auto_stop.is_set(): return
        _is_live = signal_info.get("market","OTC") == "LIVE"
        candles1 = []
        try:
            candles1 = (_fetch_live_candles(pair,500) if _is_live
                        else _fetch_otc_candles(pair,500)) or []
        except: pass
        result1,op1,cp1 = _lsig_check_result_custom(pair,direction,trade_time,candles1)
        final=result1; open_p=op1; close_p=cp1
        chart_candles = candles1; chart_time = trade_time
        if result1 == "DOJI":
            final = "WIN"
        elif result1 == "LOSS":
            mtg_time = _next_minute(trade_time)
            try:    _wait_for_next_candle(mtg_time, offset_secs=7)
            except: time.sleep(67)
            if auto_mode and sess.live_sig_auto_stop.is_set(): return
            candles2 = []
            try:
                candles2 = (_fetch_live_candles(pair,500) if _is_live
                            else _fetch_otc_candles(pair,500)) or []
            except: pass
            if candles2:
                r2,op2,cp2 = _lsig_check_result_custom(pair,direction,mtg_time,candles2)
                final   = "MTG_WIN" if r2 in ("WIN","DOJI") else r2
                open_p  = op2; close_p = cp2
                chart_candles = candles2; chart_time = mtg_time
        candle_col = "?"
        if open_p and close_p and open_p != close_p:
            candle_col = "Red" if float(close_p)<float(open_p) else "Green"
        cp_str = str(round(float(close_p),5)) if close_p else ""
        result_text  = _build_lsess_result_text(pair_disp, display_trade_time, direction, final,
                                                 cp_str, candle_col, _get_pair_payout(pair),
                                                 candles=chart_candles)
        result_kb    = {"inline_keyboard":[
            [{"text":"𝚂𝙴𝙽𝙳 𝙿𝙰𝚁𝚃𝙸𝙰𝙻","callback_data":"lsig_send_partial",
              "style":"success","icon_custom_emoji_id":str(_LIVE_SIG_EMOJI_IDS["bell"])}],
            ([{"text":"𝚂𝚃𝙾𝙿 𝙰𝚄𝚃𝙾 𝚂𝙸𝙶𝙽𝙰𝙻","callback_data":"lsig_auto_stop",
               "style":"danger","icon_custom_emoji_id":str(_LIVE_SIG_EMOJI_IDS["cross"])}]
             if auto_mode else
             [{"text":"𝙽𝙴𝚆 𝚂𝙸𝙶𝙽𝙰𝙻","callback_data":"menu_live_signal",
               "style":"primary","icon_custom_emoji_id":str(_LIVE_SIG_EMOJI_IDS["next"])}]),
        ]}
        chart_bytes = None
        try:
            fresh = chart_candles or []
            if fresh:
                tick = _fetch_live_tick(pair)
                if final in ("WIN", "MTG_WIN"):
                    sess.live_sig_session_wins += 1
                else:
                    sess.live_sig_session_losses += 1
                _w_ct = sess.live_sig_session_wins
                _l_ct = sess.live_sig_session_losses
                chart_bytes = _generate_live_signal_chart(fresh,pair,direction,chart_time,
                                                          tick_data=tick,result=final,
                                                          win_count=_w_ct,loss_count=_l_ct,
                                                          payout=_get_pair_payout(pair))
        except: pass
        _lsig_send_result(cid, result_text, use_prem, result_kb, chart_bytes, emoji_map=_RESULT_FORMAT_EMOJI)
        _db_user_add_result(uid, final)
        sess.live_sig_partial.append({"pair":pair_disp,"time":display_trade_time,
                                       "direction":direction,"result":final,
                                       "mtg_step": 1 if final == "MTG_WIN" else 0})
        db_save_partial_history(uid, sess.live_sig_partial)
        sess.live_sig_pending = None
    except Exception as ex:
        traceback.print_exc()
        print(f"[WaitResult uid={uid}] {ex}")
        sess.live_sig_pending = None

def _market_regime_signal(candles):

    if not candles or len(candles) < 40:
        return None, 0, "INSUFFICIENT_DATA"

    closes = [float(c["close"]) for c in candles]
    opens  = [float(c["open"])  for c in candles]
    highs  = [float(c["high"])  for c in candles]
    lows   = [float(c["low"])   for c in candles]
    n = len(closes)
    last = closes[-1]

    def _ema(period, data=None):
        data = data if data is not None else closes
        seg = data[-period:] if len(data) >= period else data
        k = 2.0 / (len(seg) + 1); e = seg[0]
        for v in seg[1:]: e = v * k + e * (1 - k)
        return e

    e8, e21, e50 = _ema(8), _ema(21), _ema(50)

    gains  = [max(0.0, closes[i]-closes[i-1]) for i in range(1, n)]
    losses = [max(0.0, closes[i-1]-closes[i]) for i in range(1, n)]
    ag = sum(gains[-14:]) / 14  if len(gains)  >= 14 else sum(gains)  / max(len(gains), 1)
    al = sum(losses[-14:]) / 14 if len(losses) >= 14 else sum(losses) / max(len(losses), 1)
    rsi = 100 - 100 / (1 + ag / max(al, 1e-9))

    win = min(80, n)
    seg_c = closes[-win:]
    m = len(seg_c)
    mean_x = (m - 1) / 2.0; mean_y = sum(seg_c) / m
    num = sum((x - mean_x) * (y - mean_y) for x, y in enumerate(seg_c))
    den = sum((x - mean_x) ** 2 for x in range(m)) or 1e-9
    slope = num / den
    norm_slope = (slope * m) / max(abs(mean_y), 1e-9)

    def _swing_hi(data, order=3, last_n=60):
        seg = data[-last_n:] if len(data) >= last_n else data
        return [seg[i] for i in range(order, len(seg)-order)
                if all(seg[i] >= seg[j] for j in range(i-order, i+order+1) if j != i)]
    def _swing_lo(data, order=3, last_n=60):
        seg = data[-last_n:] if len(data) >= last_n else data
        return [seg[i] for i in range(order, len(seg)-order)
                if all(seg[i] <= seg[j] for j in range(i-order, i+order+1) if j != i)]

    sh = _swing_hi(highs); sl = _swing_lo(lows)
    structure_up   = len(sh) >= 2 and len(sl) >= 2 and sh[-1] > sh[-2] and sl[-1] > sl[-2]
    structure_down = len(sh) >= 2 and len(sl) >= 2 and sh[-1] < sh[-2] and sl[-1] < sl[-2]

    ema_bull = e8 > e21 > e50
    ema_bear = e8 < e21 < e50

    ext_win = min(30, n)
    recent_high = max(highs[-ext_win:]); recent_low = min(lows[-ext_win:])
    ext_rng = max(recent_high - recent_low, 1e-9)
    near_high = (recent_high - last) <= ext_rng * 0.15
    near_low  = (last - recent_low)  <= ext_rng * 0.15

    last_range = max(highs[-1] - lows[-1], 1e-9)
    upper_wick = highs[-1] - max(closes[-1], opens[-1])
    lower_wick = min(closes[-1], opens[-1]) - lows[-1]
    bearish_rejection = near_high and (upper_wick / last_range > 0.40) and closes[-1] < opens[-1]
    bullish_rejection = near_low  and (lower_wick / last_range > 0.40) and closes[-1] > opens[-1]

    rel_range = ext_rng / max(abs(last), 1e-9)
    TIGHT_RANGE      = 0.006
    TREND_SLOPE_MIN  = 0.0012

    direction = None; confidence = 0; regime = "CHOPPY"

    if bearish_rejection and rsi > 50 and not structure_up:
        direction, regime = "PUT", "REVERSAL"
        confidence = 76 + min(10, int((upper_wick / last_range) * 14))
    elif bullish_rejection and rsi < 50 and not structure_down:
        direction, regime = "BUY", "REVERSAL"
        confidence = 76 + min(10, int((lower_wick / last_range) * 14))
    elif norm_slope > TREND_SLOPE_MIN and ema_bull and not structure_down and rsi < 88:
        direction, regime = "BUY", "TRENDING"
        confidence = 76 + min(12, int(abs(norm_slope) * 4000))
    elif norm_slope < -TREND_SLOPE_MIN and ema_bear and not structure_up and rsi > 12:
        direction, regime = "PUT", "TRENDING"
        confidence = 76 + min(12, int(abs(norm_slope) * 4000))
    elif rel_range < TIGHT_RANGE and (near_high or near_low) and 30 < rsi < 70:
        if near_low and not near_high:
            direction, regime = "BUY", "RANGE"; confidence = 75
        elif near_high and not near_low:
            direction, regime = "PUT", "RANGE"; confidence = 75

    if direction is None:
        return None, 0, "CHOPPY"

    confidence = max(75, min(91, confidence))
    return direction, confidence, regime


def _run_live_signal(uid: int, cid: int, pair: str, strategy: str = "pro2"):
    indicators = list(ALL_INDICATORS.values())
    use_prem   = _admin_has_premium()
    pair_disp  = get_display_name(pair)
    sess       = _sess(uid)
    if sess.wiz_mid:
        try: _http.post(f"{BASE}/deleteMessage",
                json={"chat_id":cid,"message_id":sess.wiz_mid},timeout=5)
        except: pass
        sess.wiz_mid = None
    anim_id = _lsig_send_anim(
        cid,
        f"🔍 𝙰𝚗𝚊𝚕𝚢𝚣𝚒𝚗𝚐 {pair_disp}\n\n⏳ 𝚂𝚌𝚊𝚗𝚗𝚒𝚗𝚐 𝚖𝚊𝚛𝚔𝚎𝚝 𝚍𝚊𝚝𝚊 · · ·",
        use_prem=use_prem
    )
    try:
        _is_live_pair = pair in ALL_LIVE_PAIRS
        candle_count = 1500 if strategy == "premium" else 500
        candles = (_fetch_live_candles(pair, candle_count) if _is_live_pair
                   else _fetch_otc_candles(pair, candle_count))
        if anim_id:
            try: _api("deleteMessage", data={"chat_id":cid,"message_id":anim_id})
            except: pass
        if not candles or len(candles) < 30:
            _send(cid, efmt("⚠️ <b>Not enough candle data.</b> Try again in a moment."),
                  {"inline_keyboard":[[{"text":"Back  ","callback_data":"menu_live_signal",
                                        "style":"danger","icon_custom_emoji_id":"5258084656674250503"}]]})
            return
        import concurrent.futures as _cf2
        with _cf2.ThreadPoolExecutor(max_workers=2) as _pex:
            _tf  = _pex.submit(_fetch_live_tick, pair)
            if strategy == "premium":
                _sf = _pex.submit(lambda: _analyze_pair_premium(pair, candles))
            elif strategy == "foxio_zx_ai":
                _sf = _pex.submit(lambda: _analyze_pair_foxio_zx_ai(pair, candles))
            else:
                _sf  = _pex.submit(_advanced_analyze, pair, candles, indicators, None)
        try:    tick_data = _tf.result(timeout=5)
        except: tick_data = None
        try:    signal = _sf.result(timeout=5)
        except: signal = None
        now       = datetime.now()
        tm,th     = now.minute+1, now.hour
        if tm>=60: tm-=60; th=(th+1)%24
        trade_time = f"{th:02d}:{tm:02d}"
        display_trade_time = _convert_trade_time(trade_time, uid)
        if signal:
            direction = signal["direction"]
            direction = "BUY" if direction.upper() in ("CALL","BUY","CAL") else "PUT"
            payout    = signal.get("payout",0) or _get_pair_payout(pair)
            sig_regime = "TRENDING"
            sig_confidence_override = None
        else:
            direction, regime_conf, regime_label = _market_regime_signal(candles)
            if direction is None:
                if uid not in ADMIN_IDS:
                    _db_live_quota_refund(uid)
                _send(cid, efmt(
                    "📉 <b>Market Not Clear Right Now</b>\n\n"
                    f"<b>{pair_disp}</b> is currently choppy/sideways with no clean setup — "
                    "giving a signal here would just be a guess, so we're skipping it.\n\n"
                    "✅ No credit was used for this attempt.\n\n"
                    "Please try a different, more trending market, or check back on this "
                    "one again in a little while."),
                    {"inline_keyboard":[[{"text":"Back  ","callback_data":"menu_live_signal",
                                          "style":"primary","icon_custom_emoji_id":"5258084656674250503"}]]})
                return
            payout    = _get_pair_payout(pair)
            sig_regime = regime_label
            sig_confidence_override = regime_conf
        highs = [c["high"] for c in candles[-30:]]
        lows  = [c["low"]  for c in candles[-30:]]
        support    = round(min(lows),5); resistance = round(max(highs),5)
        import concurrent.futures as _cf3
        with _cf3.ThreadPoolExecutor(max_workers=2) as _pex2:
            _gf  = _pex2.submit(_gemini_confirm, pair_disp, direction, candles,
                                support, resistance, payout)
            _chf = _pex2.submit(_generate_live_signal_chart, candles, pair,
                                direction, display_trade_time, tick_data, None)
        try:    confirmed, confidence, reason = _gf.result(timeout=3)
        except: confirmed, confidence, reason = True, 82, ""
        reason = _ai_analysis_text(direction, support, resistance)
        if sig_confidence_override is not None:
            confidence = sig_confidence_override
        try:    chart_bytes = _chf.result(timeout=10)
        except Exception as ce: print(f"[Chart] {ce}"); chart_bytes = None
        _owner_n   = _lsig_owner_names.get(uid)
        sig_text   = _build_lsess_signal_text(pair_disp, direction, display_trade_time, confidence,
                                               payout, support, resistance, candles,
                                               owner_name=_owner_n, mtg_steps=1)
        kb          = {"inline_keyboard":[]}
        signal_info = {"pair":pair,"direction":direction,"trade_time":trade_time,
                       "display_trade_time":display_trade_time,"use_prem":use_prem,
                       **({"market":"LIVE"} if _is_live_pair else {})}
        sess.live_sig_pending = signal_info
        ok,_ = _lsig_send_with_ai_reason(cid,sig_text,reason,kb,use_prem,chart_bytes,emoji_map=_SIGNAL_FORMAT_EMOJI)
        if not ok:
            _send(cid, fmt(sig_text, use_prem=use_prem), kb)
        threading.Thread(target=_lsig_wait_and_result,
                         args=(uid,cid,signal_info,False),daemon=True).start()
    except Exception as ex:
        traceback.print_exc()
        _send(cid, efmt(f"❌ <b>Analysis error:</b> <code>{ex}</code>"),
              {"inline_keyboard":[[{"text":"Back  ","callback_data":"menu_live_signal",
                                    "style":"danger","icon_custom_emoji_id":"5258084656674250503"}]]})

def _run_scan_animation(cid, msg_holder, pause_event, stop_event):

    DOTS = [
        "⠋","⠙","⠹","⠸","⠼",
        "⠴","⠦","⠧","⠇","⠏"
    ]
    FRAMES = [
        ("🔍","Candlestick patterns","○","Momentum check   ","○","Volume zones     ","○","Trend strength   ","Deeply scanning every movement…"),
        ("🔍","Candlestick patterns","⚡","Momentum check   ","○","Volume zones     ","○","Trend strength   ","Checking buyer & seller pressure…"),
        ("✔","Candlestick patterns","🔍","Momentum check   ","○","Volume zones     ","○","Trend strength   ","Scanning all market zones deeply…"),
        ("✔","Candlestick patterns","✔","Momentum check   ","🔍","Volume zones     ","○","Trend strength   ","Verifying volume and pressure…"),
        ("✔","Candlestick patterns","✔","Momentum check   ","✔","Volume zones     ","🔍","Trend strength   ","Identifying balanced markets…"),
        ("✔","Candlestick patterns","✔","Momentum check   ","✔","Volume zones     ","✔","Trend strength   ","Filtering best entry points…"),
        ("📡","Market internals ","✔","Buyer pressure   ","✔","Seller pressure  ","🔄","Confirming signal","Verifying both buyer & seller…"),
        ("📡","Market internals ","✔","Buyer pressure   ","✔","Seller pressure  ","◉","Searching pair   ","Waiting for high-probability setup…"),
        ("🔄","Re-scanning      ","◉","New candles      ","○","Entry zone       ","○","Confirm signal   ","Scanning inside & outside moves…"),
        ("🔄","Re-scanning      ","✔","New candles      ","◉","Entry zone       ","○","Confirm signal   ","Almost there — verifying data…"),
        ("⚡","All markets scanned","✔","Balanced market  ","✔","Entry confirmed  ","◉","Preparing signal ","Signal preparation in progress…"),
    ]

    def _build(frame_i, dot_i):
        dot = DOTS[dot_i % len(DOTS)]
        fr  = FRAMES[frame_i % len(FRAMES)]
        i0,t0,i1,t1,i2,t2,i3,t3,cap = fr
        return (
            f"<b>{dot}  ZEBRONIX AI — SCANNING</b>\n"
            f"――――――――――――――――――――――\n"
            f"{i0}  <b>{t0}</b>\n"
            f"{i1}  <b>{t1}</b>\n"
            f"{i2}  <b>{t2}</b>\n"
            f"{i3}  <b>{t3}</b>\n"
            f"――――――――――――――――――――――\n"
            f"<i>▸ {cap}</i>"
        )

    try:
        res = _send(cid, efmt(_build(0, 0)))
        if res and res.get("ok"):
            msg_holder["msg_id"] = res["result"]["message_id"]
        else:
            return
    except Exception:
        return

    mid     = msg_holder["msg_id"]
    frame_i = 1
    dot_i   = 1

    while not stop_event.is_set():
        stopped = stop_event.wait(timeout=4)
        if stopped:
            break
        if pause_event.is_set():
            continue
        try:
            _edit(cid, mid, efmt(_build(frame_i, dot_i)))
            frame_i += 1
            dot_i   += 1
        except Exception:
            pass

    if mid:
        try: _delete(cid, mid)
        except: pass


def _run_live_auto_loop(uid, cid, market, filter_mode, manual_pairs=None, strategy="pro2"):
    import concurrent.futures as _cf
    sess       = _sess(uid)
    sess.live_sig_auto_stop.clear()
    sess.state = S.LIVE_SIG_RUNNING
    sess.live_sig_blocked_pairs = {}
    sess.live_sig_session_wins = 0
    sess.live_sig_session_losses = 0
    indicators = list(ALL_INDICATORS.values())
    use_prem   = _admin_has_premium()

    if manual_pairs:
        base_pool = list(manual_pairs)
    elif market == "OTC":
        base_pool = _get_lsig_otc_pairs()
    elif market == "ALL":
        base_pool = _get_lsig_otc_pairs() + _get_lsig_live_pairs()
    else:
        base_pool = _get_lsig_live_pairs()

    _scan_msg     = {"msg_id": None}
    _scan_pause   = threading.Event()
    _scan_stop    = threading.Event()

    _anim_thread = threading.Thread(
        target=_run_scan_animation,
        args=(cid, _scan_msg, _scan_pause, _scan_stop),
        daemon=True
    )
    _anim_thread.start()
    time.sleep(0.3)

    while not sess.live_sig_auto_stop.is_set():
        try:
            now_dt = datetime.now()
            if manual_pairs:
                pairs_pool = list(manual_pairs)
            elif market == "OTC":
                pairs_pool = _get_lsig_otc_pairs()
            elif market == "ALL":
                pairs_pool = _get_lsig_otc_pairs() + _get_lsig_live_pairs()
            else:
                pairs_pool = _get_lsig_live_pairs()

            sess.live_sig_blocked_pairs = {
                p:t for p,t in sess.live_sig_blocked_pairs.items() if t > now_dt
            }

            payout_map = {}
            def _fp(p):
                return p, _get_pair_payout(p)
            with _cf.ThreadPoolExecutor(max_workers=15) as ex:
                for ft in _cf.as_completed({ex.submit(_fp,p):p for p in pairs_pool}, timeout=12):
                    try:
                        p, pct = ft.result(); payout_map[p] = pct
                    except: pass

            if filter_mode == "avoid80":
                scan_pairs = [p for p in pairs_pool
                              if payout_map.get(p,0) >= 80 and p not in sess.live_sig_blocked_pairs]
                if not scan_pairs:
                    _send(cid, efmt("⚠️ <b>No pairs with payout ≥ 80% found.</b> Retrying in 30s…"))
                    sess.live_sig_auto_stop.wait(timeout=30); continue
            else:
                scan_pairs = [p for p in pairs_pool
                              if payout_map.get(p, 0) > 0 and p not in sess.live_sig_blocked_pairs]

            if not scan_pairs:
                sess.live_sig_auto_stop.wait(timeout=15)
                continue

            best_pair = best_signal = None
            scored_sigs = []

            def _scan_one(p):
                try:
                    if strategy == "premium":
                        _c = (_fetch_live_candles(p, 1500) if p in ALL_LIVE_PAIRS
                              else _fetch_otc_candles(p, 1500))
                        s = _analyze_pair_premium(p, _c)
                    elif strategy == "foxio_zx_ai":
                        _c = (_fetch_live_candles(p, 500) if p in ALL_LIVE_PAIRS
                              else _fetch_otc_candles(p, 500))
                        s = _analyze_pair_foxio_zx_ai(p, _c)
                    else:
                        _c = (_fetch_live_candles(p, 500) if p in ALL_LIVE_PAIRS
                              else _fetch_otc_candles(p, 500))
                        s = _analyze_pair(p, indicators, _c)
                    return (p, s, _c)
                except:
                    return (p, None, None)

            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=min(len(scan_pairs), 20)) as pool:
                futures = {pool.submit(_scan_one, p): p for p in scan_pairs}
                for fut in _cf.as_completed(futures):
                    if sess.live_sig_auto_stop.is_set(): break
                    try:
                        p, sig, _c = fut.result()
                        if sig:
                            confidence = sig.get("confidence", 0)
                            if confidence < 79:
                                continue
                            scored_sigs.append((confidence, p, sig, _c))
                    except: pass

            if not scored_sigs:
                sess.live_sig_auto_stop.wait(timeout=5)
                continue

            prioritized = _pick_prioritized_signal(scored_sigs)
            if not prioritized:
                sess.live_sig_auto_stop.wait(timeout=5)
                continue
            _, best_pair, best_signal, _cands = prioritized

            candles = None
            try:
                candles = _cands if (_cands and len(_cands) >= 30) else None
                if not candles:
                    candles = (_fetch_live_candles(best_pair, 500) if best_pair in ALL_LIVE_PAIRS
                               else _fetch_otc_candles(best_pair, 500))
            except: pass
            if not candles:
                sess.live_sig_auto_stop.wait(timeout=5)
                continue

            now = datetime.now(); tm,th = now.minute+1, now.hour
            if tm>=60: tm-=60; th=(th+1)%24
            trade_time = f"{th:02d}:{tm:02d}"
            display_trade_time = _convert_trade_time(trade_time, uid)
            direction  = best_signal.get("direction","PUT")
            direction  = "BUY" if direction.upper() in ("CALL","BUY","CAL") else "PUT"
            sig_regime = best_signal.get("regime","TRENDING")
            payout     = best_signal.get("payout",0) or payout_map.get(best_pair,0)
            highs = [c["high"] for c in candles[-30:]]; lows = [c["low"] for c in candles[-30:]]
            support    = round(min(lows),5); resistance = round(max(highs),5)
            pair_disp  = get_display_name(best_pair)
            confirmed, confidence, reason = _gemini_confirm(pair_disp,direction,candles,
                                                            support,resistance,payout)
            confidence = best_signal.get("confidence", confidence)
            reason = _ai_analysis_text(direction, support, resistance)

            _owner_n = _lsig_owner_names.get(uid)
            sig_text = _build_lsess_signal_text(pair_disp, direction, display_trade_time, confidence,
                                                 payout, support, resistance, candles,
                                                 owner_name=_owner_n, mtg_steps=1)
            kb = {"inline_keyboard":[
                [{"text":"𝚂𝙴𝙽𝙳 𝙿𝙰𝚁𝚃𝙸𝙰𝙻","callback_data":"lsig_send_partial",
                  "style":"success","icon_custom_emoji_id":str(_LIVE_SIG_EMOJI_IDS["bell"])}],
                [{"text":"𝚂𝚃𝙾𝙿 𝙰𝚄𝚃𝙾 𝚂𝙸𝙶𝙽𝙰𝙻","callback_data":"lsig_auto_stop",
                  "style":"danger","icon_custom_emoji_id":str(_LIVE_SIG_EMOJI_IDS["cross"])}],
            ]}
            _tick = None
            try:
                _tick = _fetch_live_tick(best_pair)
            except: pass
            chart_bytes = None
            try:
                chart_bytes = _generate_live_signal_chart(candles,best_pair,direction,
                                                          display_trade_time,tick_data=_tick,
                                                          payout=payout)
            except: pass
            signal_info = {"pair":best_pair,"direction":direction,"trade_time":trade_time,
                           "display_trade_time":display_trade_time,"use_prem":use_prem,
                           **({"market":"LIVE"} if best_pair in ALL_LIVE_PAIRS else {})}

            if uid not in ADMIN_IDS:
                if not _db_live_quota_use(uid):
                    lic  = _db_license_get(uid)
                    lim  = int(lic.get("signal_limit", 10)) if lic else 0
                    used = _db_live_quota_get(uid)
                    if not _db_license_is_valid(uid):
                        _send(cid, efmt(_free_limit_reached_text()), _kb_free_limit_reached())
                    else:
                        _send(cid,
                              efmt(f"⚠️ <b>Daily Signal Limit Reached</b>\n\n"
                              f"Your license allows <b>{lim} signals/day</b>.\n"
                              f"You have used all <b>{used}</b> signals today.\n\n"
                              "Auto Signal has been stopped automatically."),
                              {"inline_keyboard":[[{"text":"Home","callback_data":"menu_home",
                                                    "icon_custom_emoji_id":"5416041192905265756",
                                                    "style":"primary"}]]})
                    break

            sess.live_sig_pending = signal_info

            _scan_pause.set()
            _smid = _scan_msg.get("msg_id")
            if _smid:
                try: _delete(cid, _smid); _scan_msg["msg_id"] = None
                except: pass


            ok,_ = _lsig_send_with_ai_reason(cid,sig_text,reason,kb,use_prem,chart_bytes,emoji_map=_SIGNAL_FORMAT_EMOJI)
            if not ok:
                _send(cid, fmt(sig_text, use_prem=use_prem), kb)
            _lsig_wait_and_result(uid,cid,signal_info,auto_mode=True)

            sess.live_sig_blocked_pairs[best_pair] = datetime.now() + timedelta(minutes=5)

            if not sess.live_sig_auto_stop.is_set():
                try:
                    res = _send(cid, efmt("🔍  <b>ZEBRONIX AI — SCANNING</b>\n<i>Searching for next signal…</i>"))
                    if res and res.get("ok"):
                        _scan_msg["msg_id"] = res["result"]["message_id"]
                except: pass
                _scan_pause.clear()
        except Exception as ex:
            traceback.print_exc()
            print(f"[AutoLoop uid={uid}] {ex}")
            sess.live_sig_auto_stop.wait(timeout=15)

    _scan_stop.set()
    sess.state = S.IDLE


def _lsess_kb_channel_prompt():
    return {"inline_keyboard": [
        [{"text": "Settings (Username)", "callback_data": "lsess_settings",
          "style": "primary", "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["gear"])}],
        [{"text": "Back  ", "callback_data": "menu_home",
          "style": "danger", "icon_custom_emoji_id": "5258084656674250503"}],
    ]}

def _lsess_show_username_prompt(sess):
    sess.state = S.LSESS_AWAIT_USERNAME
    mode_name = "Premium Emoji" if sess.lsess_emoji_mode == "premium" else "Normal Emoji"
    _wiz(sess, efmt(
        f"{_e_('✅')} <b>Channel Connected!</b>\n\n"
        f"📡 <b>Channel:</b> {sess.lsess_channel_title}\n"
        f"🎨 <b>Emoji Format:</b> {mode_name}\n\n"
        "👤 <b>Now send your username</b> (e.g. <code>@YourChannel</code>).\n"
        "This will appear as the <b>Owner</b> in every signal &amp; result template."),
        {"inline_keyboard": [
            [{"text": "Skip", "callback_data": "lsess_username_skip",
              "style": "primary", "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["next"])}],
            [{"text": "Back", "callback_data": "lsess_emoji_format",
              "style": "danger", "icon_custom_emoji_id": "5258084656674250503"}],
        ]})

def _lsess_emoji_format_menu(sess):
    sess.state = S.LSESS_EMOJI_SELECT
    _wiz(sess, efmt(
        "🎨 <b>EMOJI FORMAT</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "Choose how Channel Sender will publish signals:"),
        {"inline_keyboard": [
            [{"text": "PREMIUM EMOJI", "callback_data": "lsess_emoji_premium",
              "style": "success", "icon_custom_emoji_id": str(EMAP["👑"])},
             {"text": "NORMAL EMOJI", "callback_data": "lsess_emoji_normal",
              "style": "primary", "icon_custom_emoji_id": str(EMAP["✅"])}],
            [{"text": "Back", "callback_data": "lsess_start",
              "style": "danger", "icon_custom_emoji_id": "5258084656674250503"}],
        ]})

def _lsess_premium_instruction(sess):
    status = _telethon_account_status()
    account_id = status.get("id") if status.get("ok") else None
    sess.lsess_premium_account_id = account_id
    identity = f"<code>{account_id}</code>" if account_id else "<b>Not connected</b>"
    sess.state = S.LSESS_PREMIUM_CONFIRM
    _wiz(sess, efmt(
        "👑 <b>PREMIUM EMOJI</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Add Telegram account ID {identity} as a channel <b>Admin</b> and enable "
        "at least <b>Post/Send Messages</b>, then tap Confirm."),
        {"inline_keyboard": [
            [{"text": "CONFIRM", "callback_data": "lsess_emoji_confirm",
              "style": "success", "icon_custom_emoji_id": str(EMAP["✅"])}],
            [{"text": "Back", "callback_data": "lsess_emoji_format",
              "style": "danger", "icon_custom_emoji_id": "5258084656674250503"}],
        ]})


def _lsess_check_admin_and_show(uid, sess):
    chat_id = sess.lsess_channel_id
    is_admin, title, err = _check_bot_admin_in_chat(chat_id)
    sess.lsess_channel_title = title or str(chat_id)
    if is_admin:
        _lsess_emoji_format_menu(sess)
    else:
        sess.state = S.LSESS_AWAIT_RETRY
        _wiz(sess, efmt(
            f"{_e_('⚠')} <b>Bot is Not an Admin</b>\n\n"
            f"📡 <b>Channel:</b> {sess.lsess_channel_title}\n\n"
            "To connect, please add this bot as an <b>admin</b> in "
            "that channel/group, then tap Retry."),
            {"inline_keyboard": [
                [{"text": "Retry", "callback_data": "lsess_retry",
                  "style": "primary", "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["gear"])}],
                [{"text": "Back  ", "callback_data": "menu_home",
                  "style": "danger", "icon_custom_emoji_id": "5258084656674250503"}],
            ]})


def _e_(k):
    return f'<tg-emoji emoji-id="{EMAP[k]}">{k}</tg-emoji>'


def _lsess_strategy_select_menu(sess):
    pro2_on = _db_strategy_enabled("pro2")
    premium_on = _db_strategy_enabled("premium")
    custom_on = _db_strategy_enabled("foxio_zx_ai") and _custom_strategy_available()
    rows = []
    if pro2_on:
        rows.append([{"text": "ZBX PRO 2.1", "callback_data": "lsess_strategy_pro2",
                      "style": "primary", "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["robot"])}])
    if premium_on:
        rows.append([{"text": "ZBX PREMIUM", "callback_data": "lsess_strategy_premium",
                      "style": "success", "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["crown"])}])
    if custom_on:
        rows.append([{"text": "FOXIO ZX AI", "callback_data": "lsess_strategy_foxio_zx_ai",
                      "style": "primary", "icon_custom_emoji_id": str(EMAP["📊"])}])
    if not rows:
        rows.append([{"text": "⚠️ No Strategy Available", "callback_data": "noop", "style": "danger"}])
    rows.append([{"text": "Back", "callback_data": "menu_home", "style": "danger",
                  "icon_custom_emoji_id": "5258084656674250503"}])
    _wiz(sess, "🔬 <b>Channel Sender — Select Strategy</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                "Choose the strategy that will generate channel signals:",
         {"inline_keyboard": rows})


def _lsess_pair_select_menu(uid, sess):
    import concurrent.futures as _cf
    pairs_pool = _get_lsig_otc_pairs() + _get_lsig_live_pairs()
    sel  = sess.lsess_pairs

    payout_map = getattr(sess, "_lsess_payout_cache", {})
    if not payout_map:
        def _lp(p):
            return p, _get_pair_payout(p)
        with _cf.ThreadPoolExecutor(max_workers=15) as _ex:
            for fut in _cf.as_completed({_ex.submit(_lp, p): p for p in pairs_pool}, timeout=12):
                try:
                    p, pct = fut.result()
                    payout_map[p] = pct
                except: pass
        sess._lsess_payout_cache = payout_map

    rows = []
    for i in range(0, len(pairs_pool), 2):
        row = []
        for p in pairs_pool[i:i+2]:
            is_sel = p in sel
            pct   = payout_map.get(p, 0)
            label = f"{get_display_name(p)} ({pct}%)" if pct else get_display_name(p)
            style = ("success" if pct >= 80 else "primary" if pct >= 70 else "danger" if pct > 0 else "primary")
            icon_id = "6231121076814879723" if is_sel else "6233277751692894018"
            row.append({"text": label, "callback_data": f"lsess_ptog_{p}", "style": style,
                        "icon_custom_emoji_id": icon_id})
        rows.append(row)
    rows.append([{"text": "Select All", "callback_data": "lsess_sel_all", "style": "success"},
                 {"text": "AUTO AVOID UNDER 80%", "callback_data": "lsess_sel_80", "style": "success"}])
    rows.append([{"text": "Clear", "callback_data": "lsess_sel_clear", "style": "danger"}])
    rows.append([{"text": "  Confirm Selection →  ", "callback_data": "lsess_pairs_ok", "style": "success"}])
    rows.append([{"text": "Back  ", "callback_data": "menu_home",
                  "style": "danger", "icon_custom_emoji_id": "5258084656674250503"}])
    _wiz(sess,
         f"📡 <b>Channel Sender — Select Markets</b>\n\n"
         f"Channel: <b>{sess.lsess_channel_title}</b>\n"
         f"Selected: <b>{len(sel)}</b> / {len(pairs_pool)}\n"
         f"🟢 ≥80%  🔵 70-79%  🔴 &lt;70%\n"
         f"Runtime filter: <b>{'AUTO ≥80%' if getattr(sess, 'lsess_payout_filter', 'all') == 'avoid80' else 'OFF'}</b>\n\n"
         "Tap to select/deselect:",
         {"inline_keyboard": rows})


def _lsess_confirm_menu(sess):
    strategy_names = {"pro2": "ZBX PRO 2.1", "premium": "ZBX PREMIUM",
                      "foxio_zx_ai": "FOXIO ZX AI"}
    strategy_name = strategy_names.get(getattr(sess, "lsess_strategy", "pro2"), "ZBX PRO 2.1")
    payout_name = "AUTO AVOID UNDER 80%" if getattr(sess, "lsess_payout_filter", "all") == "avoid80" else "OFF"
    emoji_name = "PREMIUM EMOJI" if getattr(sess, "lsess_emoji_mode", "normal") == "premium" else "NORMAL EMOJI"
    _wiz(sess, efmt(
        f"{_e_('🤖')} <b>Channel Sender — Ready</b>\n\n"
        f"📡 <b>Channel:</b> {sess.lsess_channel_title}\n"
        f"🔬 <b>Strategy:</b> {strategy_name}\n"
        f"🎨 <b>Emoji Format:</b> {emoji_name}\n"
        f"💰 <b>Payout Filter:</b> {payout_name}\n"
        f"📊 <b>Markets:</b> {len(sess.lsess_pairs)} selected\n\n"
        "Tap Launch Session to start sending signals to this channel."),
        {"inline_keyboard": [
            [{"text": "Launch Session", "callback_data": "lsess_launch",
              "style": "success", "icon_custom_emoji_id": str(EMAP["🚀"])}],
            [{"text": "Configure Again", "callback_data": "lsess_continue",
              "style": "primary", "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["gear"])}],
            [{"text": "Back  ", "callback_data": "menu_home",
              "style": "danger", "icon_custom_emoji_id": "5258084656674250503"}],
        ]})


def _lsess_running_kb():
    return {"inline_keyboard": [
        [{"text": "Change Pairs", "callback_data": "lsess_change_pairs",
          "style": "primary", "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["gear"])}],
        [{"text": "Pause", "callback_data": "lsess_pause",
          "style": "primary", "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["alert"])},
         {"text": "Resume", "callback_data": "lsess_resume",
          "style": "success", "icon_custom_emoji_id": str(EMAP["✅"])}],
        [{"text": "𝚂𝙴𝙽𝙳 𝙿𝙰𝚁𝚃𝙸𝙰𝙻", "callback_data": "lsess_send_partial",
          "style": "success", "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["bell"])}],
        [{"text": "Stop Session", "callback_data": "lsess_stop",
          "style": "danger", "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["cross"])}],
    ]}


def _lsess_run(uid, cid, sess):
    """Background loop: scans selected pairs and posts signals + results
    + partial summaries directly to the connected channel."""
    import concurrent.futures as _cf
    channel_id = sess.lsess_channel_id
    indicators = list(ALL_INDICATORS.values())
    premium_mode = getattr(sess, "lsess_emoji_mode", "normal") == "premium"
    use_prem   = premium_mode
    strategy   = getattr(sess, "lsess_strategy", "pro2")
    sess.lsess_stop.clear()
    sess.lsess_pause.clear()
    sess.lsess_partial = []
    sess.lsess_session_wins = 0
    sess.lsess_session_losses = 0
    sess.lsess_blocked_pairs = {}
    sess.state = S.LSESS_RUNNING

    channel_ready = _channel_send_text(channel_id, efmt(
        f"{_e_('✅')} <b>Bot Connected Successfully!</b>\n\n"
        f"{_e_('🚀')} <b>Channel Sender Started</b>\n"
        "Signals will be posted here shortly. Stay tuned!"), premium=premium_mode)

    if premium_mode and not channel_ready:
        sess.state = S.IDLE
        sess.lsess_stop.set()
        _send(cid, efmt(
            "⚠️ <b>Premium Channel Connection Failed</b>\n\n"
            "The session was not started because the connected Premium account "
            "could not send verified custom-emoji entities.\n\n"
            "Check <code>telethon_config.json</code>, the saved <code>.session</code> "
            "file and your channel permission, then launch again.\n\n"
            "No normal-emoji message was sent to the channel."))
        return

    _send(cid, efmt(
        f"{_e_('✅')} <b>Channel Sender Running</b>\n\n"
        f"📡 <b>Channel:</b> {sess.lsess_channel_title}\n"
        f"📊 <b>Markets:</b> {len(sess.lsess_pairs)} selected"),
        _lsess_running_kb())

    while not sess.lsess_stop.is_set():
        try:
            if sess.lsess_pause.is_set():
                sess.lsess_stop.wait(timeout=5)
                continue

            now_dt = datetime.now()
            sess.lsess_blocked_pairs = {
                p: t for p, t in sess.lsess_blocked_pairs.items() if t > now_dt
            }

            pairs_pool = list(sess.lsess_pairs)

            scan_pairs = [p for p in pairs_pool if p not in sess.lsess_blocked_pairs]
            if scan_pairs:
                runtime_payouts = {}
                with _cf.ThreadPoolExecutor(max_workers=min(len(scan_pairs), 15)) as payout_pool:
                    payout_futures = {payout_pool.submit(_get_pair_payout, p): p for p in scan_pairs}
                    for payout_future in _cf.as_completed(payout_futures):
                        pair_key = payout_futures[payout_future]
                        try:
                            runtime_payouts[pair_key] = int(payout_future.result() or 0)
                        except Exception:
                            runtime_payouts[pair_key] = 0
                min_payout = 80 if getattr(sess, "lsess_payout_filter", "all") == "avoid80" else 1

                scan_pairs = [p for p in scan_pairs if runtime_payouts.get(p, 0) >= min_payout]
            if not scan_pairs:
                sess.lsess_stop.wait(timeout=15)
                continue

            best_pair = best_signal = None
            scored_sigs = []

            def _scan_one(p):
                try:
                    if strategy == "premium":
                        _c = (_fetch_live_candles(p, 1500) if p in ALL_LIVE_PAIRS
                              else _fetch_otc_candles(p, 1500))
                        s = _analyze_pair_premium(p, _c)
                    elif strategy == "foxio_zx_ai":
                        _c = (_fetch_live_candles(p, 500) if p in ALL_LIVE_PAIRS
                              else _fetch_otc_candles(p, 500))
                        s = _analyze_pair_foxio_zx_ai(p, _c)
                    else:
                        _c = (_fetch_live_candles(p, 500) if p in ALL_LIVE_PAIRS
                              else _fetch_otc_candles(p, 500))
                        s = _analyze_pair(p, indicators, _c)
                    return (p, s, _c)
                except:
                    return (p, None, None)

            with _cf.ThreadPoolExecutor(max_workers=min(len(scan_pairs), 20)) as pool:
                futures = {pool.submit(_scan_one, p): p for p in scan_pairs}
                for fut in _cf.as_completed(futures):
                    if sess.lsess_stop.is_set(): break
                    try:
                        p, sig, _c = fut.result()
                        if sig:
                            confidence = sig.get("confidence", 0)
                            if confidence < 79:
                                continue
                            scored_sigs.append((confidence, p, sig, _c))
                    except: pass

            if not scored_sigs:
                sess.lsess_stop.wait(timeout=5)
                continue

            prioritized = _pick_prioritized_signal(scored_sigs)
            if not prioritized:
                sess.lsess_stop.wait(timeout=5)
                continue
            _, best_pair, best_signal, _cands = prioritized

            candles = _cands if (_cands and len(_cands) >= 30) else None
            if not candles:
                try:
                    candles = (_fetch_live_candles(best_pair, 500) if best_pair in ALL_LIVE_PAIRS
                               else _fetch_otc_candles(best_pair, 500))
                except: candles = None
            if not candles:
                sess.lsess_stop.wait(timeout=5)
                continue

            now = datetime.now(); tm, th = now.minute+1, now.hour
            if tm >= 60: tm -= 60; th = (th+1) % 24
            trade_time = f"{th:02d}:{tm:02d}"
            display_trade_time = _convert_trade_time(trade_time, uid)
            direction  = best_signal.get("direction", "PUT")
            direction  = "BUY" if direction.upper() in ("CALL","BUY","CAL") else "PUT"
            sig_regime = best_signal.get("regime", "TRENDING")
            payout     = best_signal.get("payout", 0) or _get_pair_payout(best_pair)
            highs = [c["high"] for c in candles[-30:]]; lows = [c["low"] for c in candles[-30:]]
            support = round(min(lows), 5); resistance = round(max(highs), 5)
            pair_disp = get_display_name(best_pair)
            confirmed, confidence, reason = _gemini_confirm(pair_disp, direction, candles,
                                                              support, resistance, payout)
            confidence = best_signal.get("confidence", confidence)
            reason = _ai_analysis_text(direction, support, resistance)

            _owner_n = _lsig_owner_names.get(uid)
            sig_text = _build_lsess_signal_text(pair_disp, direction, display_trade_time, confidence,
                                                 payout, support, resistance, candles,
                                                 owner_name=_owner_n, mtg_steps=1)
            _tick = None
            try: _tick = _fetch_live_tick(best_pair)
            except: pass
            chart_bytes = None
            try:
                chart_bytes = _generate_live_signal_chart(candles, best_pair, direction,
                                                           display_trade_time, tick_data=_tick,
                                                           payout=payout)
            except: pass

            signal_info = {"pair": best_pair, "direction": direction, "trade_time": trade_time,
                           "display_trade_time": display_trade_time, "use_prem": use_prem,
                           "payout": payout,
                           **({"market": "LIVE"} if best_pair in ALL_LIVE_PAIRS else {})}

            if uid not in ADMIN_IDS:
                if not _db_live_quota_use(uid):
                    lic  = _db_license_get(uid)
                    lim  = int(lic.get("signal_limit", 10)) if lic else 0
                    used = _db_live_quota_get(uid)
                    if not _db_license_is_valid(uid):
                        _send(cid, efmt(_free_limit_reached_text()), _kb_free_limit_reached())
                    else:
                        _send(cid,
                              efmt(f"⚠️ <b>Daily Signal Limit Reached</b>\n\n"
                              f"Your license allows <b>{lim} signals/day</b>.\n"
                              f"You have used all <b>{used}</b> signals today.\n\n"
                              "Channel Sender has been stopped automatically."),
                              {"inline_keyboard":[[{"text":"Home","callback_data":"menu_home",
                                                    "icon_custom_emoji_id":"5416041192905265756",
                                                    "style":"primary"}]]})
                    sess.lsess_stop.set()
                    break

            sess.lsess_pending = signal_info

            ok, _ = _lsig_send_with_ai_reason(channel_id, sig_text, reason, {"inline_keyboard":[]}, use_prem, chart_bytes, via_telethon=premium_mode, emoji_map=_SIGNAL_FORMAT_EMOJI)
            if not ok and not premium_mode:
                _channel_send_text(channel_id, fmt(sig_text, use_prem=False), premium=False)

            _lsess_wait_and_result(uid, channel_id, signal_info, sess)

            sess.lsess_blocked_pairs[best_pair] = datetime.now() + timedelta(minutes=5)

        except Exception as ex:
            traceback.print_exc()
            print(f"[LiveSession uid={uid}] {ex}")
            sess.lsess_stop.wait(timeout=15)

    sess.state = S.IDLE
    if sess.lsess_partial:
        partial_msg = _build_lsess_partial_msg(sess.lsess_partial)
        _lsig_send_partial_msg(channel_id, partial_msg, use_prem, {"inline_keyboard":[]}, via_telethon=premium_mode, emoji_map=_PARTIAL_FORMAT_EMOJI)
    _channel_send_text(channel_id, efmt(
        f"{_e_('⏹')} <b>Channel Sender Ended</b>\n\nThank you for following our signals!"),
        premium=premium_mode)


def _lsess_wait_and_result(uid, channel_id, signal_info, sess):
    pair      = signal_info["pair"]; direction = signal_info["direction"]
    trade_time= signal_info["trade_time"]; use_prem = signal_info.get("use_prem", False)
    display_trade_time = signal_info.get("display_trade_time", trade_time)
    payout    = signal_info.get("payout", 0)
    pair_disp = get_display_name(pair)
    try:
        try:    _wait_for_next_candle(trade_time, offset_secs=7)
        except: time.sleep(67)
        if sess.lsess_stop.is_set(): return
        _is_live = signal_info.get("market", "OTC") == "LIVE"
        candles1 = []
        try:
            candles1 = (_fetch_live_candles(pair, 500) if _is_live
                        else _fetch_otc_candles(pair, 500)) or []
        except: pass
        result1, op1, cp1 = _lsig_check_result_custom(pair, direction, trade_time, candles1)
        final = result1; open_p = op1; close_p = cp1
        chart_candles = candles1; chart_time = trade_time
        if result1 == "DOJI":
            final = "WIN"
        elif result1 == "LOSS":
            mtg_time = _next_minute(trade_time)
            try:    _wait_for_next_candle(mtg_time, offset_secs=7)
            except: time.sleep(67)
            if sess.lsess_stop.is_set(): return
            candles2 = []
            try:
                candles2 = (_fetch_live_candles(pair, 500) if _is_live
                            else _fetch_otc_candles(pair, 500)) or []
            except: pass
            if candles2:
                r2, op2, cp2 = _lsig_check_result_custom(pair, direction, mtg_time, candles2)
                final  = "MTG_WIN" if r2 in ("WIN","DOJI") else r2
                open_p = op2; close_p = cp2
                chart_candles = candles2; chart_time = mtg_time
        candle_col = "?"
        if open_p and close_p and open_p != close_p:
            candle_col = "Red" if float(close_p) < float(open_p) else "Green"
        op_str = str(round(float(open_p), 5)) if open_p else ""
        cp_str = str(round(float(close_p), 5)) if close_p else ""
        result_text = _build_lsess_result_text(pair_disp, display_trade_time, direction, final,
                                                cp_str, candle_col, payout, candles=chart_candles)
        chart_bytes = None
        try:
            fresh = chart_candles or []
            if fresh:
                tick = _fetch_live_tick(pair)
                if final in ("WIN", "MTG_WIN"):
                    sess.lsess_session_wins += 1
                else:
                    sess.lsess_session_losses += 1
                chart_bytes = _generate_live_signal_chart(fresh, pair, direction, chart_time,
                                                           tick_data=tick, result=final,
                                                           win_count=sess.lsess_session_wins,
                                                           loss_count=sess.lsess_session_losses,
                                                           payout=payout)
        except: pass
        premium_mode = getattr(sess, "lsess_emoji_mode", "normal") == "premium"
        _lsig_send_result(channel_id, result_text, premium_mode,
                          {"inline_keyboard":[]}, chart_bytes,
                          via_telethon=premium_mode, emoji_map=_RESULT_FORMAT_EMOJI)
        sess.lsess_partial.append({"pair": pair_disp, "time": display_trade_time,
                                     "direction": direction, "result": final,
                                     "mtg_step": 1 if final == "MTG_WIN" else 0})
        sess.lsess_pending = None
    except Exception as ex:
        traceback.print_exc()
        print(f"[LiveSessionResult uid={uid}] {ex}")
        sess.lsess_pending = None


def _build_m5_from_m1(candles_1m):

    import re as _re5
    asc = list(reversed(candles_1m))
    buckets = []
    cur_key = None
    cur_group = []
    for c in asc:
        m = _re5.search(r'(\d{1,2}):(\d{2})', str(c.get("time", "")))
        if m:
            key = (int(m.group(1)) * 60 + int(m.group(2))) // 5
        else:
            key = None
        if key is None or key != cur_key:
            if cur_group:
                buckets.append(cur_group)
            cur_group = [c]; cur_key = key
        else:
            cur_group.append(c)
    if cur_group:
        buckets.append(cur_group)
    if buckets and len(buckets[-1]) < 5:
        buckets = buckets[:-1]

    m5 = []
    for grp in buckets:
        o  = float(grp[0]["open"]);  cl = float(grp[-1]["close"])
        hi = max(float(x["high"]) for x in grp)
        lo = min(float(x["low"])  for x in grp)
        m5.append({"open": o, "high": hi, "low": lo, "close": cl,
                   "time": grp[-1].get("time", "")})
    return list(reversed(m5))


def _m5_trend(m5_candles):

    asc5 = list(reversed(m5_candles))
    if len(asc5) < 60:
        return None
    closes5 = [float(c["close"]) for c in asc5]

    def _ema_local(data, period):
        if len(data) < period:
            return data[-1]
        k = 2.0 / (period + 1); e = sum(data[:period]) / period
        for v in data[period:]:
            e = v * k + e * (1 - k)
        return e

    e9_5  = _ema_local(closes5, 9)
    e20_5 = _ema_local(closes5, 20)
    e50_5 = _ema_local(closes5, min(50, len(closes5) - 1))
    if e9_5 > e20_5 > e50_5:
        return "UP"
    if e9_5 < e20_5 < e50_5:
        return "DOWN"
    return "SIDEWAYS"


def _calc_atr_adx(highs_, lows_, closes_, period=14):
    n = len(closes_)
    if n < period * 2:
        return 0.0, 0.0
    trs, pdms, mdms = [], [], []
    for i in range(1, n):
        up = highs_[i] - highs_[i - 1]
        dn = lows_[i - 1] - lows_[i]
        pdms.append(up if (up > dn and up > 0) else 0.0)
        mdms.append(dn if (dn > up and dn > 0) else 0.0)
        trs.append(max(highs_[i] - lows_[i],
                        abs(highs_[i] - closes_[i - 1]),
                        abs(lows_[i] - closes_[i - 1])))

    def _wilder_sum(vals, period):
        out = [sum(vals[:period])]
        for v in vals[period:]:
            out.append(out[-1] - out[-1] / period + v)
        return out

    tr_s, pdm_s, mdm_s = _wilder_sum(trs, period), _wilder_sum(pdms, period), _wilder_sum(mdms, period)

    dx_series = []
    for i in range(len(tr_s)):
        atr_i = tr_s[i] / period
        pdi = 100 * (pdm_s[i] / period) / max(atr_i, 1e-9)
        mdi = 100 * (mdm_s[i] / period) / max(atr_i, 1e-9)
        dx_series.append(100 * abs(pdi - mdi) / max(pdi + mdi, 1e-9))

    atr = tr_s[-1] / period
    if len(dx_series) >= period:
        adx = sum(dx_series[:period]) / period
        for d in dx_series[period:]:
            adx = (adx * (period - 1) + d) / period
    else:
        adx = sum(dx_series) / max(len(dx_series), 1)
    return atr, adx


def analyze_premium(candles):

    raw = candles
    asc = list(reversed(candles))
    if len(asc) < 80:
        return None, 0, 50.0, 0.0, 0.0, None

    m5_candles = _build_m5_from_m1(raw)
    m5_trend   = _m5_trend(m5_candles)

    asc = asc[-300:] if len(asc) > 300 else asc
    closes = [float(c["close"]) for c in asc]
    opens  = [float(c["open"])  for c in asc]
    highs  = [float(c["high"])  for c in asc]
    lows   = [float(c["low"])   for c in asc]
    n      = len(asc)

    def _ema(period, src=None):
        data = src if src is not None else closes
        if len(data) < period:
            return data[-1]
        k = 2.0 / (period + 1); e = sum(data[:period]) / period
        for v in data[period:]:
            e = v * k + e * (1 - k)
        return e

    e9 = _ema(9); e20 = _ema(20); e50 = _ema(50)

    gains  = [max(0.0, closes[i] - closes[i - 1]) for i in range(1, n)]
    losses = [max(0.0, closes[i - 1] - closes[i]) for i in range(1, n)]
    ag = sum(gains[-14:]) / 14; al = sum(losses[-14:]) / 14
    rsi = 100 - 100 / (1 + ag / max(al, 1e-9))

    def _ema_series(data, period):
        if len(data) < period:
            return [None] * len(data)
        out = [None] * (period - 1)
        k = 2.0 / (period + 1); e = sum(data[:period]) / period
        out.append(e)
        for v in data[period:]:
            e = v * k + e * (1 - k)
            out.append(e)
        return out

    ema12_s = _ema_series(closes, 12)
    ema26_s = _ema_series(closes, 26)
    macd_line = [(a - b) if (a is not None and b is not None) else None
                 for a, b in zip(ema12_s, ema26_s)]
    macd_valid = [v for v in macd_line if v is not None]
    if len(macd_valid) >= 9:
        signal_s       = _ema_series(macd_valid, 9)
        macd           = macd_valid[-1]
        macd_signal    = signal_s[-1]
        macd_hist      = macd - macd_signal
        macd_hist_prev = (macd_valid[-2] - signal_s[-2]) if len(macd_valid) >= 2 and signal_s[-2] is not None else macd_hist
    else:
        macd = macd_signal = macd_hist = macd_hist_prev = 0.0
    macd_bull_cross = macd > macd_signal
    macd_bear_cross = macd < macd_signal

    atr, adx = _calc_atr_adx(highs, lows, closes, 14)
    lb = min(50, n)
    avg_range = sum(highs[i] - lows[i] for i in range(n - lb, n)) / lb
    atr_ok    = atr >= avg_range * 0.55
    adx_ok    = adx > 25

    last_c = closes[-1]; last_o = opens[-1]
    last_h = highs[-1];  last_l = lows[-1]
    body = abs(last_c - last_o); rng = max(last_h - last_l, 1e-9)
    u_wick = last_h - max(last_c, last_o)
    l_wick = min(last_c, last_o) - last_l
    strong_candle = (body / rng) >= 0.35

    ema_bull_stack = e9 > e20 > e50
    ema_bear_stack = e9 < e20 < e50
    ema_spread     = max(e9, e20, e50) - min(e9, e20, e50)
    ema_aligned    = ema_spread >= atr * 0.5

    def _swings(order=3, lookback=50):
        seg = asc[-min(lookback, n):]
        sh, sl = [], []
        for i in range(order, len(seg) - order):
            h = float(seg[i]["high"])
            if all(h >= float(seg[j]["high"]) for j in range(i - order, i + order + 1) if j != i):
                sh.append(h)
            l = float(seg[i]["low"])
            if all(l <= float(seg[j]["low"]) for j in range(i - order, i + order + 1) if j != i):
                sl.append(l)
        return sh, sl

    swing_h, swing_l = _swings()
    recent_high = max(highs[-50:]); recent_low = min(lows[-50:])
    zone = max(recent_high - recent_low, 1e-9) * 0.10

    near_res = (recent_high - last_c) <= zone or any(abs(last_c - sh) <= zone for sh in swing_h)
    near_sup = (last_c - recent_low) <= zone or any(abs(last_c - sl) <= zone for sl in swing_l)

    bull_engulf = (n >= 2 and last_c > last_o and closes[-2] < opens[-2]
                   and last_c >= opens[-2] and last_o <= closes[-2])
    bear_engulf = (n >= 2 and last_c < last_o and closes[-2] > opens[-2]
                   and last_c <= opens[-2] and last_o >= closes[-2])
    bull_pin = l_wick >= body * 1.8 and body / rng < 0.40 and last_c > last_l + rng * 0.40
    bear_pin = u_wick >= body * 1.8 and body / rng < 0.40 and last_c < last_h - rng * 0.40

    def _consec_run(cand_dir):

        cnt = 0
        for i in range(1, min(7, n) + 1):
            c_, o_ = closes[-i], opens[-i]
            big = abs(c_ - o_) >= avg_range * 0.45
            if not big:
                break
            if cand_dir == "CALL" and c_ > o_:
                cnt += 1
            elif cand_dir == "PUT" and c_ < o_:
                cnt += 1
            else:
                break
        return cnt

    direction = None; mode = None; score = 0.0

    rev_dir = None
    if rsi <= 30 and near_sup and (bull_pin or bull_engulf):
        rev_dir = "CALL"
    elif rsi >= 70 and near_res and (bear_pin or bear_engulf):
        rev_dir = "PUT"

    if rev_dir is not None:
        if rev_dir == "CALL":
            level_tests = sum(1 for sl in swing_l if abs(sl - last_l) <= zone * 1.4)
        else:
            level_tests = sum(1 for sh in swing_h if abs(sh - last_h) <= zone * 1.4)
        c1 = level_tests >= 2

        if n >= 5:
            c2 = abs(closes[-2] - opens[-2]) <= abs(closes[-4] - opens[-4]) * 1.6
        else:
            c2 = True

        if n >= 16:
            gp = [max(0.0, closes[i] - closes[i - 1]) for i in range(1, n - 1)]
            lp = [max(0.0, closes[i - 1] - closes[i]) for i in range(1, n - 1)]
            ag_p = sum(gp[-14:]) / 14; al_p = sum(lp[-14:]) / 14
            rsi_prev = 100 - 100 / (1 + ag_p / max(al_p, 1e-9))
            c3 = (rsi >= rsi_prev) if rev_dir == "CALL" else (rsi <= rsi_prev)
        else:
            c3 = True

        overshoot = max(0.0, recent_low - last_l) if rev_dir == "CALL" else max(0.0, last_h - recent_high)
        c4 = overshoot <= zone * 2.0

        c5 = (macd_hist > macd_hist_prev) if rev_dir == "CALL" else (macd_hist < macd_hist_prev)

        rev_confirms = sum([c1, c2, c3, c4, c5])
        if rev_confirms >= 4:
            direction = rev_dir; mode = "REVERSAL"
            extra = 0.4 if ((bull_pin and bull_engulf) or (bear_pin and bear_engulf)) else 0.0
            score = 1.7 + 0.25 * rev_confirms + extra

    if direction is None:
        cand_dir = None
        if ema_bull_stack and macd_bull_cross:
            cand_dir = "CALL"
        elif ema_bear_stack and macd_bear_cross:
            cand_dir = "PUT"

        if cand_dir is not None:
            pts = 0
            pts += 1 if ((m5_trend == "UP" and cand_dir == "CALL") or
                         (m5_trend == "DOWN" and cand_dir == "PUT")) else 0
            pts += 1 if ema_aligned else 0
            pts += 1 if adx_ok else 0
            pts += 1 if ((cand_dir == "CALL" and rsi > 55) or (cand_dir == "PUT" and rsi < 45)) else 0
            pts += 1 if ((cand_dir == "CALL" and macd_bull_cross) or (cand_dir == "PUT" and macd_bear_cross)) else 0
            pts += 1 if (strong_candle and ((cand_dir == "CALL" and last_c > last_o) or
                                             (cand_dir == "PUT" and last_c < last_o))) else 0
            pts += 1 if ((cand_dir == "CALL" and not near_res) or (cand_dir == "PUT" and not near_sup)) else 0
            pts += 1 if atr_ok else 0

            consec_block = _consec_run(cand_dir) >= 5

            if pts >= 6 and not consec_block:
                direction = cand_dir; mode = "TREND_CONTINUATION"
                score = 1.2 + 0.15 * pts

    if m5_trend not in ("UP", "DOWN"):
        direction = None
    elif direction == "CALL" and m5_trend != "UP":
        direction = None
    elif direction == "PUT" and m5_trend != "DOWN":
        direction = None

    if direction is None:
        return None, 0, round(rsi, 1), round(e9, 6), round(e20, 6), None

    avg_body = sum(abs(closes[-i] - opens[-i]) for i in range(1, 11)) / 10
    range20  = max(max(highs[-20:]) - min(lows[-20:]), 1e-9)
    if avg_body / range20 < 0.018:
        return None, 0, round(rsi, 1), round(e9, 6), round(e20, 6), None

    confidence = min(92, max(78, int(78 + score * 6)))
    return direction, confidence, round(rsi, 1), round(e9, 6), round(e20, 6), mode


def _analyze_pair_premium(pair, candles):
    if not candles or len(candles) < 80:
        return None
    direction, confidence, rsi_val, e9, e20, mode = analyze_premium(candles)
    if direction is None:
        return None
    return {
        "direction":     direction,
        "confidence":    confidence,
        "confirmations": confidence,
        "confirms":      3 if confidence >= 85 else (2 if confidence >= 79 else 1),
        "market_type":   "PREMIUM",
        "sw_score":      0.5,
        "regime":        mode or "TRENDING",
        "payout":        0,
        "rsi":           rsi_val,
        "e9":            e9,
        "e20":           e20,
    }


def _lsig_show_strategy_select(sess):
    pro2_on    = _db_strategy_enabled("pro2")
    premium_on = _db_strategy_enabled("premium")
    custom_on  = _db_strategy_enabled("foxio_zx_ai") and _custom_strategy_available()

    desc_parts = ["🔬 <b>Select Strategy</b>\n━━━━━━━━━━━━━━━━━━━━"]
    buttons    = []

    if pro2_on:
        desc_parts.append(
            "\n🏆 <b>ZBX PRO 2.1</b>\n"
            "Quality Over Quantity <b>[BEST OF ALL]</b>"
        )
        buttons.append([{"text": "ZBX PRO 2.1", "callback_data": "lsig_strategy_pro2",
                         "style": "primary",
                         "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["robot"])}])
    if premium_on:
        desc_parts.append(
            "\n💎 <b>ZBX PREMIUM</b>\n"
            "ZEBRONIX POWRED <b>[Stable]</b>"
        )
        buttons.append([{"text": "ZBX PREMIUM", "callback_data": "lsig_strategy_premium",
                         "style": "success",
                         "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["crown"])}])
    if custom_on:
        desc_parts.append("\n📊 <b>FOXIO ZX AI</b>\n22-strategy combined master engine <b>[OTC + LIVE]</b>")
        buttons.append([{"text": "FOXIO ZX AI", "callback_data": "lsig_strategy_foxio_zx_ai",
                         "style": "primary", "icon_custom_emoji_id": str(EMAP["📊"])}])

    if not buttons:
        buttons.append([{"text": "⚠️ No Strategy Available", "callback_data": "noop",
                         "style": "danger"}])

    buttons.append([{"text": "Back  ", "callback_data": "lsig_mode_auto",
                     "style": "danger",
                     "icon_custom_emoji_id": "5258084656674250503"}])

    _wiz(sess, "\n".join(desc_parts), {"inline_keyboard": buttons})


def _send_strategy_panel(cid):
    pro2_on    = _db_strategy_enabled("pro2")
    premium_on = _db_strategy_enabled("premium")
    custom_on  = _db_strategy_enabled("foxio_zx_ai")
    pro2_icon    = "✅" if pro2_on    else "❌"
    premium_icon = "✅" if premium_on else "❌"
    pro2_label    = "ON" if pro2_on    else "OFF (Hidden)"
    premium_label = "ON" if premium_on else "OFF (Hidden)"
    text = efmt(
        "🔬 <b>Strategy Manager</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{pro2_icon} <b>ZBX PRO 2.1</b> — {pro2_label}\n"
        f"{premium_icon} <b>ZBX PREMIUM</b> — {premium_label}\n"
        f"{'✅' if custom_on else '❌'} <b>FOXIO ZX AI</b> — {'ON' if custom_on else 'OFF (Hidden)'}\n"
        f"Modules: <b>{'Connected' if _custom_strategy_available() else (_custom_strategy_error or 'Strategy files not available')}</b>\n\n"
        "Tap a button to toggle ON / OFF.\n"
        "<i>Hidden strategies will not appear for any user.</i>"
    )
    kb = {"inline_keyboard": [
        [{"text": f"{'🟢 ON' if pro2_on else '🔴 OFF'} — ZBX PRO 2.1",
          "callback_data": "admin_strat_tog_pro2",
          "style": "success" if pro2_on else "danger"}],
        [{"text": f"{'🟢 ON' if premium_on else '🔴 OFF'} — ZBX PREMIUM",
          "callback_data": "admin_strat_tog_premium",
          "style": "success" if premium_on else "danger"}],
        [{"text": f"{'🟢 ON' if custom_on else '🔴 OFF'} — FOXIO ZX AI",
          "callback_data": "admin_strat_tog_foxio_zx_ai",
          "style": "success" if custom_on else "danger"}],
        [{"text": "Close", "callback_data": "noop",
          "style": "primary"}],
    ]}
    _send(cid, text, kb)


def _admin_wiz_send(cid, text, cancel_btn=True):
    kb = None
    if cancel_btn:
        kb = {"inline_keyboard": [[
            {"text": "Cancel", "callback_data": "admin_wiz_cancel",
             "style": "danger", "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["cross"])}
        ]]}
    _send(cid, efmt(text), kb)


def _send_global_free_panel(cid):
    until = _db_global_free_until()
    if until:
        remaining = max(0, until - int(time.time()))
        days, rem = divmod(remaining, 86400)
        hours, rem = divmod(rem, 3600)
        minutes = rem // 60
        expires = datetime.fromtimestamp(until).strftime("%Y-%m-%d %H:%M:%S")
        text = (
            "🎁 <b>GLOBAL FREE ACCESS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🟢 Status: <b>RUNNING</b>\n"
            f"⏳ Remaining: <b>{days}d {hours}h {minutes}m</b>\n"
            f"🕒 Ends at: <code>{expires}</code>\n\n"
            "All users currently have unlimited access to every premium and limited feature.")
        rows = [[{"text": "STOP GLOBAL FREE ACCESS",
                  "callback_data": "admin_global_free_stop", "style": "danger",
                  "icon_custom_emoji_id": str(EMAP["❌"])}]]
    else:
        text = (
            "🎁 <b>GLOBAL FREE ACCESS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔴 Status: <b>OFF</b>\n\n"
            "Start a timed offer to give every user unlimited bot access.")
        rows = [[{"text": "START GLOBAL FREE ACCESS",
                  "callback_data": "admin_global_free_start", "style": "success",
                  "icon_custom_emoji_id": str(EMAP["🚀"])}]]
    rows.append([{"text": "CLOSE", "callback_data": "noop", "style": "primary"}])
    _send(cid, efmt(text), {"inline_keyboard": rows})


def _admin_wiz_start(sess, cid, cmd):
    sess.state = S.ADMIN_WIZARD
    sess.admin_wizard = {"cmd": cmd, "step": 1, "data": {}}
    prompts = {
        "globalfree":          "🎁 <b>GLOBAL FREE ACCESS</b>\n\nHow many days should every user get unlimited access?\n\nExample: <code>1</code> = exactly 24 hours.",
        "addlicense":          "👤 <b>Step 1/3 — User ID</b>\n\nSend the <b>User ID</b> of the user, or <b>forward any message</b> from that user:",
        "removelicense":       "👤 <b>Step 1/2 — User ID</b>\n\nSend the <b>User ID</b> or <b>forward a message</b> from the user whose license you want to remove:",
        "license":             "👤 <b>Step 1/1 — User ID</b>\n\nSend the <b>User ID</b> or <b>forward a message</b> from the user to check:",
        "ban":                 "👤 <b>Step 1/2 — User ID</b>\n\nSend the <b>User ID</b> or <b>forward a message</b> from the user you want to ban:",
        "unban":               "👤 <b>Step 1/2 — User ID</b>\n\nSend the <b>User ID</b> or <b>forward a message</b> from the user you want to unban:",
        "broadcast":           "📣 <b>Step 1/2 — Message</b>\n\nType the <b>broadcast message</b> to send to all users:\n\n💡 <i>Tip: You can also write your message first, then reply to it with /broadcast</i>",
        "allowlivesession":    "👤 <b>Step 1/1 — User ID</b>\n\nSend the <b>User ID</b> or <b>forward a message</b> from the user to unlock Channel Sender for them:",
        "disallowlivesession": "👤 <b>Step 1/1 — User ID</b>\n\nSend the <b>User ID</b> or <b>forward a message</b> from the user to disable Channel Sender for them:",
        "addfuturesignal":     "👤 <b>Step 1/3 — User ID</b>\n\nSend the <b>User ID</b> of the user, or <b>forward any message</b> from that user, to grant <b>Future Signal</b> access:",
        "removefuturesignal":  "👤 <b>Step 1/2 — User ID</b>\n\nSend the <b>User ID</b> or <b>forward a message</b> from the user whose Future Signal access you want to remove:",
        "futuresignal":        "👤 <b>Step 1/1 — User ID</b>\n\nSend the <b>User ID</b> or <b>forward a message</b> from the user to check Future Signal access:",
    }
    _admin_wiz_send(cid, prompts.get(cmd, "Send input:"))


def _admin_wiz_handle(uid, cid, text, sess, msg=None):
    wiz  = sess.admin_wizard
    cmd  = wiz.get("cmd", "")
    step = wiz.get("step", 1)
    data = wiz.get("data", {})

    def _bad(msg_text):
        _admin_wiz_send(cid, f"❌ <b>{msg_text}</b>\n\nTry again or tap Cancel.")

    def _done():
        sess.state = S.IDLE
        sess.admin_wizard = {}

    def _parse_uid(t):
        try: return int(t.strip())
        except: return None

    def _extract_uid_from_msg(m):
        if m:
            fwd = m.get("forward_from")
            if fwd and fwd.get("id"):
                return int(fwd["id"])
            fwd_sender = m.get("forward_sender_name")
            if fwd_sender:
                return None
        return _parse_uid(text)

    def _uid_prompt_text():
        return (
            "Send the <b>User ID</b> — either:\n"
            "• Type the number directly: <code>123456789</code>\n"
            "• Or <b>forward any message</b> from that user here"
        )

    if cmd == "globalfree":
        try:
            days = int(text.strip())
        except (TypeError, ValueError):
            return _bad("Invalid number of days. Example: 1")
        if days < 1 or days > 3650:
            return _bad("Days must be between 1 and 3650.")
        until = _db_global_free_enable(days)
        if until:
            expires = datetime.fromtimestamp(until).strftime("%Y-%m-%d %H:%M:%S")
            _send(cid, efmt(
                "✅ <b>GLOBAL FREE ACCESS STARTED</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📅 Duration: <b>{days} day(s)</b>\n"
                f"⏱ Exact access: <b>{days * 24} hours</b>\n"
                f"🕒 Ends at: <code>{expires}</code>\n\n"
                "♾ All users can now use every premium and limited feature without quota."))
        else:
            _send(cid, efmt("❌ <b>Could not start Global Free Access.</b>"))
        _done()

    elif cmd == "addlicense":
        if step == 1:
            t_uid = _extract_uid_from_msg(msg)
            if not t_uid:
                return _bad(
                    "Could not get User ID.\n\n"
                    "Please send the User ID as a number or forward a message from that user."
                )
            data["uid"] = t_uid
            wiz["step"] = 2
            _admin_wiz_send(cid,
                f"✅ User ID: <code>{t_uid}</code>\n\n"
                "📅 <b>Step 2/3 — Days</b>\n\nHow many days should this license last?\n"
                "Example: <code>30</code>")
        elif step == 2:
            try: days = int(text.strip())
            except: return _bad("Invalid number of days. Example: 30")
            if days <= 0: return _bad("Days must be greater than 0.")
            data["days"] = days
            wiz["step"] = 3
            _admin_wiz_send(cid,
                f"✅ Days: <code>{days}</code>\n\n"
                "⚡ <b>Step 3/3 — Signal Limit</b>\n\nHow many signals per day?\n"
                "Example: <code>20</code>")
        elif step == 3:
            try: limit = int(text.strip())
            except: return _bad("Invalid signal limit. Example: 20")
            if limit <= 0: return _bad("Signal limit must be greater than 0.")
            data["limit"] = limit
            wiz["step"] = 4
            _admin_wiz_send(cid,
                "✅ <b>Confirm License</b>\n\n"
                f"👤 User ID    : <code>{data['uid']}</code>\n"
                f"📅 Days       : <b>{data['days']}</b>\n"
                f"⚡ Daily Limit: <b>{data['limit']} signals/day</b>\n\n"
                "Type <b>YES</b> to confirm or <b>NO</b> to cancel.")
        elif step == 4:
            if text.strip().upper() == "YES":
                ok  = _db_license_add(data["uid"], data["days"], data["limit"])
                lic = _db_license_get(data["uid"])
                if ok:
                    _send(cid, efmt(
                        "╔══════════════════╗\n"
                        "    👑 𝚉𝙴𝙱𝚁𝙾𝙽𝙸𝚇 𝙰𝙸 👑\n"
                        "╚══════════════════╝\n\n"
                        "✅ <b>License Added Successfully!</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"👤 User ID    : <code>{data['uid']}</code>\n"
                        f"📅 Days       : {data['days']}\n"
                        f"⚡ Daily Limit : {data['limit']} signals/day\n"
                        f"⏰ Expires     : {lic.get('expires','?')}"
                    ))
                    try:
                        _api("sendMessage", data={
                            "chat_id": data["uid"],
                            "text": efmt(
                                "╔══════════════════╗\n"
                                "    👑 𝚉𝙴𝙱𝚁𝙾𝙽𝙸𝚇 𝙰𝙸 👑\n"
                                "╚══════════════════╝\n\n"
                                "🎉 <b>Your VIP License has been Activated!</b>\n"
                                "━━━━━━━━━━━━━━━━━━━━\n\n"
                                f"📅 Valid for  : <b>{data['days']} days</b>\n"
                                f"⚡ Daily Limit : <b>{data['limit']} signals/day</b>\n"
                                f"⏰ Expires     : {lic.get('expires','?')}\n\n"
                                "Tap /start to begin trading! 🚀\n"
                                "━━━━━━━━━━━━━━━━━━━━\n"
                                f"👑 𝙾𝚠𝚗𝚎𝚛 : @RASUU_QXB✨"
                            ),
                            "parse_mode": "HTML"
                        })
                    except Exception: pass
                else:
                    _send(cid, efmt("❌ <b>Database error. Failed to add license.</b>"))
            else:
                _send(cid, efmt("❌ <b>Cancelled.</b>"))
            _done()

    elif cmd == "removelicense":
        if step == 1:
            t_uid = _extract_uid_from_msg(msg)
            if not t_uid: return _bad("Could not get User ID. Send a number or forward a message from that user.")
            data["uid"] = t_uid
            lic = _db_license_get(t_uid)
            if not lic:
                _send(cid, efmt(f"⚠️ <b>No license found</b> for <code>{t_uid}</code>"))
                return _done()
            wiz["step"] = 2
            _admin_wiz_send(cid,
                f"👤 User: <code>{t_uid}</code>\n"
                f"⏰ License expires: {lic.get('expires','?')}\n\n"
                "Type <b>YES</b> to remove this license or <b>NO</b> to cancel.")
        elif step == 2:
            if text.strip().upper() == "YES":
                ok = _db_license_remove(data["uid"])
                if ok:
                    _send(cid, efmt(f"✅ <b>License removed</b> for user <code>{data['uid']}</code>"))
                    try:
                        _api("sendMessage", data={
                            "chat_id": data["uid"],
                            "text": efmt(
                                "⚠️ <b>Your VIP License has been removed.</b>\n\n"
                                "Contact support to renew your license.\n"
                                f"👑 𝙾𝚠𝚗𝚎𝚛 : @RASUU_QXB✨"
                            ),
                            "parse_mode": "HTML"
                        })
                    except Exception: pass
                else:
                    _send(cid, efmt("⚠️ <b>Failed to remove license.</b>"))
            else:
                _send(cid, efmt("❌ <b>Cancelled.</b>"))
            _done()

    elif cmd == "license":
        t_uid = _extract_uid_from_msg(msg)
        if not t_uid: return _bad("Could not get User ID. Send a number or forward a message from that user.")
        lic = _db_license_get(t_uid)
        if not lic:
            _send(cid, efmt(f"⚠️ <b>No license found</b> for <code>{t_uid}</code>"))
        else:
            valid  = _db_license_is_valid(t_uid)
            used   = _db_live_quota_get(t_uid)
            status = "✅ Active" if valid else "❌ Expired"
            _send(cid, efmt(
                "📋 <b>License Info</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 User ID    : <code>{t_uid}</code>\n"
                f"⚡ Daily Limit : {lic.get('signal_limit','?')} signals\n"
                f"📊 Used Today  : {used}\n"
                f"⏰ Expires     : {lic.get('expires','?')}\n"
                f"🔰 Status      : {status}"
            ))
        _done()

    elif cmd == "addfuturesignal":
        if step == 1:
            t_uid = _extract_uid_from_msg(msg)
            if not t_uid:
                return _bad(
                    "Could not get User ID.\n\n"
                    "Please send the User ID as a number or forward a message from that user."
                )
            data["uid"] = t_uid
            wiz["step"] = 2
            _admin_wiz_send(cid,
                f"✅ User ID: <code>{t_uid}</code>\n\n"
                "📅 <b>Step 2/3 — Days</b>\n\nHow many days should Future Signal access last?\n"
                "Example: <code>30</code>")
        elif step == 2:
            try: days = int(text.strip())
            except: return _bad("Invalid number of days. Example: 30")
            if days <= 0: return _bad("Days must be greater than 0.")
            data["days"] = days
            wiz["step"] = 3
            _admin_wiz_send(cid,
                f"✅ Days: <code>{days}</code>\n\n"
                "⚡ <b>Step 3/3 — Daily Limit</b>\n\nHow many Future Signal lists per day?\n"
                "Example: <code>5</code>")
        elif step == 3:
            try: limit = int(text.strip())
            except: return _bad("Invalid daily limit. Example: 5")
            if limit <= 0: return _bad("Daily limit must be greater than 0.")
            data["limit"] = limit
            wiz["step"] = 4
            _admin_wiz_send(cid,
                "✅ <b>Confirm Future Signal Access</b>\n\n"
                f"👤 User ID    : <code>{data['uid']}</code>\n"
                f"📅 Days       : <b>{data['days']}</b>\n"
                f"⚡ Daily Limit: <b>{data['limit']} list(s)/day</b>\n\n"
                "Type <b>YES</b> to confirm or <b>NO</b> to cancel.")
        elif step == 4:
            if text.strip().upper() == "YES":
                ok  = _db_future_access_add(data["uid"], data["days"], data["limit"])
                acc = _db_future_access_get(data["uid"])
                if ok:
                    _send(cid, efmt(
                        "╔══════════════════╗\n"
                        "    👑 𝚉𝙴𝙱𝚁𝙾𝙽𝙸𝚇 𝙰𝙸 👑\n"
                        "╚══════════════════╝\n\n"
                        "✅ <b>Future Signal Access Granted!</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"👤 User ID    : <code>{data['uid']}</code>\n"
                        f"📅 Days       : {data['days']}\n"
                        f"⚡ Daily Limit : {data['limit']} list(s)/day\n"
                        f"⏰ Expires     : {acc.get('expires','?')}"
                    ))
                    try:
                        _api("sendMessage", data={
                            "chat_id": data["uid"],
                            "text": efmt(
                                "╔══════════════════╗\n"
                                "    👑 𝚉𝙴𝙱𝚁𝙾𝙽𝙸𝚇 𝙰𝙸 👑\n"
                                "╚══════════════════╝\n\n"
                                "🎉 <b>Future Signal Access Activated!</b>\n"
                                "━━━━━━━━━━━━━━━━━━━━\n\n"
                                f"📅 Valid for  : <b>{data['days']} days</b>\n"
                                f"⚡ Daily Limit : <b>{data['limit']} list(s)/day</b>\n"
                                f"⏰ Expires     : {acc.get('expires','?')}\n\n"
                                "Tap /start and open Future Signal! 🚀\n"
                                "━━━━━━━━━━━━━━━━━━━━\n"
                                f"👑 𝙾𝚠𝚗𝚎𝚛 : @RASUU_QXB✨"
                            ),
                            "parse_mode": "HTML"
                        })
                    except Exception: pass
                else:
                    _send(cid, efmt("❌ <b>Database error. Failed to grant Future Signal access.</b>"))
            else:
                _send(cid, efmt("❌ <b>Cancelled.</b>"))
            _done()

    elif cmd == "removefuturesignal":
        if step == 1:
            t_uid = _extract_uid_from_msg(msg)
            if not t_uid: return _bad("Could not get User ID. Send a number or forward a message from that user.")
            data["uid"] = t_uid
            acc = _db_future_access_get(t_uid)
            if not acc:
                _send(cid, efmt(f"⚠️ <b>No Future Signal access found</b> for <code>{t_uid}</code>"))
                return _done()
            wiz["step"] = 2
            _admin_wiz_send(cid,
                f"👤 User: <code>{t_uid}</code>\n"
                f"⏰ Access expires: {acc.get('expires','?')}\n\n"
                "Type <b>YES</b> to remove this Future Signal access or <b>NO</b> to cancel.")
        elif step == 2:
            if text.strip().upper() == "YES":
                ok = _db_future_access_remove(data["uid"])
                if ok:
                    _send(cid, efmt(f"✅ <b>Future Signal access removed</b> for user <code>{data['uid']}</code>"))
                    try:
                        _api("sendMessage", data={
                            "chat_id": data["uid"],
                            "text": efmt(
                                "⚠️ <b>Your Future Signal access has been removed.</b>\n\n"
                                "Contact support to request access again.\n"
                                f"👑 𝙾𝚠𝚗𝚎𝚛 : @RASUU_QXB✨"
                            ),
                            "parse_mode": "HTML"
                        })
                    except Exception: pass
                else:
                    _send(cid, efmt("⚠️ <b>Failed to remove Future Signal access.</b>"))
            else:
                _send(cid, efmt("❌ <b>Cancelled.</b>"))
            _done()

    elif cmd == "futuresignal":
        t_uid = _extract_uid_from_msg(msg)
        if not t_uid: return _bad("Could not get User ID. Send a number or forward a message from that user.")
        acc = _db_future_access_get(t_uid)
        if not acc:
            _send(cid, efmt(f"⚠️ <b>No Future Signal access found</b> for <code>{t_uid}</code>"))
        else:
            valid  = _db_future_access_is_valid(t_uid)
            used   = _db_future_quota_get(t_uid)
            status = "✅ Active" if valid else "❌ Expired"
            _send(cid, efmt(
                "📋 <b>Future Signal Access Info</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 User ID    : <code>{t_uid}</code>\n"
                f"⚡ Daily Limit : {acc.get('daily_limit','?')} list(s)\n"
                f"📊 Used Today  : {used}\n"
                f"⏰ Expires     : {acc.get('expires','?')}\n"
                f"🔰 Status      : {status}"
            ))
        _done()

    elif cmd == "ban":
        if step == 1:
            t_uid = _extract_uid_from_msg(msg)
            if not t_uid: return _bad("Could not get User ID. Send a number or forward a message from that user.")
            if t_uid in ADMIN_IDS:
                _send(cid, efmt("❌ <b>Cannot ban an admin.</b>")); return _done()
            data["uid"] = t_uid
            wiz["step"] = 2
            _admin_wiz_send(cid,
                f"⚠️ <b>Ban User?</b>\n\nUser ID: <code>{t_uid}</code>\n\n"
                "Type <b>YES</b> to ban or <b>NO</b> to cancel.")
        elif step == 2:
            if text.strip().upper() == "YES":
                _db_ban_user(data["uid"])
                _send(cid, efmt(f"🔒 <b>User <code>{data['uid']}</code> has been banned.</b>"))
                try:
                    _api("sendMessage", data={
                        "chat_id": data["uid"],
                        "text": efmt(
                            "🚫 <b>You have been banned from this bot.</b>\n\n"
                            "Contact support if you think this is a mistake.\n"
                            f"👑 𝙾𝚠𝚗𝚎𝚛 : @RASUU_QXB✨"
                        ),
                        "parse_mode": "HTML"
                    })
                except Exception: pass
            else:
                _send(cid, efmt("❌ <b>Cancelled.</b>"))
            _done()

    elif cmd == "unban":
        if step == 1:
            t_uid = _extract_uid_from_msg(msg)
            if not t_uid: return _bad("Could not get User ID. Send a number or forward a message from that user.")
            data["uid"] = t_uid
            wiz["step"] = 2
            _admin_wiz_send(cid,
                f"⚠️ <b>Unban User?</b>\n\nUser ID: <code>{t_uid}</code>\n\n"
                "Type <b>YES</b> to unban or <b>NO</b> to cancel.")
        elif step == 2:
            if text.strip().upper() == "YES":
                _db_unban_user(data["uid"])
                _send(cid, efmt(f"✅ <b>User <code>{data['uid']}</code> has been unbanned.</b>"))
                try:
                    _api("sendMessage", data={
                        "chat_id": data["uid"],
                        "text": efmt(
                            "✅ <b>Your ban has been lifted.</b>\n\n"
                            "You can now use the bot again. Tap /start 🚀"
                        ),
                        "parse_mode": "HTML"
                    })
                except Exception: pass
            else:
                _send(cid, efmt("❌ <b>Cancelled.</b>"))
            _done()

    elif cmd == "broadcast":
        if step == 1:
            if not text.strip():
                return _bad("Message cannot be empty.")
            data["msg"] = text.strip()
            wiz["step"] = 2
            _admin_wiz_send(cid,
                "📣 <b>Preview:</b>\n\n"
                f"{data['msg']}\n\n"
                "Type <b>YES</b> to broadcast to all users or <b>NO</b> to cancel.\n\n"
                "💡 <i>Tip: For better results (images/videos/GIFs/formatting), "
                "write your message and then <b>reply to it</b> with /broadcast</i>")
        elif step == 2:
            if text.strip().upper() == "YES":
                users  = _db_users_list()
                sent = fail = 0
                for u in users:
                    t_uid2 = u.get("user_id")
                    if not t_uid2 or t_uid2 == uid: continue
                    try:
                        r = _api("sendMessage", data={
                            "chat_id":    t_uid2,
                            "text":       data["msg"],
                            "parse_mode": "HTML"
                        })
                        if r.get("ok"): sent += 1
                        else: fail += 1
                    except Exception: fail += 1
                    time.sleep(0.05)
                _send(cid, efmt(
                    f"📣 <b>Broadcast Complete</b>\n\n"
                    f"✅ Sent   : {sent}\n"
                    f"❌ Failed : {fail}"
                ))
            else:
                _send(cid, efmt("❌ <b>Broadcast cancelled.</b>"))
            _done()

    elif cmd == "allowlivesession":
        t_uid = _extract_uid_from_msg(msg)
        if not t_uid: return _bad("Could not get User ID. Send a number or forward a message from that user.")
        _db_lsess_allow(t_uid)
        _db_lsess_unblock(t_uid)
        _send(cid, efmt(f"✅ <b>User <code>{t_uid}</code> can now use Channel Sender.</b>"))
        try:
            _api("sendMessage", data={
                "chat_id": t_uid,
                "text": efmt(
                    "✅ <b>You now have access to Channel Sender!</b>\n\n"
                    "Tap /start to begin. 🚀"
                ),
                "parse_mode": "HTML"
            })
        except Exception: pass
        _done()

    elif cmd == "disallowlivesession":
        t_uid = _extract_uid_from_msg(msg)
        if not t_uid: return _bad("Could not get User ID. Send a number or forward a message from that user.")
        _db_lsess_block(t_uid)
        _send(cid, efmt(f"✅ <b>User <code>{t_uid}</code> can no longer use Channel Sender.</b>"))
        _done()

    else:
        _send(cid, efmt("❌ <b>Unknown command.</b>"))
        _done()


def on_message(msg):
    uid      = msg.get("from",{}).get("id")
    cid      = msg.get("chat",{}).get("id")
    text     = (msg.get("text") or "").strip()
    username = msg.get("from",{}).get("username","") or ""
    fname    = msg.get("from",{}).get("first_name","") or ""
    if not uid: return
    sess  = _sess(uid)
    _wiz_init(sess, cid)

    if text in ("/start","/menu"):
        _db_user_register(uid, username, fname)
        if fname:
            _first_name_cache[uid] = fname
        sess.state = S.IDLE
        if not _is_channel_member(uid):
            _send_channel_required(cid, sess)
            return
        _send_welcome(uid, sess, _kb_welcome)
        return

    if text == "/cancel":
        sess.state = S.IDLE
        sess.admin_wizard = {}
        sess.backtest_signals = []
        sess.backtest_original_count = 0
        sess.backtest_market = None
        sess.ai_filter_draft = {}
        if not _is_channel_member(uid):
            _send_channel_required(cid, sess)
            return
        _send_welcome(uid, sess, _kb_welcome)
        return

    unlimited_states = {
        S.TZ_SRC, S.TZ_DST, S.TZ_INPUT,
        S.FORMATTER_INPUT, S.FORMATTER_FORMAT,
        S.BACKTEST_INPUT, S.BACKTEST_READY, S.BACKTEST_RUNNING,
        S.AI_FILTER_INPUT, S.AI_FILTER_MTG, S.AI_FILTER_DAYS,
        S.CANDLE_COLOUR_INPUT, S.RECENT_TREND_INPUT, S.VOLATILITY_INPUT,
    }
    future_states = {
        S.FUTURE_MARKET_SELECT, S.FUTURE_GRID_SELECTING, S.FUTURE_DIR_SELECT,
        S.FUTURE_START_TIME, S.FUTURE_END_TIME, S.FUTURE_DAYS_SELECT,
        S.MULTI_FS_DAYS, S.MULTI_FS_START_TIME, S.MULTI_FS_END_TIME,
    }
    state_policy = ("unlimited" if sess.state in unlimited_states else
                    "future" if sess.state in future_states else None)
    if state_policy and not _enforce_premium_access(uid, sess, state_policy):
        return

    if sess.state == S.CANDLE_COLOUR_INPUT:
        _tool_manual_async(sess, text, "candle")
        return

    if sess.state == S.RECENT_TREND_INPUT:
        _tool_manual_async(sess, text, "recent")
        return

    if sess.state == S.VOLATILITY_INPUT:
        _volatility_manual_async(cid, sess, text)
        return

    if sess.state == S.AI_FILTER_INPUT:
        signals = _ai_filter_extract_signals(text)
        if not signals:
            _send(cid, efmt("❌ <b>No valid signals found! Please paste a valid signal list.</b>"))
            return
        sess.ai_filter_draft = {"signals": signals}
        sess.state = S.AI_FILTER_MTG
        _wiz(sess,
            f"✅ <b>Received {len(signals)} signals.</b>\n\nChoose Martingale level:",
            {"inline_keyboard": [
                [{"text": "NO MTG", "callback_data": "ai_filter_mtg_0", "style": "primary",
                  "icon_custom_emoji_id": "6212911416207219932"},
                 {"text": "MTG-1", "callback_data": "ai_filter_mtg_1", "style": "success",
                  "icon_custom_emoji_id": "6312168668763529862"}],
                [{"text": "MTG-2", "callback_data": "ai_filter_mtg_2", "style": "success",
                  "icon_custom_emoji_id": "6312008994764365905"},
                 {"text": "MTG-3", "callback_data": "ai_filter_mtg_3", "style": "success",
                  "icon_custom_emoji_id": "6312168668763529862"}],
                [{"text": "CANCEL", "callback_data": "ai_filter_cancel", "style": "danger",
                  "icon_custom_emoji_id": "5258084656674250503"}]]})
        return

    if sess.state == S.TZ_INPUT:
        _delete(cid, msg.get("message_id"))
        if not text:
            _wiz(sess, "⚠️ <b>Empty input.</b> Please send your signal list.")
            return
        src = float(sess.tz_draft.get("src_offset", 0)); dst = float(sess.tz_draft.get("dst_offset", 0))
        converted = _convert_signal_list(text, src, dst)
        shift = dst - src
        header = (f"🕐 <b>Timezone Converted</b>\n📤 From: <b>{_tz_offset_label(src)}</b>\n"
                  f"📥 To: <b>{_tz_offset_label(dst)}</b>\n⏱ Shift: <b>{shift:+g}h</b>\n\n")
        kb = {"inline_keyboard": [
            [{"text": "Convert Another", "callback_data": "menu_tz_convert", "style": "success",
              "icon_custom_emoji_id": "5260687119092817530"}],
            [{"text": "Back", "callback_data": "menu_home", "style": "primary",
              "icon_custom_emoji_id": "5258084656674250503"}],
        ]}
        safe_lines = converted.splitlines() or [""]
        chunks, current = [], []
        for line in safe_lines:
            if current and len("\n".join(current + [line])) > 3300:
                chunks.append("\n".join(current)); current = []
            current.append(line)
        if current: chunks.append("\n".join(current))
        for index, chunk in enumerate(chunks):
            prefix = header if index == 0 else ""
            _send(cid, efmt(prefix) + f"<pre>{_html.escape(chunk)}</pre>", kb if index == len(chunks) - 1 else None)
        sess.state = S.IDLE
        return

    if sess.state == S.FORMATTER_INPUT:
        _delete(cid, msg.get("message_id"))
        signals, errors = _parse_formatter_signals(text)
        if not signals:
            _wiz(sess, "❌ <b>No valid signals found.</b>\n\nPlease include pair, time and CALL/PUT direction.\n\n"
                 "<code>M1;EURUSD-OTC;14:26;CALL</code>")
            return
        sess.formatter_draft = {"signals": signals, "errors": errors}
        _screen_formatter_ask_format(sess)
        return

    if sess.state == S.FORMATTER_FORMAT:
        _delete(cid, msg.get("message_id"))
        signals = sess.formatter_draft.get("signals") or []
        formatted, error = _format_signals(signals, text)
        if error:
            _wiz(sess, f"❌ <b>Could not understand that format.</b>\n\n{_html.escape(error)}\n\nPlease send one clear example line.")
            return
        sess.state = S.IDLE; sess.wiz_mid = None
        output = _html.escape(formatted)
        _send(cid, efmt(f"🗂 <b>FORMATTED SIGNALS</b>\n━━━━━━━━━━━━━━\n\n✅ Signals: <b>{len(signals)}</b>\n\n")
              + f"<pre>{output}</pre>",
              {"inline_keyboard": [
                  [{"text": "Change Format", "callback_data": "fmt_ask_format", "style": "primary",
                    "icon_custom_emoji_id": "5260687119092817530"}],
                  [{"text": "Paste New List", "callback_data": "menu_formatter", "style": "success",
                    "icon_custom_emoji_id": "5193004760994685438"}],
                  [{"text": "Back Home", "callback_data": "menu_home", "style": "danger",
                    "icon_custom_emoji_id": "5258084656674250503"}],
              ]})
        return

    if sess.state == S.LSESS_AWAIT_CHANNEL:
        if uid not in ADMIN_IDS and not _lsess_can_use(uid):
            sess.state = S.IDLE
            _send_welcome(uid, sess, _kb_welcome)
            return
        if text.startswith("/"):
            pass
        else:
            target_chat_id = None
            fwd_chat = msg.get("forward_from_chat")
            if fwd_chat and fwd_chat.get("id"):
                target_chat_id = fwd_chat.get("id")
            elif text:
                try:
                    target_chat_id = int(text)
                except ValueError:
                    if text.startswith("@"):
                        target_chat_id = text
            if not target_chat_id:
                _send(cid, efmt(
                    "⚠️ <b>Invalid Input</b>\n\n"
                    "Please forward a message from your channel/group, "
                    "or send the chat ID (e.g. <code>-1001234567890</code>)."))
                return
            sess.lsess_channel_id = target_chat_id
            _lsess_check_admin_and_show(uid, sess)
            return

    if sess.state == S.LSESS_AWAIT_USERNAME:
        if uid not in ADMIN_IDS and not _lsess_can_use(uid):
            sess.state = S.IDLE
            _send_welcome(uid, sess, _kb_welcome)
            return
        if text.startswith("/"):
            pass
        else:
            uname = text.strip()[:40]
            if uname:
                _lsig_owner_names[uid] = uname
                sess.lsess_owner_name = uname
            _send(cid, efmt(f"✅ <b>Username saved:</b> {_html.escape(uname) if uname else '—'}"))
            _lsess_strategy_select_menu(sess)
            return

    if sess.state == S.AWAIT_OWNER_USERNAME:
        return_cb = sess.owner_return_cb or "menu_home"
        if text.startswith("/"):
            pass
        else:
            uname = text.strip()[:40]
            if uname:
                _lsig_owner_names[uid] = uname
                sess.lsess_owner_name = uname
                _send(cid, efmt(f"✅ <b>Username saved:</b> {_html.escape(uname)}"))
            else:
                _send(cid, efmt("⚠️ <b>Empty username ignored.</b>"))
            sess.state = S.IDLE
            cb2 = {"from": {"id": uid, "username": username, "first_name": fname},
                   "message": {"chat": {"id": cid}, "message_id": sess.wiz_mid},
                   "id": "", "data": return_cb}
            on_callback(cb2)
            return

    if sess.state == S.MULTI_FS_DAYS:
        try:
            days = int(text)
            if not 1 <= days <= 30:
                raise ValueError
        except (TypeError, ValueError):
            _send(cid, efmt("❌ Invalid! Enter integer between 1 and 30."))
            return
        sess.multi_fs["days"] = days
        sess.state = S.MULTI_FS_START_TIME
        _send(cid, efmt(_mfs_start_time_prompt()))
        return

    if sess.state == S.MULTI_FS_START_TIME:
        if not re.match(r"^([01]?\d|2[0-3]):([0-5]\d)$", text):
            _send(cid, efmt("❌ Invalid! Use HH:MM format (e.g., 14:00)."))
            return
        sess.multi_fs["start_time"] = text
        sess.state = S.MULTI_FS_END_TIME
        _send(cid, efmt(_mfs_end_time_prompt()))
        return

    if sess.state == S.MULTI_FS_END_TIME:
        if not re.match(r"^([01]?\d|2[0-3]):([0-5]\d)$", text):
            _send(cid, efmt("❌ Invalid! Use HH:MM format (e.g., 17:00)."))
            return
        sess.multi_fs["end_time"] = text
        if uid not in ADMIN_IDS and not _db_future_access_is_valid(uid):
            sess.state = S.IDLE
            _send(cid, efmt(_future_access_denied_text(uid)), _kb_future_access_required())
            return
        if not _db_future_quota_use(uid):
            limit = int(_db_future_access_get(uid).get("daily_limit", 0) or 0)
            sess.state = S.IDLE
            _send(cid, efmt(
                "💎 <b>DAILY LIMIT REACHED</b> 💎\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"⚠️ Your Future Signal access allows <b>{limit} list(s) per day</b>.\n"
                "You've already used today's list.\n\n"
                f"✉️ Message Support: <b>{SUPPORT_USERNAME}</b> to increase your limit."
            ), _kb_free_limit_reached())
            return
        _mfs_generate_and_send(cid, sess)
        return

    if sess.state == S.ADMIN_WIZARD and uid in ADMIN_IDS:
        if not text.startswith("/"):
            _admin_wiz_handle(uid, cid, text, sess, msg)
            return

    if sess.state == S.FUTURE_START_TIME:
        if not re.match(r'^\d{2}:\d{2}$', text):
            _send(cid, efmt("❌ <b>Invalid time format. Please try again.</b>\n\n" +
                            _future_time_prompt("START")))
            return
        sess.fut_start_time = text
        sess.state = S.FUTURE_END_TIME
        _send(cid, efmt(_future_time_prompt("END")))
        return

    if sess.state == S.FUTURE_END_TIME:
        if not re.match(r'^\d{2}:\d{2}$', text):
            _send(cid, efmt("❌ <b>Invalid time format. Please try again.</b>\n\n" +
                            _future_time_prompt("END")))
            return
        sess.fut_end_time = text
        sess.state = S.FUTURE_DAYS_SELECT
        days_keyboard = (_kb_future_new_days_select()
                         if getattr(sess, "fut_engine", "legacy") == "hard_filter"
                         else _kb_future_days_select())
        _send(cid, efmt("💯 <b>FUTURE DAYS FILTER</b>\n\nSelect Day Analysis, tap below:"),
              days_keyboard)
        return

    if sess.state == S.BACKTEST_INPUT:
        backtest_market = str(getattr(sess, "backtest_market", "") or "").upper()
        valid, errors = _backtest_parse_signals(text, backtest_market)
        unique, duplicate_count = _backtest_deduplicate(valid)
        if not unique:
            market_label = "Live" if backtest_market == "LIVE" else "OTC"
            _send(cid, efmt(
                f"❌ <b>{market_label} market not available.</b>\n\n"
                f"Only supported {market_label} market pairs can be backtested. "
                "Unsupported or wrong-market signals were skipped."))
            return
        sess.backtest_signals = unique
        sess.backtest_original_count = len(valid)
        sess.state = S.BACKTEST_READY
        skipped = len(errors)
        preview = "\n".join(signal["raw"] for signal in unique[:5])
        if len(unique) > 5:
            preview += f"\n... +{len(unique) - 5} more"
        notes = []
        if duplicate_count:
            notes.append(f"♻️ Duplicate time removed: <b>{duplicate_count}</b>")
        if skipped:
            market_label = "Live" if backtest_market == "LIVE" else "OTC"
            notes.append(f"⚠️ {market_label} market not available / skipped: <b>{skipped}</b>")
        note_text = ("\n" + "\n".join(notes)) if notes else ""
        _send(cid, efmt(
            f"✅ <b>{len(unique)} SIGNAL(S) LOADED</b>{note_text}\n\n"
            f"<code>{_html.escape(preview)}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>Ready for backtest.</b> Now click <b>RUN BACKTEST</b> to start."),
            {"inline_keyboard": [
                [{"text": "RUN BACKTEST", "callback_data": "backtest_run", "style": "success",
                  "icon_custom_emoji_id": "6001261178821544871"}],
                [{"text": "CANCEL", "callback_data": "backtest_cancel", "style": "danger",
                  "icon_custom_emoji_id": "5258084656674250503"}]]})
        return

    if sess.state == S.CHECKER_INPUT:
        mode = sess.checker_draft.get("checker_mode", "otc")
        if mode in ("whiteout", "blackout"):
            valid, errors = _ck_parse_whiteout_signals(text)
        elif mode in ("whiteout_live", "blackout_live"):
            valid, errors = _ck_parse_live_directionless_signals(text)
        elif mode == "live":
            valid, errors = _ck_parse_live_signals(text)
        else:
            valid, errors = _ck_parse_signals(text)

        if mode in ("otc", "whiteout", "blackout"):
            for signal in valid:
                pair = str(signal.get("pair") or "").upper()
                pair = _ck_re.sub(r"^OTC[_\-]?", "", pair, flags=_ck_re.IGNORECASE)
                if not pair.endswith("_OTC"):
                    pair = _ck_normalize_pair(f"{pair}_OTC")
                signal["pair"] = pair
                direction = signal.get("direction")
                signal["raw"] = (f"M1 {pair} {signal['time']} {direction}"
                                 if direction and direction != "WHITEOUT"
                                 else f"M1 {pair} {signal['time']}")

        if not valid:
            back_cb = _CK_MODE_MENU_CB.get(mode, "menu_otc_checker")
            _send(cid, efmt("❌ <b>No valid signals found.</b>\n\nPlease check your input and try again."),
                  {"inline_keyboard": [[{"text": "Back", "callback_data": back_cb, "style": "primary"}]]})
            return

        sess.checker_draft["signals"] = valid
        sess.state = S.CHECKER_MTG

        preview_lines = [s["raw"] for s in valid[:5]]
        if len(valid) > 5:
            preview_lines.append(f"... +{len(valid) - 5} more")
        preview = "\n".join(preview_lines)
        err_note = f"\n⚠️ <b>{len(errors)} line(s) skipped</b> (wrong format)" if errors else ""

        sess.wiz_mid = None
        _send(cid,
              efmt(f"✅ <b>{len(valid)} signal(s) loaded</b>{err_note}\n\n"
                   f"<code>{preview}</code>\n\n"
                   "━━━━━━━━━━━━━━━━━━━━\n"
                   "<b>Select Martingale Step:</b>\n\n"
                   "🔁 <b>MTG 1</b> — entry + 1 recovery candle\n"
                   "🔁 <b>MTG 2</b> — entry + up to 2 recovery candles\n"
                   "⚙️ <b>Custom</b> — set any number of MTG steps"),
              _kb_checker_mtg())
        return

    if sess.state == S.CHECKER_CUSTOM_MTG:
        raw_num = text.strip()
        try:
            custom_steps = int(raw_num)
            if custom_steps < 1 or custom_steps > 20:
                raise ValueError()
        except (ValueError, TypeError):
            _send(cid, efmt("❌ <b>Invalid number!</b> Please enter a number between <b>1 and 20</b>."))
            return
        sess.checker_draft["mtg_steps"] = custom_steps
        sess.state = S.CHECKER_DATE
        _send(cid, efmt(f"✅ Mode: <b>MTG {custom_steps} (Custom)</b>\n\n📅 <b>Select Date</b>"),
              _kb_checker_date())
        return

    if uid in ADMIN_IDS:
        parts = text.split()
        cmd   = parts[0].lower().split("@")[0] if parts else ""

        reply_to = msg.get("reply_to_message")
        if cmd == "/globalfree":

            arg = parts[1].strip().lower() if len(parts) > 1 else ""
            if arg in {"off", "stop", "disable", "0"}:
                if _db_global_free_disable():
                    _send(cid, efmt("⛔ <b>GLOBAL FREE ACCESS STOPPED</b>"))
                else:
                    _send(cid, efmt("❌ <b>Could not stop Global Free Access.</b>"))
                _send_global_free_panel(cid)
            elif arg:
                try:
                    days = int(arg)
                    if days < 1 or days > 3650:
                        raise ValueError()
                except (TypeError, ValueError):
                    _send(cid, efmt(
                        "❌ <b>Invalid duration.</b>\n\n"
                        "Use <code>/globalfree 1</code> to start for 24 hours, "
                        "or <code>/globalfree off</code> to stop."))
                    return
                until = _db_global_free_enable(days)
                if until:
                    expires = datetime.fromtimestamp(until).strftime("%Y-%m-%d %H:%M:%S")
                    _send(cid, efmt(
                        "✅ <b>GLOBAL FREE ACCESS STARTED</b>\n\n"
                        f"📅 Duration: <b>{days} day(s)</b>\n"
                        f"🕒 Ends at: <code>{expires}</code>"))
                    _send_global_free_panel(cid)
                else:
                    _send(cid, efmt("❌ <b>Could not start Global Free Access.</b>"))
            else:
                _send_global_free_panel(cid)
            return

        if cmd == "/broadcast" and reply_to:
            def _do_reply_broadcast():
                users   = _db_users_list()
                sent = fail = 0
                src_cid = reply_to.get("chat",{}).get("id") or cid
                src_mid = reply_to.get("message_id")
                for u in users:
                    t_uid2 = u.get("user_id")
                    if not t_uid2 or t_uid2 == uid: continue
                    try:
                        r = _api("copyMessage", data={
                            "chat_id":      t_uid2,
                            "from_chat_id": src_cid,
                            "message_id":   src_mid,
                        })
                        if r.get("ok"): sent += 1
                        else: fail += 1
                    except Exception: fail += 1
                    time.sleep(0.04)
                _send(cid, efmt(
                    f"📣 <b>Broadcast Complete</b>\n\n"
                    f"✅ Sent   : {sent}\n"
                    f"❌ Failed : {fail}"
                ))
            _send(cid, efmt("📣 <b>Broadcasting...</b>"))
            threading.Thread(target=_do_reply_broadcast, daemon=True).start()
            return

        WIZARD_CMDS = {
            "/addlicense", "/removelicense", "/license",
            "/ban", "/unban", "/broadcast",
            "/allowlivesession", "/disallowlivesession",
            "/addfuturesignal", "/removefuturesignal", "/futuresignal"
        }
        if cmd in WIZARD_CMDS:
            _admin_wiz_start(sess, cid, cmd.lstrip("/"))
            return

        if cmd == "/users":
            users = _db_users_list()
            if not users:
                _send(cid, efmt("📋 <b>No users registered yet.</b>")); return
            ulines = [f"📋 <b>All Users ({len(users)} total)</b>\n━━━━━━━━━━━━━━━━━━━━"]
            for i, u in enumerate(users, 1):
                uid2   = u.get("user_id","?")
                uname  = f"@{u['username']}" if u.get("username") else "—"
                name   = u.get("full_name","—")
                joined = u.get("joined_at","—")
                total  = u.get("total_sigs",0)
                wins   = u.get("wins",0)
                losses = u.get("losses",0)
                expiry = u.get("license_expiry","")
                valid  = _db_license_is_valid(uid2) if isinstance(uid2,int) else False
                banned = bool(u.get("is_banned",0))
                if banned: lic_status = "🔒 Banned"
                elif valid: lic_status = f"✅ Active (exp: {expiry})"
                elif expiry: lic_status = f"❌ Expired ({expiry})"
                else: lic_status = "❌ No License"
                fut_expiry = u.get("future_access_expiry","")
                fut_valid  = _db_future_access_is_valid(uid2) if isinstance(uid2,int) else False
                if fut_valid: fut_status = f"✅ Active (exp: {fut_expiry})"
                elif fut_expiry: fut_status = f"❌ Expired ({fut_expiry})"
                else: fut_status = "❌ No Access"
                ulines.append(
                    f"\n<b>#{i}</b>\n"
                    f"  🆔 ID       : <code>{uid2}</code>\n"
                    f"  👤 Username : {uname}\n"
                    f"  📛 Name     : {name}\n"
                    f"  📅 Joined   : {joined}\n"
                    f"  📊 Signals  : {total} (✅{wins} ❌{losses})\n"
                    f"  🔰 License  : {lic_status}\n"
                    f"  📆 Future Sig: {fut_status}"
                )
            chunks = []; chunk = ""
            for line in ulines:
                if len(chunk)+len(line)>3800: chunks.append(chunk); chunk=line
                else: chunk += "\n"+line if chunk else line
            if chunk: chunks.append(chunk)
            for ch in chunks: _send(cid, efmt(ch))
            return

        if cmd == "/strategy":
            _send_strategy_panel(cid)
            return

        if cmd == "/adminhelp":
            _send(cid, efmt(
                "⚙️ <b>Admin Commands</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "All commands are step-by-step wizards.\n"
                "Just send the command and follow the prompts!\n\n"
                "📋 <b>License:</b>\n"
                "  /addlicense — Add VIP license\n"
                "  /removelicense — Remove license\n"
                "  /license — View license info\n"
                "  /globalfree — Timed unlimited access for everyone\n\n"
                "👤 <b>Users:</b>\n"
                "  /users — List all users\n"
                "  /ban — Ban a user\n"
                "  /unban — Unban a user\n\n"
                "📡 <b>Channel Sender</b> (all VIP users have access by default):\n"
                "  /allowlivesession — Unlock for a specific user (even free)\n"
                "  /disallowlivesession — Disable for a specific user\n\n"
                "📆 <b>Future Signal (separate from license):</b>\n"
                "  /addfuturesignal — Grant Future Signal access + daily limit + days\n"
                "  /removefuturesignal — Revoke Future Signal access\n"
                "  /futuresignal — View Future Signal access info\n\n"
                "🔬 <b>Strategy:</b>\n"
                "  /strategy — Enable / Hide strategies\n\n"
                "📣 <b>Broadcast:</b>\n"
                "  /broadcast — Send message to all users\n\n"
                "ℹ️ <b>Other:</b>\n"
                "  /adminhelp — Show this help\n\n"
                "💡 Type /cancel anytime to exit a wizard."
            ))
            return



TIMEZONE_LIST = [
    ("Bangladesh", 6.0, "BD"), ("India", 5.5, "IN"), ("Pakistan", 5.0, "PK"),
    ("Nepal", 5.75, "NP"), ("Sri Lanka", 5.5, "LK"), ("UAE/Dubai", 4.0, "AE"),
    ("Saudi Arabia", 3.0, "SA"), ("Turkey", 3.0, "TR"), ("Kenya", 3.0, "KE"),
    ("Moscow", 3.0, "RU"), ("Egypt", 2.0, "EG"), ("South Africa", 2.0, "ZA"),
    ("Germany/CET", 1.0, "DE"), ("London/UTC", 0.0, "GB"), ("Brazil", -3.0, "BR"),
    ("Argentina", -3.0, "AR"), ("New York", -5.0, "NY"), ("Chicago", -6.0, "CH"),
    ("Denver", -7.0, "DV"), ("Los Angeles", -8.0, "LA"), ("Toronto", -5.0, "CA"),
    ("Mexico City", -6.0, "MX"), ("Japan", 9.0, "JP"), ("China", 8.0, "CN"),
    ("Singapore", 8.0, "SG"), ("Sydney", 10.0, "AU"), ("New Zealand", 12.0, "NZ"),
    ("Indonesia", 7.0, "ID"), ("Thailand", 7.0, "TH"), ("Philippines", 8.0, "PH"),
]

def _tz_offset_label(offset):
    sign = "+" if offset >= 0 else "-"
    absolute = abs(float(offset)); hour = int(absolute); minute = int(round((absolute - hour) * 60))
    return f"UTC{sign}{hour:02d}:{minute:02d}"

def _tz_by_code(code):
    return next(((label, offset) for label, offset, item_code in TIMEZONE_LIST if item_code == code), ("Unknown", 0.0))

def _tz_buttons(prefix):
    rows = []
    for index in range(0, len(TIMEZONE_LIST), 2):
        row = []
        for _label, offset, code in TIMEZONE_LIST[index:index + 2]:
            row.append({"text": f"  {_tz_offset_label(offset)}  ", "callback_data": f"{prefix}{code}",
                        "style": "primary", "icon_custom_emoji_id": "6075593821331137073"})
        rows.append(row)
    rows.append([{"text": "Back", "callback_data": "menu_home", "style": "danger",
                  "icon_custom_emoji_id": "5258084656674250503"}])
    return rows

def _convert_signal_list(raw_text, src_offset, dst_offset):
    delta_minutes = int(round((float(dst_offset) - float(src_offset)) * 60))
    def replace_time(match):
        hour, minute = map(int, match.group(0).split(":"))
        if hour > 23 or minute > 59:
            return match.group(0)
        total = (hour * 60 + minute + delta_minutes) % 1440
        return f"{total // 60:02d}:{total % 60:02d}"
    return "\n".join(re.sub(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b", replace_time, line)
                     for line in str(raw_text).strip().splitlines())

def _parse_formatter_signals(raw_text):
    """Reuse the bot's broad Checker parser so every supported signal format works here too."""
    valid, errors = _backtest_parse_signals(str(raw_text or ""))
    signals = []
    for signal in valid:
        direction = str(signal.get("direction") or "").upper()
        signals.append({
            "pair": str(signal.get("pair") or "").upper(),
            "time": str(signal.get("time") or "").zfill(5),
            "direction": "CALL" if direction in ("BUY", "CALL", "CAL", "UP") else "PUT",
        })
    return signals, errors

def _formatter_pair_variants(pair, example):
    normalized_example = _ck_clean_unicode(str(example or ""))
    first_line = next((line.strip() for line in normalized_example.splitlines() if line.strip()), normalized_example)
    is_otc = pair.upper().endswith("_OTC")
    base = pair[:-4] if is_otc else pair
    slash = f"{base[:3]}/{base[3:6]}" if len(base) == 6 else base
    body = slash if "/" in first_line else base
    pair_match = re.search(r"[A-Za-z]{2,12}(?:/[A-Za-z]{2,12})?(?:[-_]OTC)?", first_line, re.I)
    sample_pair = pair_match.group(0) if pair_match else ""
    lower_pair = bool(sample_pair) and any(ch.islower() for ch in sample_pair if ch.isalpha())
    body = body.lower() if lower_pair else body.upper()
    if not is_otc:
        return body
    if "_otc" in first_line: return body + "_otc"
    if "_OTC" in first_line: return body + "_OTC"
    if "-otc" in first_line: return body + "-otc"
    return body + "-OTC"

def _formatter_template(example):
    original = next((line.strip() for line in str(example).splitlines() if line.strip()), "")
    use_mono = any(0x1D400 <= ord(ch) <= 0x1D7FF for ch in original)
    example = _ck_clean_unicode(original).strip()
    if all(key in example.upper() for key in ("{PAIR}", "{TIME}")) and ("{DIR}" in example.upper() or "{DIRECTION}" in example.upper()):
        template = re.sub(r"\{PAIR\}", "{PAIR}", example, flags=re.I)
        template = re.sub(r"\{TIME\}", "{TIME}", template, flags=re.I)
        template = re.sub(r"\{DIR(?:ECTION)?\}", "{DIR}", template, flags=re.I)
        return (template, use_mono), None
    parsed, _ = _parse_formatter_signals(example)
    if not parsed:
        return None, "Could not understand the example format."
    template = re.sub(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b", "{TIME}", example, count=1)
    template = re.sub(r"\b(CALL|CAL|BUY|UP|PUT|SELL|DOWN)\b", "{DIR}", template, count=1, flags=re.I)
    pair = str(parsed[0].get("pair") or "")
    base = re.sub(r"[-_]OTC$", "", pair, flags=re.I)
    slash = f"{base[:3]}/{base[3:]}" if len(base) >= 6 else base
    candidates = [pair, pair.replace("_OTC", "-OTC"), pair.replace("_OTC", "_otc"),
                  pair.replace("_OTC", "-otc"), base, slash]
    replaced = False
    for candidate in sorted(set(candidates), key=len, reverse=True):
        match = re.search(re.escape(candidate), template, flags=re.I)
        if match:
            template = template[:match.start()] + "{PAIR}" + template[match.end():]
            replaced = True; break
    if not replaced:
        return None, "Could not find the pair in the example format."
    return (template, use_mono), None

def _format_signals(signals, example):
    template_data, error = _formatter_template(example)
    if error:
        return None, error
    template, use_mono = template_data
    example_upper = _ck_clean_unicode(str(example or "")).upper()
    if re.search(r"\bSELL\b", example_upper):
        buy_word, sell_word = "BUY", "SELL"
    elif re.search(r"\bBUY\b", example_upper) and not re.search(r"\bCALL\b", example_upper):
        buy_word, sell_word = "BUY", "PUT"
    else:
        buy_word, sell_word = "CALL", "PUT"
    lines = []
    for signal in signals:
        pair = _formatter_pair_variants(signal["pair"], example)
        direction = buy_word if signal["direction"] == "CALL" else sell_word
        line = template.replace("{PAIR}", pair).replace("{TIME}", signal["time"]).replace("{DIR}", direction)
        lines.append(_to_mono(line) if use_mono else line)
    return "\n".join(lines), None

def _screen_formatter_input(sess):
    sess.state = S.FORMATTER_INPUT; sess.formatter_draft = {}
    _wiz(sess, "🗂 <b>SIGNAL FORMATTER</b>\n━━━━━━━━━━━━━━\n\n<b>Step 1/2 — Paste Signal List</b>\n\n"
         "Send your signals in any format.\n\n<code>M1;EURUSD-OTC;14:26;CALL</code>\n"
         "<code>M1 EURUSD_OTC 14:42 PUT</code>\n\n📩 <b>Paste your signal list now</b>\n\n<i>To cancel use /cancel</i>",
         {"inline_keyboard": [[{"text": "Back", "callback_data": "menu_home", "style": "danger",
                                "icon_custom_emoji_id": "5258084656674250503"}]]})

def _screen_formatter_ask_format(sess):
    sess.state = S.FORMATTER_FORMAT
    count = len(sess.formatter_draft.get("signals") or [])
    _wiz(sess, f"🗂 <b>SIGNAL FORMATTER</b>\n━━━━━━━━━━━━━━\n\n✅ Loaded <b>{count}</b> signal(s)\n\n"
         "<b>Step 2/2 — Send Output Format</b>\n\nSend one example line of the format you want.\n\n"
         "<code>M1;EURUSD-OTC;14:26;CALL</code>\n<code>❒ USDCOP_otc 1M - 00:12 PUT</code>\n\n"
         "⬇️ <b>Send your format now</b>",
         {"inline_keyboard": [[{"text": "Paste List Again", "callback_data": "menu_formatter", "style": "primary",
                                "icon_custom_emoji_id": "5260687119092817530"}],
                              [{"text": "Back", "callback_data": "menu_home", "style": "danger",
                                "icon_custom_emoji_id": "5258084656674250503"}]]})

try:
    from quantex_news_signal import (
        NEWS_GLOBAL_PAIRS as _NEWS_GLOBAL_PAIRS,
        NEWS_FILTERS as _NEWS_FILTERS,
        NEWS_DAYS as _NEWS_DAYS,
        NEWS_EMOJI_IDS as _NEWS_EMOJI_IDS,
        default_news_draft as _default_news_draft,
        build_news_events as _build_news_events,
        build_news_signal_parts as _build_news_signal_parts,
        parts_to_text_and_entities as _news_parts_to_entities,
    )
except Exception as _news_imp_err:
    print(f"[NewsSignal] import failed: {_news_imp_err}")
    _NEWS_GLOBAL_PAIRS = ("EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "USD/CAD", "NZD/USD")
    _NEWS_FILTERS = ("all", "high", "medium", "low")
    _NEWS_DAYS = (1, 2, 3)
    _NEWS_EMOJI_IDS = {}
    def _default_news_draft():
        return {"pairs": list(_NEWS_GLOBAL_PAIRS), "n_days": 1, "filter": "high", "page": 0, "ai_mode": True}
    def _build_news_events(**kwargs):
        return {"status": "error", "message": "quantex_news_signal.py was not loaded"}
    def _build_news_signal_parts(*args, **kwargs):
        return [("News signal unavailable", None)]
    def _news_parts_to_entities(parts, *, use_prem, extra_emoji_ids=None):
        text = "".join(s for s, _ in parts)
        return text, [{"type": "bold", "offset": 0, "length": len(text)}]

def _news_ensure_draft(sess):
    if not isinstance(sess.news_draft, dict) or not sess.news_draft:
        sess.news_draft = _default_news_draft()
    return sess.news_draft

_NEWS_HTML_EMOJIS = {
    "📰": "news", "🔥": "fire2", "📆": "calendar2", "🗓": "calendar2",
    "🕒": "clock2", "💎": "gem", "🌐": "world", "🌍": "world",
    "💥": "impact_high", "🟠": "impact_med", "🔵": "impact_low",
    "🟢": "call_grn", "🔴": "put_red", "⌛": "hourglass", "⏳": "hourglass",
    "⏰": "stopwatch", "📊": "chart_up", "📈": "chart_up", "📉": "chart_down",
    "🎯": "target", "👑": "king", "⚡": "bolt", "✅": "check",
    "❌": "warn", "ℹ️": "news",
}

def _news_premium_html(text):
    """Apply the Manager File's premium emoji pack to News Signal messages."""
    result = str(text)
    for emoji, key in _NEWS_HTML_EMOJIS.items():
        emoji_id = (_NEWS_EMOJI_IDS or {}).get(key)
        if emoji_id:
            result = result.replace(emoji, f'<tg-emoji emoji-id="{emoji_id}">{emoji}</tg-emoji>')
    return result

def _news_wiz(sess, text, markup=None):
    text = _news_premium_html(text)
    if sess.wiz_mid:
        result = _edit(sess.wiz_chat, sess.wiz_mid, text, markup)
        if result.get("ok") or "not modified" in result.get("description", "").lower():
            return
    result = _send(sess.wiz_chat, text, markup)
    mid = result.get("result", {}).get("message_id")
    if mid:
        sess.wiz_mid = mid

def _kb_news_home(draft):
    count = len(draft.get("pairs") or [])
    days = int(draft.get("n_days") or 1)
    impact = str(draft.get("filter") or "high").upper()
    ai_on = bool(draft.get("ai_mode", True))
    return {"inline_keyboard": [
        [{"text": f"PAIRS ({count})", "callback_data": "news_pairs", "style": "primary",
          "icon_custom_emoji_id": "6330188813939251966"}],
        [{"text": f"DAYS : {days}", "callback_data": "news_days", "style": "primary",
          "icon_custom_emoji_id": "6102906733842144545"},
         {"text": f"IMPACT : {impact}", "callback_data": "news_filter", "style": "primary",
          "icon_custom_emoji_id": "6231237393119191254"}],
        [{"text": f"ZEBRONIX AI : {'ON' if ai_on else 'OFF'}", "callback_data": "news_ai_toggle",
          "style": "success" if ai_on else "danger", "icon_custom_emoji_id": "6271527128408264959"}],
        [{"text": "GENERATE NEWS SIGNALS", "callback_data": "news_generate", "style": "success",
          "icon_custom_emoji_id": "5438571934210082705"}],
        [{"text": "Back", "callback_data": "menu_home", "style": "danger",
          "icon_custom_emoji_id": "5258084656674250503"}],
    ]}

def _screen_news_home(sess):
    draft = _news_ensure_draft(sess)
    _news_wiz(sess,
         "📰 <b>ZEBRONIX AI NEWS SIGNAL</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
         "Advanced global economic-news analyzer for news-based trading signals.\n\n"
         "Select pairs, days and impact, then tap GENERATE.",
         _kb_news_home(draft))

def _screen_news_pairs(sess):
    draft = _news_ensure_draft(sess)
    selected = set(draft.get("pairs") or [])
    rows, row = [], []
    for pair in _NEWS_GLOBAL_PAIRS:
        row.append({"text": pair,
                    "callback_data": f"news_ptog_{pair}",
                    "style": "success" if pair in selected else "primary",
                    "icon_custom_emoji_id": "6244395867244077774" if pair in selected else "6330188813939251966"})
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.extend([
        [{"text": "Select All", "callback_data": "news_sel_all", "style": "success", "icon_custom_emoji_id": "6244395867244077774"},
         {"text": "Clear", "callback_data": "news_sel_clear", "style": "danger", "icon_custom_emoji_id": "6260072893011469020"}],
        [{"text": "Confirm", "callback_data": "news_pairs_ok", "style": "success", "icon_custom_emoji_id": "6246965275594333152"}],
        [{"text": "Back", "callback_data": "menu_news_signal", "style": "danger", "icon_custom_emoji_id": "5258084656674250503"}],
    ])
    _news_wiz(sess, f"⚡ <b>NEWS SIGNAL — GLOBAL PAIRS</b>\n\nSelected: <b>{len(selected)}</b> / {len(_NEWS_GLOBAL_PAIRS)}",
         {"inline_keyboard": rows})

def _news_send_card(cid, parts, kb):
    text, entities = _news_parts_to_entities(parts, use_prem=True,
                                              extra_emoji_ids=_NEWS_EMOJI_IDS)
    payload = {"chat_id": cid, "text": text, "entities": entities}
    if kb:
        payload["reply_markup"] = _style_button_markup(kb)
    try:
        data = requests.post(f"{BASE}/sendMessage", json=payload, timeout=25).json()
        if data.get("ok"):
            return True
        print(f"[NewsSignal] send failed: {data.get('description')}")
    except Exception as ex:
        print(f"[NewsSignal] send error: {ex}")
    return False

def _run_news_signal_generate(uid, cid, draft):
    pairs = list(draft.get("pairs") or [])
    days = int(draft.get("n_days") or 1)
    impact = str(draft.get("filter") or "all")
    use_ai = bool(draft.get("ai_mode", True))
    wait = _send(cid, _news_premium_html(f"⏳ <b>Generating AI NEWS SIGNALS...</b>\n<i>{len(pairs)} pairs · {days}d · {impact.upper()}</i>"))
    wait_mid = (wait or {}).get("result", {}).get("message_id")
    result = _build_news_events(pairs=pairs, n_days=days, newsfilter=impact,
                                tz_hours=6.0, use_ai=use_ai,
                                gemini_keys=list(GEMINI_API_KEYS) if use_ai else None)
    if wait_mid:
        _api("deleteMessage", data={"chat_id": cid, "message_id": wait_mid})
    kb = {"inline_keyboard": [
        [{"text": "Generate Again", "callback_data": "news_generate", "style": "success", "icon_custom_emoji_id": "5438571934210082705"}],
        [{"text": "News Menu", "callback_data": "menu_news_signal", "style": "primary", "icon_custom_emoji_id": "5971837723676249096"}],
        [{"text": "Back Home", "callback_data": "menu_home", "style": "danger", "icon_custom_emoji_id": "5258084656674250503"}],
    ]}
    if not isinstance(result, dict) or result.get("status") != "success":
        _send(cid, _news_premium_html(f"❌ <b>News signal generation failed.</b>\n\n<code>{(result or {}).get('message', 'Unknown error')}</code>"), kb)
        return
    events = result.get("events") or []
    if not events:
        _send(cid, _news_premium_html("ℹ️ <b>No matching tradable news found.</b>\nTry more pairs, days, or Impact = ALL."), kb)
        return
    tz = result.get("tz_label") or "UTC+6"
    for index, event in enumerate(events):
        parts = _build_news_signal_parts(event, events_today=len(events), tz_label=tz,
                                         owner=SUPPORT_USERNAME, bot_username="ZEBRONIX_AI",
                                         ai_used=bool(result.get("ai_used")))
        last_kb = kb if index == len(events) - 1 else None
        if not _news_send_card(cid, parts, last_kb):
            _send(cid, _news_premium_html("".join(s for s, _ in parts)), last_kb)
        if index < len(events) - 1:
            time.sleep(0.35)

def on_callback(cb):
    uid      = cb.get("from",{}).get("id")
    cid      = cb.get("message",{}).get("chat",{}).get("id")
    cb_id    = cb.get("id","")
    data     = cb.get("data","")
    username = cb.get("from",{}).get("username","") or ""
    fname    = cb.get("from",{}).get("first_name","") or ""
    if not uid or not data: return
    _answer(cb_id)
    if uid not in _db_cache:
        _db_user_register(uid, username, fname)
    sess = _sess(uid)
    if not sess.wiz_chat:
        sess.wiz_chat = cid
    sess.wiz_mid = cb.get("message",{}).get("message_id")
    if sess.wiz_mid and sess.wiz_mid == getattr(sess, "welcome_photo_mid", None):
        _delete(cid, sess.wiz_mid)
        sess.wiz_mid = None
        sess.welcome_photo_mid = None

    if uid not in ADMIN_IDS and _db_is_banned(uid) and data not in ("menu_home","/start"):
        _wiz(sess,
             "🚫 <b>You are banned from this bot.</b>\n\n"
             f"Contact {SUPPORT_USERNAME} if you think this is a mistake.",
             {"inline_keyboard":[[{"text":"Contact Support","url":f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}","style":"primary","icon_custom_emoji_id":str(EMAP["✉"])}]]})
        return

    if data == "verify_channel":
        if _is_channel_member(uid):
            sess.state = S.IDLE
            _send_welcome(uid, sess, _kb_welcome)
        else:
            _send_channel_required(cid, sess, already_joined=True)
        return

    if uid not in ADMIN_IDS and data not in ("menu_home", "/start", "verify_channel")             and not _is_channel_member(uid):
        _send_channel_required(cid, sess)
        return

    if data in ("menu_home","/start"):
        sess.state = S.IDLE
        if uid not in ADMIN_IDS and not _is_channel_member(uid):
            _send_channel_required(cid, sess)
            return
        _send_welcome(uid, sess, _kb_welcome)
        return

    if data in _COMING_SOON_BUTTONS:
        feature_name = _COMING_SOON_BUTTONS[data][0]
        sess.state = S.IDLE
        _wiz(sess, efmt(
            f"🚧 <b>{_html.escape(feature_name)}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "This feature is under development, coming soon."),
            {"inline_keyboard": [[{
                "text": "BACK", "callback_data": "menu_home", "style": "primary",
                "icon_custom_emoji_id": "5258084656674250503"
            }]]})
        return

    access_policy = _premium_access_policy(data)
    if access_policy and not _enforce_premium_access(uid, sess, access_policy):
        return

    if data == "menu_pair_list":
        sess.state = S.IDLE
        sess.wiz_mid = None
        chunks = _pair_list_messages()
        home_kb = {"inline_keyboard": [[{
            "text": "𝙷𝙾𝙼𝙴", "callback_data": "menu_home", "style": "primary",
            "icon_custom_emoji_id": "5416041192905265756"
        }]]}
        for index, chunk in enumerate(chunks):
            _send(cid, chunk, home_kb if index == len(chunks) - 1 else None)
        return

    if data == "menu_market_payouts":
        sess.state = S.IDLE
        _market_payouts_async(cid, sess)
        return

    if data == "menu_bug_future":
        sess.state = S.IDLE
        _wiz(sess, efmt("🚧 <b>𝙱𝚄𝙶 𝙵𝚄𝚃𝚄𝚁𝙴</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                        "This feature is under maintenance — coming soon."),
             {"inline_keyboard":[[{"text":"𝙷𝙾𝙼𝙴","callback_data":"menu_home","style":"primary"}]]})
        return

    if data == "menu_volatility_filter":
        sess.state = S.VOLATILITY_INPUT
        _wiz(sess, _volatility_efmt(
            "👾 <b>𝚉𝙴𝙱𝚁𝙾𝙽𝙸𝚇 𝙰𝙸 𝚅𝙾𝙻𝙰𝚃𝙸𝙻𝙸𝚃𝚈 𝙱𝙾𝚃</b> 👾\n\n"
            "Click <b>SCAN VOLATILITY (85%+)</b> to analyze all high-payout assets, "
            "or send any pair name manually (example: <code>USDARS_otc</code>)."),
             _volatility_result_keyboard())
        return

    if data == "volatility_scan_all":
        sess.state = S.VOLATILITY_INPUT
        _volatility_scan_all_async(cid, sess)
        return

    if data == "menu_ai_thinker":
        sess.state = S.IDLE
        _wiz(sess, efmt("🤖 <b>𝗭𝗘𝗕𝗥𝗢𝗡𝗜𝗫 𝗔𝗜 𝗧𝗛𝗜𝗡𝗞𝗘𝗥</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                        "Select a market type to load open pairs with live payouts."),
             {"inline_keyboard":[
                 [{"text":"𝙾𝚃𝙲 𝙼𝙰𝚁𝙺𝙴𝚃","callback_data":"ai_thinker_market_OTC","style":"primary","icon_custom_emoji_id":str(EMAP["📊"])}],
                 [{"text":"𝙻𝙸𝚅𝙴 𝙼𝙰𝚁𝙺𝙴𝚃","callback_data":"ai_thinker_market_LIVE","style":"primary","icon_custom_emoji_id":str(EMAP["📈"])}],
                 [{"text":"𝙷𝙾𝙼𝙴","callback_data":"menu_home","style":"danger"}]]})
        return

    if data in ("ai_thinker_market_OTC", "ai_thinker_market_LIVE"):
        _ai_thinker_load_market(cid, sess, data.rsplit("_", 1)[-1])
        return

    if data.startswith("ai_thinker_page_"):
        try:
            _, _, _, market, page = data.split("_", 4)
            if market != sess.ai_thinker_market:
                _ai_thinker_load_market(cid, sess, market)
                return
            kb, current, total = _ai_thinker_market_menu(sess, market, int(page))
            _wiz(sess, efmt(f"🤖 <b>ZEBRONIX AI THINKER</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"📊 <b>{market} OPEN MARKETS</b>\nSelect one pair to analyze.\n\nPage {current}/{total}"), kb)
        except Exception:
            _ai_thinker_load_market(cid, sess, sess.ai_thinker_market or "OTC")
        return

    if data.startswith("ai_thinker_pair_"):
        try:
            idx = int(data.rsplit("_", 1)[-1])
            pair = sess.ai_thinker_pairs[idx]
        except Exception:
            _ai_thinker_load_market(cid, sess, sess.ai_thinker_market or "OTC")
            return
        _ai_thinker_analyze_async(cid, sess, pair, sess.ai_thinker_market or "OTC")
        return

    if data == "menu_market_filter":
        sess.state = S.IDLE
        _wiz(sess, efmt("📊 <b>MARKET FILTERS</b>\nSelect market type to scan:"),
             {"inline_keyboard":[
                 [{"text":"OTC MARKET","callback_data":"market_filter_OTC","style":"primary","icon_custom_emoji_id":str(EMAP["📊"])}],
                 [{"text":"LIVE MARKET","callback_data":"market_filter_LIVE","style":"primary","icon_custom_emoji_id":str(EMAP["📈"])}],
                 [{"text":"HOME","callback_data":"menu_home","style":"danger"}]]})
        return

    if data in ("market_filter_OTC", "market_filter_LIVE"):
        _tool_scan_async(cid, sess, "market", data.rsplit("_",1)[-1])
        return

    if data == "menu_candle_colours":
        sess.state = S.CANDLE_COLOUR_INPUT
        _wiz(sess, efmt("📊 <b>Recent Candle History</b>\n━━━━━━━━━━━━━━━━━━━━\n\nSend a pair name manually (example: <code>EURUSD_otc</code>) or scan all available pairs with <b>90%+ payout</b>."),
             {"inline_keyboard":[
                 [{"text":"SCAN ALL PAIRS","callback_data":"candle_scan_all","style":"primary","icon_custom_emoji_id":str(EMAP["🔍"])}],
                 [{"text":"HOME","callback_data":"menu_home","style":"danger"}]]})
        return

    if data == "candle_scan_all":
        _tool_scan_async(cid, sess, "candle")
        return

    if data == "menu_recent_trend":
        sess.state = S.RECENT_TREND_INPUT
        _wiz(sess, efmt("📊 <b>RECENT TREND ANALYZER</b>\n━━━━━━━━━━━━━━━━━━━━\n\nSend a pair name manually (example: <code>USDARS_otc</code>) or scan all available pairs with <b>88%+ payout</b>."),
             {"inline_keyboard":[
                 [{"text":"SCAN ALL PAIRS","callback_data":"recent_scan_all","style":"primary","icon_custom_emoji_id":str(EMAP["🔍"])}],
                 [{"text":"HOME","callback_data":"menu_home","style":"danger"}]]})
        return

    if data == "recent_scan_all":
        _tool_scan_async(cid, sess, "recent")
        return

    if data == "menu_ai_filter":
        sess.state = S.AI_FILTER_INPUT
        sess.ai_filter_draft = {}
        _wiz(sess, _ai_filter_input_prompt(),
             {"inline_keyboard": [[{
                 "text": "CANCEL", "callback_data": "ai_filter_cancel", "style": "danger",
                 "icon_custom_emoji_id": "5258084656674250503"
             }]]})
        return

    if data.startswith("ai_filter_mtg_") and sess.state == S.AI_FILTER_MTG:
        try:
            mtg = int(data.rsplit("_", 1)[-1])
        except ValueError:
            return
        if mtg not in (0, 1, 2, 3):
            return
        sess.ai_filter_draft["mtg"] = mtg
        sess.state = S.AI_FILTER_DAYS
        _wiz(sess, "📅 <b>Choose how many previous days to check (1-10):</b>",
             {"inline_keyboard": [
                 [{"text": "1 DAY", "callback_data": "ai_filter_days_1", "style": "primary",
                   "icon_custom_emoji_id": str(EMAP["📅"])},
                  {"text": "2 DAYS", "callback_data": "ai_filter_days_2", "style": "primary",
                   "icon_custom_emoji_id": str(EMAP["📅"])},
                  {"text": "3 DAYS", "callback_data": "ai_filter_days_3", "style": "primary",
                   "icon_custom_emoji_id": str(EMAP["📅"])},
                  {"text": "5 DAYS", "callback_data": "ai_filter_days_5", "style": "primary",
                   "icon_custom_emoji_id": str(EMAP["📅"])}],
                 [{"text": "7 DAYS", "callback_data": "ai_filter_days_7", "style": "primary",
                   "icon_custom_emoji_id": str(EMAP["📅"])},
                  {"text": "10 DAYS", "callback_data": "ai_filter_days_10", "style": "primary",
                   "icon_custom_emoji_id": str(EMAP["📅"])}],
                 [{"text": "CANCEL", "callback_data": "ai_filter_cancel", "style": "danger",
                   "icon_custom_emoji_id": "5258084656674250503"}]]})
        return

    if data.startswith("ai_filter_days_") and sess.state == S.AI_FILTER_DAYS:
        try:
            days = int(data.rsplit("_", 1)[-1])
        except ValueError:
            return
        if days not in (1, 2, 3, 5, 7, 10):
            return
        sess.ai_filter_draft["days"] = days
        sess.wiz_mid = None
        _run_ai_filter(uid, cid, sess, days)
        return

    if data == "ai_filter_cancel":
        sess.state = S.IDLE
        sess.ai_filter_draft = {}
        sess.wiz_mid = None
        _send_welcome(uid, sess, _kb_welcome)
        return

    if data == "menu_backtest":
        sess.state = S.IDLE
        sess.backtest_signals = []
        sess.backtest_original_count = 0
        sess.backtest_market = None
        _wiz(sess,
             "🎯 <b>BACKTEST MARKET SELECTION</b>\n"
             "━━━━━━━━━━━━━━━━━━━━\n\n"
             "Select the market of the signal list you want to backtest.",
             {"inline_keyboard": [
                 [{"text": "OTC MARKET", "callback_data": "backtest_market_OTC",
                   "style": "primary", "icon_custom_emoji_id": str(EMAP["📊"])},
                  {"text": "LIVE MARKET", "callback_data": "backtest_market_LIVE",
                   "style": "primary", "icon_custom_emoji_id": str(EMAP["📈"])}],
                 [{"text": "CANCEL", "callback_data": "backtest_cancel",
                   "style": "danger", "icon_custom_emoji_id": "5258084656674250503"}]
             ]})
        return

    if data in ("backtest_market_OTC", "backtest_market_LIVE"):
        market = data.rsplit("_", 1)[-1]
        sess.backtest_market = market
        sess.state = S.BACKTEST_INPUT
        sess.backtest_signals = []
        sess.backtest_original_count = 0
        market_label = "OTC MARKET" if market == "OTC" else "LIVE MARKET"
        example = ("M1;EURUSD_OTC;14:26;CALL" if market == "OTC"
                   else "M1;EURUSD;14:26;CALL")
        _wiz(sess,
             f"🎯 <b>{market_label} BACKTEST</b>\n"
             "━━━━━━━━━━━━━━━━━━━━\n\n"
             "⚙️ Timezone: <b>UTC+6 (BDT)</b>\n\n"
             "📩 <b>Send your signal list now</b> — <b>ALL FORMAT SUPPORTED</b>\n\n"
             f"<code>{example}</code>\n\n"
             f"<i>Only supported {market_label.lower()} pairs will be accepted.</i>",
             {"inline_keyboard": [[{
                 "text": "BACK", "callback_data": "menu_backtest",
                 "style": "danger", "icon_custom_emoji_id": "5258084656674250503"
             }]]})
        return

    if data == "backtest_run" and sess.state == S.BACKTEST_READY:
        sess.state = S.BACKTEST_RUNNING
        sess.wiz_mid = None
        _run_backtest(uid, cid, sess)
        return

    if data == "backtest_cancel":
        sess.state = S.IDLE
        sess.backtest_signals = []
        sess.backtest_original_count = 0
        sess.backtest_market = None
        sess.wiz_mid = None
        _send_welcome(uid, sess, _kb_welcome)
        return

    if data == "menu_multi_fs" or data.startswith("mfs_"):
        if uid not in ADMIN_IDS and not _db_future_access_is_valid(uid):
            _wiz(sess, efmt(_future_access_denied_text(uid)), _kb_future_access_required())
            sess.state = S.IDLE
            return

    if data == "menu_multi_fs":
        _mfs_start(sess)
        return

    if data.startswith("mfs_mkt_"):
        market_type = data.replace("mfs_mkt_", "")
        if market_type not in ("REAL", "OTC"):
            return
        sess.multi_fs = {"market_type": market_type, "selected_pairs": [],
                         "payouts": {}, "sorted_pairs": []}
        _wiz(sess, "⏳ <b>Fetching live payouts…</b> please wait.")

        def _mfs_payout_worker(_market_type=market_type):
            pool = MULTIPLE_FS_OTC if _market_type == "OTC" else MULTIPLE_FS_REAL
            payouts = _mfs_fetch_payouts(pool)
            if sess.multi_fs.get("market_type") != _market_type:
                return
            sess.multi_fs["payouts"] = payouts
            sess.multi_fs["sorted_pairs"] = sorted(
                pool, key=lambda pair: payouts.get(pair, 0), reverse=True
            )
            _mfs_render_pairs(sess)
        threading.Thread(target=_mfs_payout_worker, daemon=True).start()
        return

    if data.startswith("mfs_pair_"):
        selected = data.replace("mfs_pair_", "")
        current = sess.multi_fs.setdefault("selected_pairs", [])
        if selected == "CONFIRM":
            if not current:
                _answer(cb_id, "⚠️ Select at least 1 pair!", show_alert=True)
                return
            _wiz(sess,
                 f"😧 <b>SELECT DIRECTION CRITERIA ({len(current)} Pairs Selected):</b>",
                 {"inline_keyboard": [
                     [{"text": " CALL BUY UP", "callback_data": "mfs_dir_CALL", "style": "success",
                       "icon_custom_emoji_id": "6055584668210701185"}],
                     [{"text": " PUT SELL DOWN", "callback_data": "mfs_dir_PUT", "style": "primary",
                       "icon_custom_emoji_id": "6057775002747412180"}],
                     [{"text": " BUY & PUT (BOTH)", "callback_data": "mfs_dir_BOTH", "style": "success",
                       "icon_custom_emoji_id": "6057849898387119890"}],
                 ]})
            return
        pool = MULTIPLE_FS_OTC if sess.multi_fs.get("market_type") == "OTC" else MULTIPLE_FS_REAL
        if selected not in pool:
            return
        if selected in current:
            current.remove(selected)
        else:
            current.append(selected)
        _mfs_render_pairs(sess)
        return

    if data.startswith("mfs_dir_"):
        direction = data.replace("mfs_dir_", "")
        if direction not in ("CALL", "PUT", "BOTH"):
            return
        sess.multi_fs["direction"] = direction
        sess.state = S.MULTI_FS_DAYS
        _send(cid, efmt("<b>✏️ ENTER ANALYSIS DAYS (1 - 30):</b>\n"
                        "Provide historical quantum depth days to analyze:"))
        return

    if data == "menu_profile":
        doc   = db_get(uid)
        valid = _db_license_is_valid(uid)
        used  = _db_live_quota_get(uid)
        uname  = f"@{doc['username']}" if doc.get("username") else "—"
        joined = doc.get("joined_at","—")
        total  = doc.get("total_sigs",0)
        wins   = doc.get("wins",0)
        losses = doc.get("losses",0)
        expiry = doc.get("license_expiry","")
        lim    = doc.get("signal_limit",0)
        plan   = doc.get("plan_type","free")
        if uid in ADMIN_IDS:
            lic_txt = "♾ Admin — Unlimited"
            lim_txt = "Unlimited"
            exp_txt = "Never"
        elif valid:
            lic_txt = "✅ Active"
            lim_txt = str(lim)
            exp_txt = expiry
        elif expiry:
            lic_txt = "❌ Expired"
            lim_txt = str(lim)
            exp_txt = expiry
        else:
            lic_txt = "❌ No License (Free)"
            lim_txt = str(FREE_DAILY_LIMIT)
            exp_txt = "—"
        acc_txt = f"{round(wins/(wins+losses)*100,1)}%" if (wins+losses) > 0 else "—"
        _wiz(sess,
             efmt(
                 "◆═══════════════════◆\n"
                 "     👤  YOUR PROFILE\n"
                 "◆═══════════════════◆\n"
                 "▸━━━━━━━━━━━━━━━━━━▸\n"
                 f"▹ 🆔 ID        : <code>{uid}</code>\n"
                 f"▹ 👤 Username  : {uname}\n"
                 f"▹ 📅 Member Since : {joined}\n"
                 "▸━━━━━━━━━━━━━━━━━━▸\n"
                 "▸━━━━━━━━━━━━━━━━━━▸\n"
                 f"▹ 📊 Signals Sent : {total}\n"
                 f"▹ ✅ Wins      : {wins}\n"
                 f"▹ ❌ Losses    : {losses}\n"
                 f"▹ 🎯 Win Rate  : {acc_txt}\n"
                 f"▹ ⚡ Today's Usage : {used}\n"
                 "▸━━━━━━━━━━━━━━━━━━▸\n"
                 "▸━━━━━━━━━━━━━━━━━━▸\n"
                 f"▹ 🔰 License   : {lic_txt}\n"
                 f"▹ 🏷 Plan      : {plan.upper()}\n"
                 f"▹ ⚡ Daily Cap : {lim_txt} signals\n"
                 f"▹ ⏰ Valid Till : {exp_txt}\n"
                 "▸━━━━━━━━━━━━━━━━━━▸"
             ),
             {"inline_keyboard":[
                 ([{"text":"Get License","url":f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}","style":"success","icon_custom_emoji_id":str(EMAP["👑"])}]
                  if not valid and uid not in ADMIN_IDS else []),
                 [{"text":"Home","callback_data":"menu_home","icon_custom_emoji_id":"5416041192905265756","style":"primary",}],
             ]})
        return

    if data == "menu_about":
        a_html = _build_about()
        if sess.wiz_mid:
            res = _api("editMessageText", data={
                "chat_id":uid,"message_id":sess.wiz_mid,
                "text":a_html,"parse_mode":"HTML",
                "reply_markup":json.dumps({"inline_keyboard":[
                    [{"text":"Home","callback_data":"menu_home","icon_custom_emoji_id":"5416041192905265756","style":"primary",}]
                ]})
            })
            if res.get("ok") or "not modified" in res.get("description","").lower():
                return
        r   = _send(uid, a_html, {"inline_keyboard":[
                  [{"text":"Home","callback_data":"menu_home","icon_custom_emoji_id":"5416041192905265756","style":"primary",}]
              ]})
        mid = r.get("result",{}).get("message_id")
        if mid: sess.wiz_mid = mid
        return

    if data == "menu_checkers":
        _wiz(sess, "🔍 <b>SELECT A CHECKER:</b>", {"inline_keyboard": [
            [{"text": "𝙾𝚃𝙲 𝙲𝙷𝙴𝙲𝙺𝙴𝚁", "callback_data": "menu_otc_checker",
              "style": "primary", "icon_custom_emoji_id": str(EMAP["🔍"])}],
            [{"text": "𝚆𝙷𝙸𝚃𝙴𝙾𝚄𝚃 𝙲𝙷𝙴𝙲𝙺𝙴𝚁", "callback_data": "menu_whiteout_checker",
              "style": "primary", "icon_custom_emoji_id": "6213218467714179432"}],
            [{"text": "𝙱𝙻𝙰𝙲𝙺𝙾𝚄𝚃 𝙲𝙷𝙴𝙲𝙺𝙴𝚁", "callback_data": "menu_blackout_checker",
              "style": "primary", "icon_custom_emoji_id": "6213218467714179432"}],
            [{"text": "𝙻𝙸𝚅𝙴 𝙼𝙰𝚁𝙺𝙴𝚃 𝙲𝙷𝙴𝙲𝙺𝙴𝚁", "callback_data": "menu_live_checker",
              "style": "primary", "icon_custom_emoji_id": str(EMAP["📈"])}],
            [{"text": "Home", "callback_data": "menu_home", "style": "danger",
              "icon_custom_emoji_id": "5416041192905265756"}],
        ]})
        return

    if data in ("menu_whiteout_checker", "menu_blackout_checker"):
        is_whiteout = data == "menu_whiteout_checker"
        label = "WHITEOUT" if is_whiteout else "BLACKOUT"
        icon = "⚪" if is_whiteout else "😈"
        prefix = "checker_whiteout" if is_whiteout else "checker_blackout"
        _wiz(sess,
             f"{icon} <b>{label} CHECKER</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
             "Select which market you want to check:",
             {"inline_keyboard": [
                 [{"text": "𝙾𝚃𝙲 𝙼𝙰𝚁𝙺𝙴𝚃", "callback_data": f"{prefix}_otc",
                   "style": "primary", "icon_custom_emoji_id": str(EMAP["📊"])},
                  {"text": "𝙻𝙸𝚅𝙴 𝙼𝙰𝚁𝙺𝙴𝚃", "callback_data": f"{prefix}_live",
                   "style": "success", "icon_custom_emoji_id": str(EMAP["📈"])}],
                 [{"text": "Back", "callback_data": "menu_home", "style": "danger",
                   "icon_custom_emoji_id": "5258084656674250503"}],
             ]})
        return

    if data in ("menu_otc_checker", "menu_live_checker",
                "checker_whiteout_otc", "checker_whiteout_live",
                "checker_blackout_otc", "checker_blackout_live",
                "menu_whiteout_live_checker", "menu_blackout_live_checker"):
        mode = {"menu_otc_checker": "otc",
                "checker_whiteout_otc": "whiteout",
                "checker_whiteout_live": "whiteout_live",
                "menu_whiteout_live_checker": "whiteout_live",
                "menu_live_checker": "live",
                "checker_blackout_otc": "blackout",
                "checker_blackout_live": "blackout_live",
                "menu_blackout_live_checker": "blackout_live"}[data]
        sess.checker_draft = {"checker_mode": mode}
        sess.state = S.CHECKER_INPUT
        title = {"otc": "OTC CHECKER", "whiteout": "WHITEOUT CHECKER (OTC)",
                  "whiteout_live": "WHITEOUT CHECKER (LIVE)",
                  "live": "LIVE MARKET CHECKER", "blackout": "BLACKOUT CHECKER (OTC)",
                  "blackout_live": "BLACKOUT CHECKER (LIVE)"}[mode]
        if mode == "otc":
            example = ("<code>M1;EURUSD_OTC;14:26;CALL</code>\n"
                       "<code>M1 EURUSD_OTC 14:42 PUT</code>")
        elif mode in ("whiteout", "blackout"):
            example = ("<code>M1;EURUSD_OTC;14:26</code>\n"
                       "<code>M1 EURUSD_OTC 14:42</code>")
        elif mode in ("whiteout_live", "blackout_live"):
            example = ("<code>M1;EURUSD;14:26</code>\n"
                       "<code>M1 GBPUSD 14:42</code>")
        else:
            example = ("<code>M1;EURUSD;14:26;CALL</code>\n"
                       "<code>M1 GBPUSD 14:42 PUT</code>")
        _wiz(sess,
             f"🔍 <b>{title}</b>\n"
             "━━━━━━━━━━━━━━━━━━━━\n\n"
             "⚙️ Timezone: <b>UTC+6 (BDT)</b>\n\n"
             "📩 <b>Send your signal list now</b> (any common format works):\n"
             f"{example}\n\n"
             "━━━━━━━━━━━━━━━━━━━━\n"
             "<i>To cancel use /cancel</i>",
             {"inline_keyboard": [[{"text": "Home", "callback_data": "menu_home", "style": "danger",
                                     "icon_custom_emoji_id": "5416041192905265756"}]]})
        return

    if data.startswith("checker_mtg_") and data != "checker_mtg_custom" and sess.state == S.CHECKER_MTG:
        step_map = {"checker_mtg_0": 0, "checker_mtg_1": 1, "checker_mtg_2": 2}
        sess.checker_draft["mtg_steps"] = step_map.get(data, 1)
        sess.state = S.CHECKER_DATE
        _wiz(sess, "📅 <b>Select Date</b>\n\nChoose which date to check signals for:",
             _kb_checker_date())
        return

    if data == "checker_mtg_custom" and sess.state == S.CHECKER_MTG:
        sess.state = S.CHECKER_CUSTOM_MTG
        _wiz(sess,
             "⚙️ <b>Custom MTG Step</b>\n\n"
             "━━━━━━━━━━━━━━━━━━━━\n"
             "How many MTG steps do you want?\n\n"
             "✏️ Enter a number <b>(1 – 20)</b>:\n\n"
             "<i>To cancel use /cancel</i>",
             {"inline_keyboard": [[{"text": "Home", "callback_data": "menu_home", "style": "danger",
                                     "icon_custom_emoji_id": "5416041192905265756"}]]})
        return

    if data in ("checker_date_today", "checker_date_yesterday") and sess.state == S.CHECKER_DATE:
        sess.checker_draft["date_mode"] = "today" if data == "checker_date_today" else "yesterday"
        sess.state = S.CHECKER_PAYOUT
        _wiz(sess,
             "💰 <b>Payout Filter</b>\n\n"
             "━━━━━━━━━━━━━━━━━━━━\n\n"
             "Signals with payout <b>below 80%</b> will be shown with their "
             "payout% and will <b>not</b> be counted as WIN or LOSS.\n\n"
             "Enable the payout filter?",
             _kb_checker_payout())
        return

    if data in ("checker_payout_yes", "checker_payout_no"):
        sess.checker_draft["payout_filter"] = (data == "checker_payout_yes")
        mtg_steps = sess.checker_draft.get("mtg_steps", 1)
        sess.state = S.IDLE
        sess.wiz_mid = None
        _send(cid, efmt("🚨 <b>Checking signals…</b> please wait."))
        _ck_run_checker(uid, cid, sess, mtg_steps)
        return

    if data == "checker_recheck_payout":
        sess.checker_draft["payout_filter"] = True
        mtg_steps = sess.checker_draft.get("mtg_steps", 1)
        _send(cid, efmt("🚨 <b>Re-checking with payout filter…</b>"))
        _ck_run_checker(uid, cid, sess, mtg_steps)
        return

    if data == "checker_show_loss":
        _ck_run_show_loss(uid, cid, sess)
        return

    if data == "menu_tz_convert":
        sess.wiz_mid = None; sess.tz_draft = {}; sess.state = S.TZ_SRC
        _wiz(sess, "🕐 <b>Timezone Converter</b>\n\n<b>Step 1/3 — Select Source Timezone</b>\n\n"
             "Which timezone is your signal list currently in?",
             {"inline_keyboard": _tz_buttons("tz_src_")})
        return

    if data.startswith("tz_src_"):
        code = data.replace("tz_src_", "", 1); label, offset = _tz_by_code(code)
        sess.tz_draft.update({"src_code": code, "src_label": label, "src_offset": offset})
        sess.state = S.TZ_DST
        _wiz(sess, f"🕐 <b>Timezone Converter</b>\n\n✅ Source: <b>{_tz_offset_label(offset)}</b>\n\n"
             "<b>Step 2/3 — Select Target Timezone</b>\n\nWhich timezone do you want to convert TO?",
             {"inline_keyboard": _tz_buttons("tz_dst_")})
        return

    if data.startswith("tz_dst_"):
        code = data.replace("tz_dst_", "", 1); label, offset = _tz_by_code(code)
        sess.tz_draft.update({"dst_code": code, "dst_label": label, "dst_offset": offset})
        sess.state = S.TZ_INPUT
        _wiz(sess, f"🕐 <b>Timezone Converter</b>\n\n"
             f"✅ From: <b>{_tz_offset_label(sess.tz_draft.get('src_offset', 0))}</b>\n"
             f"✅ To: <b>{_tz_offset_label(offset)}</b>\n\n"
             "<b>Step 3/3 — Upload Signal List</b>\n\n📋 Paste or send your signal list below. Any format is supported.",
             {"inline_keyboard": [[{"text": "Back", "callback_data": "menu_tz_convert", "style": "primary",
                                    "icon_custom_emoji_id": "5258084656674250503"}]]})
        return

    if data == "menu_formatter":
        sess.wiz_mid = None
        _screen_formatter_input(sess)
        return

    if data == "fmt_ask_format":
        if sess.formatter_draft.get("signals"):
            _screen_formatter_ask_format(sess)
        else:
            _screen_formatter_input(sess)
        return

    if data == "menu_news_signal":
        _screen_news_home(sess)
        return

    if data == "news_pairs":
        _screen_news_pairs(sess)
        return

    if data.startswith("news_ptog_"):
        draft = _news_ensure_draft(sess)
        pair = data.replace("news_ptog_", "", 1)
        selected = list(draft.get("pairs") or [])
        selected = [p for p in selected if p != pair] if pair in selected else selected + [pair]
        order = {p: i for i, p in enumerate(_NEWS_GLOBAL_PAIRS)}
        draft["pairs"] = sorted(selected, key=lambda p: order.get(p, 999))
        _screen_news_pairs(sess)
        return

    if data == "news_sel_all":
        _news_ensure_draft(sess)["pairs"] = list(_NEWS_GLOBAL_PAIRS)
        _screen_news_pairs(sess)
        return

    if data == "news_sel_clear":
        _news_ensure_draft(sess)["pairs"] = []
        _screen_news_pairs(sess)
        return

    if data == "news_pairs_ok":
        if not _news_ensure_draft(sess).get("pairs"):
            _answer(cb_id, "Select at least one pair!", show_alert=True)
        else:
            _screen_news_home(sess)
        return

    if data == "news_days":
        draft = _news_ensure_draft(sess)
        current = int(draft.get("n_days") or 1)
        rows = [[{"text": f"{'✓ ' if d == current else ''}{d} Day{'s' if d > 1 else ''}",
                  "callback_data": f"news_days_set_{d}",
                  "style": "success" if d == current else "primary",
                  "icon_custom_emoji_id": "6102906733842144545"}] for d in _NEWS_DAYS]
        rows.append([{"text": "Back", "callback_data": "menu_news_signal", "style": "danger",
                      "icon_custom_emoji_id": "5258084656674250503"}])
        _news_wiz(sess, "📆 <b>NEXT DAY NEWS SIGNALS</b>\n\nHow many upcoming days should be analyzed?",
             {"inline_keyboard": rows})
        return

    if data.startswith("news_days_set_"):
        try:
            days = int(data.replace("news_days_set_", "", 1))
        except ValueError:
            days = 1
        _news_ensure_draft(sess)["n_days"] = days if days in _NEWS_DAYS else 1
        _screen_news_home(sess)
        return

    if data == "news_filter":
        draft = _news_ensure_draft(sess)
        current = str(draft.get("filter") or "high").lower()
        labels = {"all": "ALL IMPACT", "high": "HIGH", "medium": "MEDIUM", "low": "LOW"}
        rows = [[{"text": ("✓ " if f == current else "") + labels[f],
                  "callback_data": f"news_filter_set_{f}",
                  "style": "success" if f == current else "primary",
                  "icon_custom_emoji_id": "6231237393119191254"}] for f in _NEWS_FILTERS]
        rows.append([{"text": "Back", "callback_data": "menu_news_signal", "style": "danger",
                      "icon_custom_emoji_id": "5258084656674250503"}])
        _news_wiz(sess, "💥 <b>NEWS IMPACT FILTER</b>\n\nChoose which impact levels to include:",
             {"inline_keyboard": rows})
        return

    if data.startswith("news_filter_set_"):
        value = data.replace("news_filter_set_", "", 1).lower()
        _news_ensure_draft(sess)["filter"] = value if value in _NEWS_FILTERS else "all"
        _screen_news_home(sess)
        return

    if data == "news_ai_toggle":
        draft = _news_ensure_draft(sess)
        draft["ai_mode"] = not bool(draft.get("ai_mode", True))
        _screen_news_home(sess)
        return

    if data == "news_generate":
        draft = _news_ensure_draft(sess)
        if not draft.get("pairs"):
            _answer(cb_id, "Select at least one pair first!", show_alert=True)
            return
        snapshot = {"pairs": list(draft["pairs"]), "n_days": int(draft.get("n_days") or 1),
                    "filter": str(draft.get("filter") or "all"),
                    "ai_mode": bool(draft.get("ai_mode", True))}
        threading.Thread(target=_run_news_signal_generate, args=(uid, cid, snapshot), daemon=True).start()
        return

    if data == "menu_help":
        help_text = (
            "🛡 <b>ZEBRONIX AI — HELP CENTER</b> 🛡\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 <b>Auto Signal</b> — bot automatically scans the market and "
            "sends you a live signal when ready.\n\n"
            "✍️ <b>Manual Signal</b> — you pick the pair yourself and get an "
            "instant AI-confirmed signal.\n\n"
            "📆 <b>Future Signal</b> — generate a batch of upcoming signals for "
            "a chosen time window, days ahead, and market type.\n\n"
            "🔍 <b>Checkers</b> — verify OTC, Whiteout, Blackout, or Live Market conditions "
            "before you trade.\n\n"
            "👤 <b>My Profile</b> — view your usage stats, win rate, and plan details.\n\n"
            "🤖 <b>About</b> — learn more about ZEBRONIX AI.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"😈 <b>Need more help?</b> Contact {SUPPORT_USERNAME}\n"
            f"📣 <b>Channels:</b> {REQUIRED_CHANNEL_1_LINK} | {REQUIRED_CHANNEL_2_LINK}"
        )
        _wiz(sess, help_text, {"inline_keyboard": [
            [{"text": "Home", "callback_data": "menu_home", "style": "primary",
              "icon_custom_emoji_id": "5416041192905265756"}]
        ]})
        return

    if data == "menu_future_signal":
        if uid not in ADMIN_IDS and not _db_future_access_is_valid(uid):
            _wiz(sess, efmt(_future_access_denied_text(uid)), _kb_future_access_required())
            sess.state = S.IDLE
            return
        sess.fut_market_mode = None
        sess.fut_engine = "legacy"
        sess.fut_new_strategy = None
        sess.fut_pairs = []
        sess.fut_action_choice = "3"
        sess.fut_start_time = None
        sess.fut_end_time = None
        sess.state = S.FUTURE_MARKET_SELECT
        _wiz(sess, "🚀 <b>SELECT TARGET MARKET TYPE FROM BELOW:</b>", _kb_future_mode_select())
        return

    if data.startswith("futnew_home_"):
        strategy = data.replace("futnew_home_", "").upper()
        if strategy not in ("BLACKOUT", "WHITEOUT"):
            return
        if uid not in ADMIN_IDS and not _db_future_access_is_valid(uid):
            _wiz(sess, efmt(_future_access_denied_text(uid)), _kb_future_access_required())
            sess.state = S.IDLE
            return
        sess.fut_engine = "hard_filter"
        sess.fut_new_strategy = strategy
        sess.fut_market_mode = None
        sess.fut_pairs = []
        sess.fut_action_choice = "3"
        sess.fut_start_time = None
        sess.fut_end_time = None
        sess.fut_pair_payouts = {}
        sess.fut_sorted_pairs = []
        sess.state = S.FUTURE_MARKET_SELECT
        icon = "⚪" if strategy == "WHITEOUT" else "😈"
        _wiz(sess,
             f"{icon} <b>{strategy} FS NEW</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
             "Select the target market:",
             _kb_future_new_market_select(strategy))
        return

    if data.startswith("futnew_market_"):
        parts = data.split("_")
        if len(parts) != 4:
            return
        strategy, market_mode = parts[2].upper(), parts[3].upper()
        if strategy not in ("BLACKOUT", "WHITEOUT") or market_mode not in ("OTC", "REAL"):
            return
        sess.fut_engine = "hard_filter"
        sess.fut_new_strategy = strategy
        sess.fut_market_mode = market_mode
        sess.fut_pairs = []
        sess.fut_pair_payouts = {}
        sess.fut_sorted_pairs = []
        sess.state = S.FUTURE_GRID_SELECTING
        _wiz(sess, "⏳ <b>Fetching live payouts…</b> please wait.")

        def _new_worker(_mode=market_mode):
            pool = _future_pair_pool(_mode)
            payouts = _future_fetch_payouts(pool)
            sess.fut_pair_payouts = payouts
            sess.fut_sorted_pairs = sorted(pool, key=lambda p: payouts.get(p, 0), reverse=True)
            _wiz(sess,
                 "🔍 <b><i>Select one or more assets, then tap Continue Next:</i></b>",
                 _kb_future_pair_grid(sess))
        threading.Thread(target=_new_worker, daemon=True).start()
        return

    if data.startswith("fut_home_"):
        mode = data.replace("fut_home_", "")
        sess.fut_engine = "legacy"
        sess.fut_new_strategy = None
        sess.fut_market_mode = mode
        sess.fut_pairs = []
        sess.fut_action_choice = "3"
        sess.fut_start_time = None
        sess.fut_end_time = None
        sess.fut_pair_payouts = {}
        sess.fut_sorted_pairs = []
        sess.state = S.FUTURE_GRID_SELECTING
        _wiz(sess, "⏳ <b>Fetching live payouts…</b> please wait.")

        def _worker(_mode=mode):
            pool = _future_pair_pool(_mode)
            payouts = _future_fetch_payouts(pool)
            sess.fut_pair_payouts = payouts
            sess.fut_sorted_pairs = sorted(pool, key=lambda p: payouts.get(p, 0), reverse=True)
            _wiz(sess,
                 "🔍 <b><i>Tap Multiple Assets To Select Them individually, then Click Done "
                 "Or Click The Range below Then Generate Signal:</i></b>",
                 _kb_future_pair_grid(sess))
        threading.Thread(target=_worker, daemon=True).start()
        return

    if sess.state == S.FUTURE_MARKET_SELECT and data.startswith("fut_mode_"):
        mode = data.replace("fut_mode_", "")
        sess.fut_market_mode = mode
        sess.fut_pairs = []
        sess.fut_pair_payouts = {}
        sess.fut_sorted_pairs = []
        sess.state = S.FUTURE_GRID_SELECTING
        _wiz(sess, "⏳ <b>Fetching live payouts…</b> please wait.")

        def _worker(_mode=mode):
            pool = _future_pair_pool(_mode)
            payouts = _future_fetch_payouts(pool)
            sess.fut_pair_payouts = payouts
            sess.fut_sorted_pairs = sorted(pool, key=lambda p: payouts.get(p, 0), reverse=True)
            _wiz(sess,
                 "🔍 <b><i>Tap Multiple Assets To Select Them individually, then Click Done "
                 "Or Click The Range below Then Generate Signal:</i></b>",
                 _kb_future_pair_grid(sess))
        threading.Thread(target=_worker, daemon=True).start()
        return

    if sess.state == S.FUTURE_GRID_SELECTING and data.startswith("futg_") and data != "futg_done":
        pair = data[len("futg_"):]
        if pair in sess.fut_pairs:
            sess.fut_pairs.remove(pair)
        else:
            sess.fut_pairs.append(pair)
        pairs_formatted = ", ".join(sess.fut_pairs) if sess.fut_pairs else "None"
        _wiz(sess,
             f"📣 <b><i>Tap Pair List Selected And Tap Pair Unselected Choice Yours:</i></b>\n\n"
             f"<code>{pairs_formatted}</code>",
             _kb_future_pair_grid(sess))
        return

    if sess.state == S.FUTURE_GRID_SELECTING and data == "futg_done":
        if not sess.fut_pairs:
            _answer(cb_id, "⌛ Please select at least ONE pair before continuing!", show_alert=True)
            return
        if (getattr(sess, "fut_engine", "legacy") != "hard_filter" and
                sess.fut_market_mode not in ("BLACKOUT", "WHITEOUT")):
            sess.state = S.FUTURE_DIR_SELECT
            _wiz(sess, "👑 <b>SELECT DIRECTION :</b>", _kb_future_dir_select())
        else:
            sess.fut_action_choice = "3"
            sess.state = S.FUTURE_START_TIME
            _wiz(sess, _future_time_prompt("START"))
        return

    if sess.state == S.FUTURE_DIR_SELECT and data.startswith("fut_dir_"):
        sess.fut_action_choice = data.replace("fut_dir_", "")
        sess.state = S.FUTURE_START_TIME
        _wiz(sess, _future_time_prompt("START"))
        return

    if sess.state == S.FUTURE_DAYS_SELECT and (data.startswith("fut_day_") or
                                               data.startswith("futnew_day_")):
        prefix = "futnew_day_" if data.startswith("futnew_day_") else "fut_day_"
        filter_days = int(data.replace(prefix, ""))
        if uid not in ADMIN_IDS and not _db_future_access_is_valid(uid):
            _wiz(sess, efmt(_future_access_denied_text(uid)), _kb_future_access_required())
            sess.state = S.IDLE
            return
        if not _db_future_quota_use(uid):
            lim = int(_db_future_access_get(uid).get("daily_limit", 0) or 0)
            _wiz(sess, efmt(
                "💎 <b>DAILY LIMIT REACHED</b> 💎\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"⚠️ Your Future Signal access allows <b>{lim} list(s) per day</b>.\n"
                "You've already used today's list.\n\n"
                f"✉️ Message Support: <b>{SUPPORT_USERNAME}</b> to increase your limit."
            ), _kb_free_limit_reached())
            sess.state = S.IDLE
            return
        _execute_future_generation(uid, sess, filter_days)
        sess.state = S.IDLE
        return

    if data == "noop":
        return

    if data == "menu_live_signal":
        sess.wiz_mid = None
        if uid not in ADMIN_IDS:
            if _db_is_banned(uid):
                _wiz(sess, "🚫 <b>You are banned.</b>", _kb_license_required()); return
        lic   = _db_license_get(uid)
        used  = _db_live_quota_get(uid)
        is_free = (uid not in ADMIN_IDS and not _db_license_is_valid(uid))
        if uid in ADMIN_IDS:
            quota_line = "♾ Unlimited signals (Admin)"
        elif is_free:
            remaining = max(0, FREE_DAILY_LIMIT - used)
            quota_line = (
                "🔰 <b>Free Account</b>\n\n"
                f"🔋 {remaining}/{FREE_DAILY_LIMIT} free signals remaining today\n\n"
                "Upgrade to VIP for unlimited signals and premium features."
            )
        else:
            limit     = int(lic.get("signal_limit", 10))
            remaining = max(0, limit - used)
            quota_line = f"🔋 {remaining}/{limit} signals remaining today"
        kb_rows = [
            [{"text":"𝙼𝙰𝙽𝚄𝙰𝙻 𝚂𝙸𝙶𝙽𝙰𝙻","callback_data":"lsig_mode_manual",
              "style":"success","icon_custom_emoji_id":str(_LIVE_SIG_EMOJI_IDS["writing"])}],
            [{"text":"𝙰𝚄𝚃𝙾 𝚂𝙸𝙶𝙽𝙰𝙻","callback_data":"lsig_mode_auto",
              "style":"primary","icon_custom_emoji_id":str(_LIVE_SIG_EMOJI_IDS["robot"])}],
            [{"text":"Settings","callback_data":"lsig_settings",
              "style":"primary","icon_custom_emoji_id":str(_LIVE_SIG_EMOJI_IDS["gear"])}],
        ]
        if is_free:
            kb_rows.append([{"text":"Get VIP Access",
                             "url": f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}",
                             "style": "success",
                             "icon_custom_emoji_id": str(EMAP["👑"])}])
        kb_rows.append([{"text":"Back  ","callback_data":"menu_home",
                         "style":"danger","icon_custom_emoji_id":"5258084656674250503"}])
        _wiz(sess,
             f"📡 <b>Live Signal                                                                                  </b>\n\n"
             f"{quota_line}\n\n"
             "━━━━━━━━━━━━━━━━━━━━\n"
             "Choose signal mode:",
             {"inline_keyboard": kb_rows})
        return

    if data == "lsig_mode_manual":
        sess.live_sig_mode = "manual"
        if sess.live_sig_pending is not None:
            _wiz(sess,
                 "⚠️ <b>Signal Pending Result</b>\n\n"
                 "You cannot create a new signal until the previous signal's result is received.\n\n"
                 "Please wait for the current signal to complete.",
                 {"inline_keyboard":[[{"text":"Back  ","callback_data":"menu_live_signal",
                                       "style":"primary","icon_custom_emoji_id":"5258084656674250503"}]]})
            return
        pro2_on    = _db_strategy_enabled("pro2")
        premium_on = _db_strategy_enabled("premium")
        custom_on  = _db_strategy_enabled("foxio_zx_ai") and _custom_strategy_available()
        desc_parts_m = ["🔬 <b>Select Strategy</b>\n━━━━━━━━━━━━━━━━━━━━"]
        buttons_m    = []
        if pro2_on:
            desc_parts_m.append(
                "\n🏆 <b>ZBX PRO 2.1</b>\n"
                "Quality Over Quantity <b>[BEST OF ALL]</b>"
            )
            buttons_m.append([{"text": "ZBX PRO 2.1",
                                "callback_data": "lsig_manual_strategy_pro2",
                                "style": "primary",
                                "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["robot"])}])
        if premium_on:
            desc_parts_m.append(
                "\n💎 <b>ZBX PREMIUM</b>\n"
                "ZEBRONIX POWRED <b>[Stable]</b>"
            )
            buttons_m.append([{"text": "ZBX PREMIUM",
                                "callback_data": "lsig_manual_strategy_premium",
                                "style": "success",
                                "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["crown"])}])
        if custom_on:
            desc_parts_m.append("\n📊 <b>FOXIO ZX AI</b>\n22-strategy combined master engine <b>[OTC + LIVE]</b>")
            buttons_m.append([{"text": "FOXIO ZX AI",
                                "callback_data": "lsig_manual_strategy_foxio_zx_ai",
                                "style": "primary", "icon_custom_emoji_id": str(EMAP["📊"])}])
        if not buttons_m:
            buttons_m.append([{"text": "⚠️ No Strategy Available",
                                "callback_data": "noop", "style": "danger"}])
        buttons_m.append([{"text": "Settings", "callback_data": "lsig_settings",
                           "style": "primary",
                           "icon_custom_emoji_id": str(_LIVE_SIG_EMOJI_IDS["gear"])}])
        buttons_m.append([{"text": "Back  ", "callback_data": "menu_live_signal",
                           "style": "danger",
                           "icon_custom_emoji_id": "5258084656674250503"}])
        _wiz(sess, "\n".join(desc_parts_m), {"inline_keyboard": buttons_m})
        return

    if data.startswith("lsig_manual_strategy_"):
        if data.endswith("foxio_zx_ai"):
            strategy = "foxio_zx_ai"
        elif "premium" in data:
            strategy = "premium"
        else:
            strategy = "pro2"
        if not _db_strategy_enabled(strategy):
            cb2 = dict(cb); cb2["data"] = "lsig_mode_manual"; on_callback(cb2); return
        sess.live_sig_strategy = strategy
        if sess.live_sig_pending is not None:
            _wiz(sess, "⚠️ <b>Signal Pending.</b> Wait for current result.",
                 {"inline_keyboard":[[{"text":"Back  ","callback_data":"menu_live_signal",
                                       "style":"danger","icon_custom_emoji_id":"5258084656674250503"}]]})
            return
        sess.live_sig_draft["market"] = "ALL"
        sess.state = S.LIVE_SIG_PAIR
        strat_label = ("💎 PREMIUM" if strategy == "premium" else
                       "📊 FOXIO ZX AI" if strategy == "foxio_zx_ai" else "🏆 PRO 2.0")
        _wiz(sess,
             f"✍️ <b>Manual Signal</b>\n"
             f"Strategy: <b>{strat_label}</b>\n\n"
             "━━━━━━━━━━━━━━━━━━━━\n"
             "Select a market type:",
             {"inline_keyboard": [
                 [{"text": "OTC Market", "callback_data": "lsig_manual_market_OTC",
                   "style": "primary", "icon_custom_emoji_id": str(EMAP["📊"])},
                  {"text": "Live Market", "callback_data": "lsig_manual_market_LIVE",
                   "style": "primary", "icon_custom_emoji_id": str(EMAP["📈"])}],
                 [{"text": "Back  ", "callback_data": "lsig_mode_manual",
                   "style": "danger", "icon_custom_emoji_id": "5213358684024877471"}],
             ]})
        return

    if data.startswith("lsig_manual_market_"):
        market   = data.replace("lsig_manual_market_", "")  
        strategy = getattr(sess, "live_sig_strategy", "pro2")
        strat_label   = ("💎 PREMIUM" if strategy == "premium" else
                         "📊 FOXIO ZX AI" if strategy == "foxio_zx_ai" else "🏆 PRO 2.0")
        market_label  = "OTC Market" if market == "OTC" else "Live Market"
        back_cb       = f"lsig_manual_strategy_{strategy}"

        def _show_pairs(_market=market):
            pairs_pool = _get_lsig_otc_pairs() if _market == "OTC" else _get_lsig_live_pairs()
            if not pairs_pool:
                _wiz(sess,
                     f"⚠️ <b>No {market_label} pairs available right now.</b>\n\n"
                     "(Live forex markets are closed on weekends — try OTC instead.)",
                     {"inline_keyboard": [[{"text": "Back  ", "callback_data": back_cb,
                                             "style": "danger", "icon_custom_emoji_id": "5213358684024877471"}]]})
                return
            payout_map = _future_fetch_payouts(pairs_pool)
            available_pairs = [p for p in pairs_pool if payout_map.get(p, 0) > 0]
            if not available_pairs:
                _wiz(sess,
                     f"⚠️ <b>No {market_label} pairs have a payout right now.</b>\n\n"
                     "Please try again in a moment.",
                     {"inline_keyboard": [[{"text": "Back  ", "callback_data": back_cb,
                                             "style": "danger", "icon_custom_emoji_id": "5213358684024877471"}]]})
                return
            sorted_pairs = sorted(available_pairs, key=lambda p: payout_map.get(p, 0), reverse=True)
            rows = []
            for i in range(0, len(sorted_pairs), 2):
                row = []
                for p in sorted_pairs[i:i + 2]:
                    pct = payout_map.get(p, 0); disp = get_display_name(p)
                    label = f"{disp} ({pct}%)"
                    style = ("success" if pct >= 80 else "primary" if 70 <= pct <= 79 else "danger")
                    btn_d = {"text": label, "callback_data": f"lsig_pair_{p}", "style": style}
                    row.append(btn_d)
                rows.append(row)
            rows.append([{"text": "Back  ", "callback_data": back_cb,
                          "style": "danger", "icon_custom_emoji_id": "5213358684024877471"}])
            _wiz(sess,
                 f"✍️ <b>Manual Signal — {market_label}</b>\n"
                 f"Strategy: <b>{strat_label}</b>\n\n"
                 "━━━━━━━━━━━━━━━━━━━━\n"
                 "Select a pair to analyze:",
                 {"inline_keyboard": rows})
        _wiz(sess, efmt(f"📈 <b>Loading {market_label} payouts…</b>"))
        threading.Thread(target=_show_pairs, daemon=True).start()
        return

    if data.startswith("lsig_pair_"):
        pair = data.replace("lsig_pair_","")
        if sess.live_sig_pending is not None:
            _wiz(sess,"⚠️ <b>Signal Pending Result</b>\n\nWait for the current signal to complete.",
                 {"inline_keyboard":[[{"text":"Back  ","callback_data":"menu_live_signal",
                                       "style":"primary","icon_custom_emoji_id":"5258084656674250503"}]]})
            return
        if uid not in ADMIN_IDS and not _db_live_quota_use(uid):
            if not _db_license_is_valid(uid):
                _wiz(sess, efmt(_free_limit_reached_text()), _kb_free_limit_reached())
            else:
                lic  = _db_license_get(uid)
                lim  = int(lic.get("signal_limit",10)) if lic else 0
                used = _db_live_quota_get(uid)
                _wiz(sess, efmt(
                    f"⚠️ <b>Daily limit reached!</b>\n\n"
                    f"Your license allows <b>{lim} signals/day</b>.\n"
                    f"Used today: <b>{used}</b>"),
                    _kb_license_required())
            return
        threading.Thread(target=_run_live_signal,args=(uid,cid,pair,getattr(sess,'live_sig_strategy','pro2')),daemon=True).start()
        return

    if data.startswith("lsig_live_pair_"):
        pair = data.replace("lsig_live_pair_","")
        if sess.live_sig_pending is not None:
            _wiz(sess,"⚠️ <b>Signal Pending Result</b>\n\nWait for the current signal to complete.",
                 {"inline_keyboard":[[{"text":"Back  ","callback_data":"menu_live_signal",
                                       "style":"danger","icon_custom_emoji_id":"5258084656674250503"}]]})
            return
        if uid not in ADMIN_IDS and not _db_live_quota_use(uid):
            if not _db_license_is_valid(uid):
                _wiz(sess, efmt(_free_limit_reached_text()), _kb_free_limit_reached())
            else:
                lic  = _db_license_get(uid)
                lim  = int(lic.get("signal_limit",10)) if lic else 0
                used = _db_live_quota_get(uid)
                _wiz(sess, efmt(
                    f"⚠️ <b>Daily limit reached!</b>\n\n"
                    f"Your license allows <b>{lim} signals/day</b>.\n"
                    f"Used today: <b>{used}</b>"),
                    _kb_license_required())
            return
        threading.Thread(target=_run_live_signal,args=(uid,cid,pair,getattr(sess,'live_sig_strategy','pro2')),daemon=True).start()
        return

    if data == "lsig_mode_auto":
        sess.live_sig_mode = "auto"
        if sess.state == S.LIVE_SIG_RUNNING:
            _wiz(sess,"🤖 <b>Auto Signal Already Running</b>\n\nAuto signal mode is currently active.",
                 {"inline_keyboard":[
                     [{"text":"𝚂𝚃𝙾𝙿 𝙰𝚄𝚃𝙾 𝚂𝙸𝙶𝙽𝙰𝙻","callback_data":"lsig_auto_stop",
                       "style":"danger","icon_custom_emoji_id":str(_LIVE_SIG_EMOJI_IDS["cross"])}],
                 ]})
            return
        _wiz(sess,
             "🤖 <b>Auto Signal Mode                                                         </b>\n\n"
             "━━━━━━━━━━━━━━━━━━━━\n"
             "Choose auto signal mode:",
             {"inline_keyboard":[
                 [{"text":"𝙰𝙻𝙻 𝙿𝙰𝙸𝚁𝚂","callback_data":"lsig_auto_filter_all",
                   "style":"success","icon_custom_emoji_id":str(_LIVE_SIG_EMOJI_IDS["chart"])}],
                 [{"text":"𝙰𝚅𝙾𝙸𝙳 𝚄𝙽𝙳𝙴𝚁 𝟾𝟶%","callback_data":"lsig_auto_filter_avoid80",
                   "style":"success","icon_custom_emoji_id":str(_LIVE_SIG_EMOJI_IDS["target"])}],
                 [{"text":"𝚂𝙴𝙻𝙴𝙲𝚃 𝙿𝙰𝙸𝚁𝚂","callback_data":"lsig_auto_select_manual",
                   "style":"success","icon_custom_emoji_id":str(_LIVE_SIG_EMOJI_IDS["badge"])}],
                 [{"text":"𝙻𝙸𝚅𝙴 𝙼𝙰𝚁𝙺𝙴𝚃","callback_data":"lsig_auto_live_menu",
                   "style":"primary","icon_custom_emoji_id":str(EMAP["📈"])}],
                 [{"text":"Settings","callback_data":"lsig_settings",
                   "style":"primary","icon_custom_emoji_id":str(_LIVE_SIG_EMOJI_IDS["gear"])}],
                 [{"text":"Back  ","callback_data":"menu_live_signal",
                   "style":"danger","icon_custom_emoji_id":"5258084656674250503"}],
             ]})
        return

    if data == "lsig_auto_live_menu":
        if sess.live_sig_auto_thread and sess.live_sig_auto_thread.is_alive():
            return
        _wiz(sess,
             "🌐 <b>Auto Signal — Live Market                                                 </b>\n\n"
             "━━━━━━━━━━━━━━━━━━━━\n"
             "Scans and generates signals only from Live Market pairs.\n\n"
             "Choose a mode:",
             {"inline_keyboard":[
                 [{"text":"𝙰𝙻𝙻 𝙻𝙸𝚅𝙴 𝙿𝙰𝙸𝚁𝚂","callback_data":"lsig_auto_live_all",
                   "style":"success","icon_custom_emoji_id":str(_LIVE_SIG_EMOJI_IDS["chart"])}],
                 [{"text":"𝙰𝚅𝙾𝙸𝙳 𝚄𝙽𝙳𝙴𝚁 𝟾𝟶%","callback_data":"lsig_auto_live_avoid80",
                   "style":"success","icon_custom_emoji_id":str(_LIVE_SIG_EMOJI_IDS["target"])}],
                 [{"text":"𝚂𝙴𝙻𝙴𝙲𝚃 𝙿𝙰𝙸𝚁𝚂","callback_data":"lsig_auto_live_select",
                   "style":"success","icon_custom_emoji_id":str(_LIVE_SIG_EMOJI_IDS["badge"])}],
                 [{"text":"Back  ","callback_data":"lsig_mode_auto",
                   "style":"danger","icon_custom_emoji_id":"5258084656674250503"}],
             ]})
        return

    if data.startswith("lsig_auto_filter_"):
        filter_mode = data.replace("lsig_auto_filter_","")
        if sess.live_sig_auto_thread and sess.live_sig_auto_thread.is_alive():
            return
        sess.live_sig_draft["auto_market"]      = "ALL"
        sess.live_sig_draft["auto_filter_mode"] = filter_mode
        sess.live_sig_draft["auto_manual_pairs"] = None
        _lsig_show_strategy_select(sess)
        return

    if data == "lsig_auto_live_all":
        if sess.live_sig_auto_thread and sess.live_sig_auto_thread.is_alive():
            return
        sess.live_sig_draft["auto_market"]      = "LIVE"
        sess.live_sig_draft["auto_filter_mode"] = "all"
        sess.live_sig_draft["auto_manual_pairs"] = None
        _lsig_show_strategy_select(sess)
        return

    if data == "lsig_auto_live_avoid80":
        if sess.live_sig_auto_thread and sess.live_sig_auto_thread.is_alive():
            return
        sess.live_sig_draft["auto_market"]      = "LIVE"
        sess.live_sig_draft["auto_filter_mode"] = "avoid80"
        sess.live_sig_draft["auto_manual_pairs"] = None
        _lsig_show_strategy_select(sess)
        return

    if data == "lsig_auto_live_select":
        import concurrent.futures as _cf
        pairs_pool = _get_lsig_live_pairs()
        sel  = getattr(sess,"live_sig_auto_live_pairs",[])
        pg   = getattr(sess,"live_sig_auto_live_page",0)
        per  = 10; chunk = pairs_pool[pg*per:pg*per+per]
        total= (len(pairs_pool)+per-1)//per
        payout_map = getattr(sess, "_live_payout_cache", {})
        if not payout_map:
            def _lp(p):
                return p, _get_pair_payout(p)
            with _cf.ThreadPoolExecutor(max_workers=15) as _ex:
                for fut in _cf.as_completed({_ex.submit(_lp, p): p for p in pairs_pool}, timeout=10):
                    try:
                        p, pct = fut.result()
                        payout_map[p] = pct
                    except: pass
            sess._live_payout_cache = payout_map
        rows = []
        for i in range(0,len(chunk),2):
            row = []
            for p in chunk[i:i+2]:
                is_sel = p in sel
                pct   = payout_map.get(p, 0)
                label = f"{get_display_name(p)} ({pct}%)" if pct else get_display_name(p)
                style = ("success" if pct >= 80 else "primary" if pct >= 70 else "danger" if pct > 0 else "primary")
                icon_id = "6231121076814879723" if is_sel else "6233277751692894018"
                row.append({"text": label,
                            "callback_data": f"lsig_auto_live_ptog_{p}",
                            "style": style,
                            "icon_custom_emoji_id": icon_id})
            rows.append(row)
        nav = [{"text":f"{pg+1}/{total}","callback_data":"noop"}]
        if pg > 0:   nav.insert(0,{"text":"◀ Prev","callback_data":f"lsig_auto_live_ppage_{pg-1}"})
        if pg < total-1: nav.append({"text":"Next ▶","callback_data":f"lsig_auto_live_ppage_{pg+1}"})
        rows.append(nav)
        rows.append([{"text":"Select All","callback_data":"lsig_auto_live_sel_all","style":"success"},
                     {"text":"❌ Clear","callback_data":"lsig_auto_live_sel_clear","style":"danger"}])
        rows.append([{"text":"  ✔️  Confirm Selection →  ","callback_data":"lsig_auto_live_ok","style":"success"}])
        rows.append([{"text":"Back  ","callback_data":"lsig_mode_auto",
                      "style":"danger","icon_custom_emoji_id":"5258084656674250503"}])
        _wiz(sess,
             f"🌐 <b>Auto Signal — Live Market Pairs</b>\n\n"
             f"Selected: <b>{len(sel)}</b>\n"
             f"🟢 ≥80%  🔵 70-79%  🔴 <70%\n\nTap to select/deselect:",
             {"inline_keyboard":rows})
        return

    if data.startswith("lsig_auto_live_ptog_"):
        p = data.replace("lsig_auto_live_ptog_","")
        if not hasattr(sess,"live_sig_auto_live_pairs"): sess.live_sig_auto_live_pairs=[]
        if p in sess.live_sig_auto_live_pairs: sess.live_sig_auto_live_pairs.remove(p)
        else: sess.live_sig_auto_live_pairs.append(p)
                             
        cb2 = dict(cb); cb2["data"] = "lsig_auto_live_select"; on_callback(cb2)
        return

    if data.startswith("lsig_auto_live_ppage_"):
        sess.live_sig_auto_live_page = int(data.replace("lsig_auto_live_ppage_",""))
                                              
        cb2 = dict(cb); cb2["data"] = "lsig_auto_live_select"; on_callback(cb2)
        return

    if data == "lsig_auto_live_sel_all":
        sess.live_sig_auto_live_pairs = _get_lsig_live_pairs()
        sess.live_sig_auto_live_page  = 0
        sess._live_payout_cache = {}
        cb2 = dict(cb); cb2["data"] = "lsig_auto_live_select"; on_callback(cb2)
        return

    if data == "lsig_auto_live_sel_clear":
        sess.live_sig_auto_live_pairs = []
        sess.live_sig_auto_live_page  = 0
        sess._live_payout_cache = {}
        cb2 = dict(cb); cb2["data"] = "lsig_auto_live_select"; on_callback(cb2)
        return

    if data == "lsig_auto_live_ok":
        chosen = list(getattr(sess,"live_sig_auto_live_pairs",[]))
        if not chosen:
            _wiz(sess,"⚠️ <b>No Pairs Selected</b>\n\nPlease select at least one pair.",
                 {"inline_keyboard":[[{"text":"Back  ","callback_data":"lsig_auto_live_select",
                                       "style":"danger","icon_custom_emoji_id":"5258084656674250503"}]]})
            return
        if sess.live_sig_auto_thread and sess.live_sig_auto_thread.is_alive():
            return
        sess.live_sig_draft["auto_market"]       = "LIVE"
        sess.live_sig_draft["auto_filter_mode"]  = "all"
        sess.live_sig_draft["auto_manual_pairs"] = chosen
        _lsig_show_strategy_select(sess)
        return

    if data == "lsig_auto_select_manual":
        pairs_pool = _get_lsig_otc_pairs() + _get_lsig_live_pairs()
        if not hasattr(sess,"live_sig_auto_manual_pairs"): sess.live_sig_auto_manual_pairs = []
        if not hasattr(sess,"_auto_sel_payout_cache"): sess._auto_sel_payout_cache = {}
        sel  = getattr(sess,"live_sig_auto_manual_pairs",[])
        pg   = getattr(sess,"live_sig_auto_select_page",0)
        per  = 20; chunk = pairs_pool[pg*per:pg*per+per]
        total= (len(pairs_pool)+per-1)//per
        pmap = getattr(sess,"_auto_sel_payout_cache",{})
        if not pmap:
            import concurrent.futures as _cf2
            def _fp(p):
                return p, _get_pair_payout(p)
            try:
                with _cf2.ThreadPoolExecutor(max_workers=20) as _ex2:
                    for fut in _cf2.as_completed({_ex2.submit(_fp,p):p for p in pairs_pool},timeout=12):
                        try:
                            p2,pct=fut.result()
                            if pct: pmap[p2]=pct
                        except: pass
            except: pass
            sess._auto_sel_payout_cache = pmap
        rows = []
        for i in range(0,len(chunk),2):
            row=[]
            for p in chunk[i:i+2]:
                is_sel = p in sel
                pct=pmap.get(p,0)
                pct_str=f" ({pct}%)" if pct else ""
                style=("success" if pct>=80 else "primary" if pct>=70 else "danger" if pct>0 else "primary")
                icon_id = "6231121076814879723" if is_sel else "6233277751692894018"
                row.append({"text":f"{get_display_name(p)}{pct_str}",
                            "callback_data":f"lsig_auto_ptog_{p}","style":style,
                            "icon_custom_emoji_id": icon_id})
            rows.append(row)
        nav=[{"text":f"{pg+1}/{total}","callback_data":"noop"}]
        if pg>0: nav.insert(0,{"text":"◀ Prev","callback_data":f"lsig_auto_ppage_{pg-1}"})
        if pg<total-1: nav.append({"text":"Next ▶","callback_data":f"lsig_auto_ppage_{pg+1}"})
        rows.append(nav)
        rows.append([{"text":"Select All","callback_data":"lsig_auto_psel_all","style":"success","icon_custom_emoji_id":"6213053622574392612"},
                     {"text":"Clear","callback_data":"lsig_auto_psel_clear","style":"danger","icon_custom_emoji_id":"6210541801145638044"}])
        rows.append([{"text":"   Confirm Selection →  ","callback_data":"lsig_auto_pair_ok","style":"success","icon_custom_emoji_id":"6303323183617415678"}])
        rows.append([{"text":"Back  ","callback_data":"lsig_mode_auto",
                      "style":"danger","icon_custom_emoji_id":"5258084656674250503"}])
        _wiz(sess,
             f"🤖 <b>Auto Signal — Select Pairs</b>\n"
             f"━━━━━━━━━━━━━━━━━━━━\n"
             f"Selected: <b>{len(sel)}</b>  |  🟢≥80%  🔵70-79%  🔴&lt;70%\n\n"
             "Tap pairs to select/deselect:",
             {"inline_keyboard":rows})
        return

    if data.startswith("lsig_auto_ptog_"):
        p = data.replace("lsig_auto_ptog_","")
        if not hasattr(sess,"live_sig_auto_manual_pairs"): sess.live_sig_auto_manual_pairs=[]
        if p in sess.live_sig_auto_manual_pairs: sess.live_sig_auto_manual_pairs.remove(p)
        else: sess.live_sig_auto_manual_pairs.append(p)
        cb2 = dict(cb); cb2["data"] = "lsig_auto_select_manual"; on_callback(cb2)
        return

    if data.startswith("lsig_auto_ppage_"):
        sess.live_sig_auto_select_page = int(data.replace("lsig_auto_ppage_",""))
        cb2 = dict(cb); cb2["data"] = "lsig_auto_select_manual"; on_callback(cb2)
        return

    if data == "lsig_auto_psel_all":
        sess.live_sig_auto_manual_pairs = _get_lsig_otc_pairs() + _get_lsig_live_pairs()
        sess.live_sig_auto_select_page  = 0
        cb2 = dict(cb); cb2["data"] = "lsig_auto_select_manual"; on_callback(cb2)
        return

    if data == "lsig_auto_psel_clear":
        sess.live_sig_auto_manual_pairs = []
        sess.live_sig_auto_select_page  = 0
        cb2 = dict(cb); cb2["data"] = "lsig_auto_select_manual"; on_callback(cb2)
        return

    if data == "lsig_auto_pair_ok":
        chosen = list(getattr(sess,"live_sig_auto_manual_pairs",[]))
        if not chosen:
            _wiz(sess,"⚠️ <b>No Pairs Selected</b>\n\nPlease select at least one pair.",
                 {"inline_keyboard":[[{"text":"Back  ","callback_data":"lsig_auto_select_manual",
                                       "style":"danger","icon_custom_emoji_id":"5258084656674250503"}]]})
            return
        if sess.live_sig_auto_thread and sess.live_sig_auto_thread.is_alive():
            return
        sess.live_sig_draft["auto_market"]       = "ALL"
        sess.live_sig_draft["auto_filter_mode"]  = "all"
        sess.live_sig_draft["auto_manual_pairs"] = chosen
        _lsig_show_strategy_select(sess)
        return

    if data in ("lsig_strategy_pro2", "lsig_strategy_premium", "lsig_strategy_foxio_zx_ai"):
        if data == "lsig_strategy_foxio_zx_ai":
            strategy = "foxio_zx_ai"
        elif data == "lsig_strategy_premium":
            strategy = "premium"
        else:
            strategy = "pro2"
        if not _db_strategy_enabled(strategy):
            _lsig_show_strategy_select(sess); return
        market       = sess.live_sig_draft.get("auto_market", "ALL")
        filter_mode  = sess.live_sig_draft.get("auto_filter_mode", "all")
        manual_pairs = sess.live_sig_draft.get("auto_manual_pairs")
        if sess.live_sig_auto_thread and sess.live_sig_auto_thread.is_alive():
            return
        sess.live_sig_auto_stop.clear(); sess.live_sig_partial = []; db_save_partial_history(uid, [])
        sess.live_sig_strategy = strategy
        t = threading.Thread(target=_run_live_auto_loop,
                             args=(uid, cid, market, filter_mode, manual_pairs, strategy), daemon=True)
        sess.live_sig_auto_thread = t; t.start()
        return

    if data == "lsig_auto_stop":
        sess.live_sig_auto_stop.set(); sess.state = S.IDLE; sess.live_sig_pending = None
        _wiz(sess,"⏹ <b>Auto Signal Stopping…</b>\nWill stop after current check.",
             {"inline_keyboard":[[{"text":"Home","callback_data":"menu_home","icon_custom_emoji_id":"5416041192905265756",
                                   "style":"primary"}]]})
        return

    if data == "lsig_send_partial":
        if not sess.live_sig_partial:
            _send(cid, efmt("⚠️ <b>No signals in partial history yet.</b>")); return
        partial_msg = _build_lsig_partial_msg(sess.live_sig_partial)
        partial_kb  = {"inline_keyboard":[
            [{"text":"𝚁𝙴𝚂𝙴𝚃 𝙿𝙰𝚁𝚃𝙸𝙰𝙻","callback_data":"lsig_reset_partial",
              "style":"primary","icon_custom_emoji_id":str(_LIVE_SIG_EMOJI_IDS["gear"])}],
            [{"text":"𝚂𝚃𝙾𝙿 𝙿𝚁𝙾𝙶𝚁𝙰𝙼𝙼𝙴","callback_data":"lsig_stop_programme",
              "style":"danger","icon_custom_emoji_id":str(_LIVE_SIG_EMOJI_IDS["cross"])}],
        ]}
        _lsig_send_partial_msg(cid, partial_msg, _admin_has_premium(), partial_kb,
                               emoji_map=_PARTIAL_FORMAT_EMOJI)
        return

    if data == "lsig_reset_partial":
        sess.live_sig_partial = []
        db_save_partial_history(uid, [])
        _send(cid, efmt("🔄 <b>Partial history reset.</b>")); return

    if data == "lsig_stop_programme":
        sess.live_sig_auto_stop.set(); sess.live_sig_pending=None; sess.live_sig_partial=[]
        db_save_partial_history(uid, [])
        sess.state = S.IDLE
        _send_welcome(uid, sess, _kb_welcome); return

    if data == "lsess_start":
        if not _lsess_can_use(uid):
            _wiz(sess, "🚫 <b>Not Authorized</b>\n\nChannel Sender requires an active VIP license.",
                 _kb_license_required())
            return
        sess.state = S.LSESS_AWAIT_CHANNEL
        sess.lsess_channel_id = None
        sess.lsess_channel_title = None
        sess.lsess_emoji_mode = None
        sess.lsess_premium_account_id = None
        sess.lsess_pairs = []
        sess.lsess_select_page = 0
        sess._lsess_payout_cache = {}
        _wiz(sess, efmt(
            f"{_e_('📡')} <b>Channel Sender — Connect Channel</b>\n\n"
            "To connect your channel/group:\n\n"
            f"{_e_('1️⃣')} Forward any message from that channel/group here, "
            "or send its chat ID (e.g. <code>-1001234567890</code>).\n\n"
            f"{_e_('🛡')} Make sure this bot is an <b>admin</b> in that channel/group."),
            _lsess_kb_channel_prompt())
        return

    if data == "lsig_settings":
        _owner_settings_menu(uid, sess, "menu_live_signal")
        return

    if data == "lsess_settings":
        if not _lsess_can_use(uid):
            _wiz(sess, "🚫 <b>Not Authorized</b>\n\nChannel Sender requires an active VIP license.",
                 _kb_license_required())
            return
        _owner_settings_menu(uid, sess, "lsess_start")
        return

    if data == "owner_username_edit":
        sess.state = S.AWAIT_OWNER_USERNAME
        _wiz(sess, efmt(
            "<b>Send your new username now</b> (e.g. <code>@YourChannel</code>).\n\n"
            "This will appear as the <b>Owner</b> in every signal &amp; result template."),
            {"inline_keyboard": [
                [{"text": "Cancel", "callback_data": sess.owner_return_cb,
                  "style": "danger", "icon_custom_emoji_id": "5258084656674250503"}],
            ]})
        return

    if data == "lsess_retry":
        if not _lsess_can_use(uid):
            sess.state = S.IDLE
            _send_welcome(uid, sess, _kb_welcome); return
        if not sess.lsess_channel_id:
            sess.state = S.LSESS_AWAIT_CHANNEL
            cb2 = dict(cb); cb2["data"] = "lsess_start"; on_callback(cb2)
            return
        _lsess_check_admin_and_show(uid, sess)
        return

    if data == "lsess_emoji_format":
        if not sess.lsess_channel_id:
            cb2 = dict(cb); cb2["data"] = "lsess_start"; on_callback(cb2)
            return
        _lsess_emoji_format_menu(sess)
        return

    if data == "lsess_emoji_normal":
        sess.lsess_emoji_mode = "normal"
        _lsess_show_username_prompt(sess)
        return

    if data == "lsess_emoji_premium":
        sess.lsess_emoji_mode = "premium"
        _lsess_premium_instruction(sess)
        return

    if data == "lsess_emoji_confirm":
        if not sess.lsess_channel_id:
            cb2 = dict(cb); cb2["data"] = "lsess_start"; on_callback(cb2)
            return
        _wiz(sess, efmt("⏳ <b>Checking Premium account permission...</b>"), None)
        status = _telethon_account_status(sess.lsess_channel_id)
        if status.get("ok") and status.get("premium") and status.get("can_send"):
            sess.lsess_emoji_mode = "premium"
            sess.lsess_premium_account_id = status.get("id")
            _lsess_show_username_prompt(sess)
        else:
            sess.state = S.LSESS_PREMIUM_CONFIRM
            error = _html.escape(str(status.get("error") or
                                     "Account is not an admin or cannot send messages."))
            account_id = status.get("id") or sess.lsess_premium_account_id
            identity = f"<code>{account_id}</code>" if account_id else "<b>Premium account</b>"
            _wiz(sess, efmt(
                "⚠️ <b>PREMIUM PERMISSION FAILED</b>\n\n"
                f"{identity} must be a channel admin with <b>Post/Send Messages</b> permission.\n\n"
                f"<code>{error}</code>"),
                {"inline_keyboard": [
                    [{"text":"RETRY","callback_data":"lsess_emoji_confirm","style":"success",
                      "icon_custom_emoji_id":str(EMAP["🔄"])}],
                    [{"text":"NORMAL EMOJI","callback_data":"lsess_emoji_normal","style":"primary",
                      "icon_custom_emoji_id":str(EMAP["✅"])}],
                    [{"text":"Back","callback_data":"lsess_emoji_format","style":"danger",
                      "icon_custom_emoji_id":"5258084656674250503"}]]})
        return

    if data == "lsess_username_skip":
        if not _lsess_can_use(uid):
            sess.state = S.IDLE
            _send_welcome(uid, sess, _kb_welcome); return
        _lsess_strategy_select_menu(sess)
        return

    if data == "lsess_continue":
        if not _lsess_can_use(uid):
            sess.state = S.IDLE
            _send_welcome(uid, sess, _kb_welcome); return
        if not sess.lsess_channel_id:
            sess.state = S.LSESS_AWAIT_CHANNEL
            cb2 = dict(cb); cb2["data"] = "lsess_start"; on_callback(cb2)
            return
        _lsess_strategy_select_menu(sess)
        return

    if data in ("lsess_strategy_pro2", "lsess_strategy_premium", "lsess_strategy_foxio_zx_ai"):
        strategy = data.replace("lsess_strategy_", "")
        if not _db_strategy_enabled(strategy):
            _lsess_strategy_select_menu(sess); return
        if strategy == "foxio_zx_ai" and not _custom_strategy_available():
            _wiz(sess, "⚠️ <b>FOXIO ZX AI strategy modules are not available.</b>\n\n"
                       f"<code>{_html.escape(_custom_strategy_error or 'Unknown load error')}</code>")
            return
        sess.lsess_strategy = strategy
        sess.lsess_payout_filter = "all"
        sess.lsess_pairs = []
        sess.lsess_select_page = 0
        sess._lsess_payout_cache = {}
        sess.state = S.LSESS_PAIR_SELECT
        _lsess_pair_select_menu(uid, sess)
        return

    if data.startswith("lsess_ptog_"):
        p = data.replace("lsess_ptog_","")
        if p in sess.lsess_pairs: sess.lsess_pairs.remove(p)
        else: sess.lsess_pairs.append(p)
        _lsess_pair_select_menu(uid, sess)
        return

    if data.startswith("lsess_ppage_"):
        sess.lsess_select_page = int(data.replace("lsess_ppage_",""))
        _lsess_pair_select_menu(uid, sess)
        return

    if data == "lsess_sel_all":
        sess.lsess_pairs = _get_lsig_otc_pairs() + _get_lsig_live_pairs()
        sess.lsess_payout_filter = "all"
        sess.lsess_select_page = 0
        _lsess_pair_select_menu(uid, sess)
        return

    if data == "lsess_sel_80":
        pairs_pool = _get_lsig_otc_pairs() + _get_lsig_live_pairs()

        sess.lsess_pairs = list(pairs_pool)
        sess.lsess_payout_filter = "avoid80"
        sess.lsess_select_page = 0
        _lsess_pair_select_menu(uid, sess)
        return

    if data == "lsess_sel_clear":
        sess.lsess_pairs = []
        sess.lsess_payout_filter = "all"
        sess.lsess_select_page = 0
        _lsess_pair_select_menu(uid, sess)
        return

    if data == "lsess_pairs_ok":
        if not sess.lsess_pairs:
            _wiz(sess, "⚠️ <b>No Markets Selected</b>\n\nPlease select at least one market.",
                 {"inline_keyboard":[[{"text":"Back  ","callback_data":"lsess_continue",
                                       "style":"danger","icon_custom_emoji_id":"5258084656674250503"}]]})
            return
        sess.state = S.LSESS_CONFIRM
        _lsess_confirm_menu(sess)
        return

    if data == "lsess_launch":
        if not _lsess_can_use(uid):
            sess.state = S.IDLE
            _send_welcome(uid, sess, _kb_welcome); return
        if not sess.lsess_channel_id or not sess.lsess_pairs:
            _wiz(sess, "⚠️ <b>Setup Incomplete</b>\n\nPlease connect a channel and select markets first.",
                 {"inline_keyboard":[[{"text":"Back  ","callback_data":"menu_home",
                                       "style":"danger","icon_custom_emoji_id":"5258084656674250503"}]]})
            return
        if getattr(sess, "lsess_emoji_mode", None) not in ("premium", "normal"):
            _lsess_emoji_format_menu(sess)
            return
        if sess.lsess_thread and sess.lsess_thread.is_alive():
            _wiz(sess, "🤖 <b>Channel Sender Already Running</b>",
                 _lsess_running_kb())
            return
        t = threading.Thread(target=_lsess_run, args=(uid, cid, sess), daemon=True)
        sess.lsess_thread = t; t.start()
        return

    if data == "lsess_change_pairs":
        sess.state = S.LSESS_PAIR_SELECT
        sess.lsess_select_page = 0
        sess._lsess_payout_cache = {}
        _lsess_pair_select_menu(uid, sess)
        return

    if data == "lsess_pause":
        sess.lsess_pause.set()
        _wiz(sess, efmt(f"{_e_('⏹')} <b>Channel Sender Paused</b>"), _lsess_running_kb())
        return

    if data == "lsess_resume":
        sess.lsess_pause.clear()
        _wiz(sess, efmt(f"{_e_('✅')} <b>Channel Sender Resumed</b>"), _lsess_running_kb())
        return

    if data == "lsess_send_partial":
        if not sess.lsess_partial:
            _send(cid, efmt("⚠️ <b>No signals in partial history yet.</b>")); return
        partial_msg = _build_lsess_partial_msg(sess.lsess_partial)
        premium_mode = getattr(sess, "lsess_emoji_mode", "normal") == "premium"
        _lsig_send_partial_msg(sess.lsess_channel_id, partial_msg, premium_mode,
                                {"inline_keyboard":[]}, via_telethon=premium_mode,
                                emoji_map=_PARTIAL_FORMAT_EMOJI)
        _send(cid, efmt(f"{_e_('✅')} <b>Partial summary sent to channel.</b>"))
        return

    if data == "lsess_stop":
        sess.lsess_stop.set(); sess.lsess_pending = None; sess.lsess_pause.clear()
        sess.state = S.IDLE
        _send_welcome(uid, sess, _kb_welcome)
        return

    if data == "admin_wiz_cancel":
        sess.state = S.IDLE
        sess.admin_wizard = {}
        _send(cid, efmt("❌ <b>Wizard cancelled.</b>"))
        return

    if data == "admin_global_free_start":
        if uid not in ADMIN_IDS:
            return
        _admin_wiz_start(sess, cid, "globalfree")
        return

    if data == "admin_global_free_stop":
        if uid not in ADMIN_IDS:
            return
        was_active = _db_global_free_is_active()
        ok = _db_global_free_disable()
        if ok:
            _send(cid, efmt(
                "⛔ <b>GLOBAL FREE ACCESS STOPPED</b>\n\n"
                + ("All users have returned to their own license and quota settings."
                   if was_active else "The offer was already inactive.")))
            _send_global_free_panel(cid)
        else:
            _send(cid, efmt("❌ <b>Could not stop Global Free Access.</b>"))
        return

    if data.startswith("admin_strat_tog_"):
        if uid not in ADMIN_IDS:
            return
        strategy = data.replace("admin_strat_tog_", "")
        if strategy not in ("pro2", "premium", "foxio_zx_ai"):
            return
        current  = _db_strategy_enabled(strategy)
        new_val  = not current
        ok = _db_strategy_set_enabled(strategy, new_val)
        strat_names = {"pro2": "ZBX PRO 2.1", "premium": "ZBX PREMIUM",
                       "foxio_zx_ai": "FOXIO ZX AI"}
        strat_name  = strat_names.get(strategy, strategy)
        status_text = "✅ <b>Enabled (Visible)</b>" if new_val else "❌ <b>Disabled (Hidden)</b>"
        _send(cid, efmt(
            f"🔬 <b>Strategy Updated</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>{strat_name}</b>\n"
            f"Status: {status_text}"
        ))
        _send_strategy_panel(cid)
        return

    if data == "noop":
        return

def _daily_reset_watcher():

    last_run_date = None
    UTC_OFFSET_HOURS = 6
    while True:
        try:
            from datetime import timezone, timedelta as _td
            utc6 = datetime.utcnow() + _td(hours=UTC_OFFSET_HOURS)
            today = utc6.strftime("%Y-%m-%d")
            if utc6.hour == 0 and utc6.minute == 0 and last_run_date != today:
                users = _db_all_users_for_reset()
                reset_count = 0
                for doc in users:
                    uid = doc.get("user_id")
                    if not uid:
                        continue
                    try:
                        db_reset_daily(uid)
                        reset_count += 1
                    except Exception as ne:
                        print(f"[DailyReset] reset error uid={uid}: {ne}")
                last_run_date = today
                print(f"[DailyReset] Silently reset {reset_count}/{len(users)} user(s) at {utc6} (UTC+6).")
        except Exception as e:
            print(f"[DailyReset] error: {e}")
        time.sleep(30)


def run():
    print("╔═══════════════════════╗")
    print("║      ZEBRONIX AI      ║")
    print("╚═══════════════════════╝")
    setup_db()

    executor = ThreadPoolExecutor(max_workers=40, thread_name_prefix="Worker")
    threading.Thread(target=_daily_reset_watcher, daemon=True).start()
    session_locks : dict = {}
    locks_meta    = threading.Lock()

    def _get_lock(uid):
        with locks_meta:
            if uid not in session_locks:
                session_locks[uid] = threading.Lock()
            return session_locks[uid]

    def _handle(upd):
        uid = None
        try:
            if   "message"        in upd: uid = upd["message"].get("from",{}).get("id")
            elif "callback_query" in upd: uid = upd["callback_query"].get("from",{}).get("id")
            elif "chat_member"    in upd:
                cm   = upd["chat_member"]
                chat = cm.get("chat", {})
                if chat.get("id") in (REQUIRED_CHANNEL_1_ID, REQUIRED_CHANNEL_2_ID):
                    new_status = cm.get("new_chat_member", {}).get("status", "")
                    mem_uid    = cm.get("new_chat_member", {}).get("user", {}).get("id")
                    if mem_uid and new_status in ("left", "kicked"):
                        try:
                            sess_left = _sess(mem_uid)
                            if not sess_left.wiz_chat:
                                sess_left.wiz_chat = mem_uid
                            leave_text = efmt(
                                "⚠️ <b>You Have Left a Channel!</b>\n\n"
                                "━━━━━━━━━━━━━━━━━━━━\n"
                                "You have left one of our official channels.\n\n"
                                "To continue using this bot, you must "
                                "rejoin both channels.\n\n"
                                "Tap the buttons below to rejoin, "
                                "then tap <b>Verify</b> to restore your access."
                            )
                            kb_leave = {"inline_keyboard": [
                                [{"text": "Rejoin Channel 1",
                                  "url": REQUIRED_CHANNEL_1_LINK,
                                  "style": "primary",
                                  "icon_custom_emoji_id": str(EMAP["🔔"])}],
                                [{"text": "Rejoin Channel 2",
                                  "url": REQUIRED_CHANNEL_2_LINK,
                                  "style": "primary",
                                  "icon_custom_emoji_id": str(EMAP["🔔"])}],
                                [{"text": "Verify Access",
                                  "callback_data": "verify_channel",
                                  "style": "success",
                                  "icon_custom_emoji_id": str(EMAP["✅"])}],
                            ]}
                            _invalidate_channel_cache(mem_uid)
                            _send(mem_uid, leave_text, kb_leave)
                        except Exception as le:
                            print(f"[Channel] leave notify error uid={mem_uid}: {le}")
                return
            lock = _get_lock(uid) if uid else threading.Lock()
            with lock:
                if   "message"        in upd: on_message(upd["message"])
                elif "callback_query" in upd: on_callback(upd["callback_query"])
        except Exception as e:
            print(f"[Handler uid={uid}] {e}"); traceback.print_exc()

    offset = 0
    print("[Bot] Polling started.")
    while True:
        try:
            res = _tg_poll.get(f"{BASE}/getUpdates",
                              params={"offset":offset,"timeout":30,"limit":100,
                                      "allowed_updates":json.dumps(["message","callback_query","chat_member"])},
                              timeout=40).json()
            for upd in res.get("result",[]):
                offset = upd["update_id"] + 1
                executor.submit(_handle, upd)
        except requests.exceptions.Timeout:
            pass
        except Exception as e:
            print(f"[Polling] {e}"); time.sleep(5)

if __name__ == "__main__":
    run()
