

from __future__ import annotations

import json
import re
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from urllib.parse import urlencode

import requests

FF_WEEK_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

NEWS_GLOBAL_PAIRS: tuple[str, ...] = (
    "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "USD/CAD", "NZD/USD",
    "EUR/GBP", "EUR/JPY", "EUR/CHF", "EUR/AUD", "EUR/CAD", "EUR/NZD",
    "GBP/JPY", "GBP/CHF", "GBP/AUD", "GBP/CAD", "GBP/NZD",
    "AUD/JPY", "AUD/CHF", "AUD/CAD", "AUD/NZD",
    "CAD/JPY", "CAD/CHF", "CHF/JPY",
    "NZD/JPY", "NZD/CHF", "NZD/CAD",
    "XAU/USD",
)

NEWS_PAIRS_PER_PAGE = 8
NEWS_FILTERS = ("all", "high", "medium", "low")
NEWS_DAYS = (1, 2, 3)

_CURRENCY_FLAGS = {
    "USD": "🇺🇸", "EUR": "🇪🇺", "GBP": "🇬🇧", "JPY": "🇯🇵",
    "CHF": "🇨🇭", "CAD": "🇨🇦", "AUD": "🇦🇺", "NZD": "🇳🇿",
    "XAU": "🏅", "CNY": "🇨🇳",
}


_FF_COUNTRY_TO_CCY = {
    "USD": "USD", "EUR": "EUR", "GBP": "GBP", "JPY": "JPY",
    "CAD": "CAD", "AUD": "AUD", "NZD": "NZD", "CHF": "CHF",
    "CNY": "CNY", "CNH": "CNY",
}

_NEGATIVE_IF_HIGHER = (
    "unemployment", "jobless", "claims", "inventories", "inventory",
    "deficit", "debt",
)

NEWS_EMOJI_IDS = {

    "fire": 6264785189394717307,
    "calendar": 6102906733842144545,
    "clock": 5215484787325676090,
    "alarm": 5215484787325676090,
    "timer": 5382194935057372936,
    "trend_up": 6102644427304478726,
    "trend_down": 6102805248059906486,
    "up_arr": 6102644427304478726,
    "down_arr": 6102805248059906486,
    "list": 5258477770735885832,
    "refresh": 4956371914323920049,
    "robot": 5417909469319272937,
    "rocket": 6068700050928704109,
    "bolt": 5438571934210082705,
    "warn": 6276132901012640832,
    "writing": 5193004760994685438,
    "news": 5971837723676249096,
    "surprise": 6273865673676428425,
    "brain": 4958937938239947673,
    "check": 6267291337171670780,
    "crown": 6147893428186258508,
    "money": 6104726047628990417,

    "king": 6289747595153643743,       
    "fire2": 6339211745659197163,      
    "calendar2": 6143327564417998601, 
    "clock2": 5843618381361581907,     
    "gem": 5229173741451230931,        
    "world": 5316878305075404851,     
    "impact_high": 5888974760720732797,
    "warn2": 5462935376714802451,      
    "call_grn": 6231288370086026695, 
    "put_red": 6233323046417996962,    
    "hourglass": 6336632656452652003, 
    "stopwatch": 6231214251835397322,  
    "chart_up": 6246668128281959578,   
    "chart_down": 6224316916610108722, 
    "target": 5256131095094652290,     
    "money2": 6145667045989031906,  
    "impact_med": 6032988557503632139, 
    "impact_low": 5192887216329729431,
}

CURRENCY_EMOJI_IDS = {
    "CAD": 5222001124592071204,
    "USD": 5224321781321442532,
    "EUR": 5222108911091331711,
    "GBP": 5224518800061245598,
    "CHF": 5224707263226194753,
    "AUD": 5224659803837574114,
    "NZD": 5224573595254009705,
    "JPY": 5222390089715299207,
}

_gemini_lock = threading.Lock()
_gemini_idx = 0


def default_news_draft() -> dict:
    return {
        "pairs": list(NEWS_GLOBAL_PAIRS),
        "n_days": 1,
        "filter": "high",
        "page": 0,
        "ai_mode": True,
    }


def _u16len(s: str) -> int:
    return sum(2 if ord(c) > 0xFFFF else 1 for c in s)


def slash_pair(symbol: str) -> str:
    s = (symbol or "").strip().upper().replace(" ", "").replace("-", "").replace("_", "")
    if "/" in (symbol or ""):
        return symbol.strip().upper()
    for a in ("XAU", "XAG", "EUR", "GBP", "AUD", "NZD", "USD", "CAD", "CHF", "JPY"):
        if s.startswith(a) and len(s) > len(a):
            return f"{a}/{s[len(a):]}"
    if len(s) == 6:
        return f"{s[:3]}/{s[3:]}"
    return symbol.strip().upper()


def currencies_from_pairs(pairs: list[str] | tuple[str, ...]) -> set[str]:
    out: set[str] = set()
    for p in pairs:
        sp = slash_pair(p)
        if "/" in sp:
            a, b = sp.split("/", 1)
            out.add(a)
            out.add(b)
    return out


def fetch_ff_calendar(*, timeout: int = 40) -> list[dict]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }
    r = requests.get(FF_WEEK_URL, headers=headers, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise ValueError("Unexpected calendar payload")

    return data


def _parse_impact(raw: str) -> str:
    s = (raw or "").strip().lower()
    if s in ("high", "red"):
        return "HIGH"
    if s in ("medium", "med", "orange"):
        return "MEDIUM"
    return "LOW"


def _parse_num(raw: Any) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s.upper() in ("N/A", "NA", "-", "—", ""):
        return None
    mult = 1.0
    su = s.upper().replace(",", "")
    if su.endswith("%"):
        su = su[:-1]
    if su.endswith("K"):
        mult = 1_000.0
        su = su[:-1]
    elif su.endswith("M"):
        mult = 1_000_000.0
        su = su[:-1]
    elif su.endswith("B"):
        mult = 1_000_000_000.0
        su = su[:-1]
    su = re.sub(r"[^\d.\-+]", "", su)
    try:
        return float(su) * mult
    except ValueError:
        return None


def _heuristic_bias(title: str, forecast: Any, previous: Any) -> tuple[str | None, int]:

    f = _parse_num(forecast)
    p = _parse_num(previous)
    if f is None or p is None or f == p:
        return None, 0
    title_l = (title or "").lower()
    invert = any(k in title_l for k in _NEGATIVE_IF_HIGHER)
    stronger = f > p
    if invert:
        stronger = not stronger
    bias = "BULLISH" if stronger else "BEARISH"

    base = abs(p) if abs(p) > 1e-9 else 1.0
    gap = abs(f - p) / base
    conf = 72 + min(20, int(gap * 100))
    return bias, conf


def _to_local(dt_utc: datetime, tz_hours: float = 6.0) -> datetime:
    return dt_utc.astimezone(timezone(timedelta(hours=tz_hours)))


def _parse_ff_date(raw: str) -> datetime | None:
    s = (raw or "").strip()
    if not s:
        return None
    try:

        return datetime.fromisoformat(s)
    except ValueError:
        pass
    try:
        return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def filter_calendar_events(
    events: list[dict],
    *,
    pairs: list[str],
    n_days: int = 1,
    newsfilter: str = "all",
    tz_hours: float = 6.0,
) -> list[dict]:
    days = max(1, min(3, int(n_days or 1)))
    filt = str(newsfilter or "all").strip().lower()
    allowed_impacts = {"HIGH", "MEDIUM", "LOW"} if filt == "all" else {_parse_impact(filt)}
    wanted_ccy = currencies_from_pairs(pairs)
    now_local = datetime.now(timezone(timedelta(hours=tz_hours)))
    end_local = now_local + timedelta(days=days)

    out: list[dict] = []
    for ev in events or []:
        country = str(ev.get("country") or "").upper()
        ccy = _FF_COUNTRY_TO_CCY.get(country, country)
        if wanted_ccy and ccy not in wanted_ccy:
            continue
        impact = _parse_impact(ev.get("impact") or "")
        if impact not in allowed_impacts:
            continue
        dt = _parse_ff_date(str(ev.get("date") or ""))
        if not dt:
            continue
        local = _to_local(dt, tz_hours)
        if local < now_local - timedelta(minutes=5):
            continue
        if local > end_local:
            continue
        title = str(ev.get("title") or "").strip()
        if not title:
            continue
        bias, conf = _heuristic_bias(title, ev.get("forecast"), ev.get("previous"))
        out.append({
            "title": title,
            "currency": ccy,
            "impact": impact,
            "forecast": ev.get("forecast") if ev.get("forecast") not in (None, "") else "N/A",
            "previous": ev.get("previous") if ev.get("previous") not in (None, "") else "N/A",
            "dt_local": local,
            "date_fmt": local.strftime("%d-%m-%Y"),
            "time_fmt": local.strftime("%H:%M"),
            "bias": bias,
            "confidence": conf,
            "source": "ForexFactory",
        })
    out.sort(key=lambda x: x["dt_local"])
    return out


def _pairs_for_bias(pairs: list[str], currency: str, bias: str) -> tuple[list[str], list[str]]:

    call: list[str] = []
    put: list[str] = []
    ccy = (currency or "").upper()
    bullish = (bias or "").upper() == "BULLISH"
    for raw in pairs:
        sp = slash_pair(raw)
        if "/" not in sp:
            continue
        base, quote = sp.split("/", 1)
        if ccy not in (base, quote):
            continue
        if bullish:
            if base == ccy:
                call.append(sp)
            else:
                put.append(sp)
        else:
            if base == ccy:
                put.append(sp)
            else:
                call.append(sp)
    return call, put


def analyze_events_with_gemini(
    events: list[dict],
    pairs: list[str],
    gemini_keys: list[str],
    *,
    model: str = "gemini-2.0-flash",
) -> dict[int, dict]:

    global _gemini_idx
    if not events or not gemini_keys:
        return {}

    compact = []
    for i, ev in enumerate(events[:40]):
        compact.append({
            "id": i,
            "event": ev["title"],
            "currency": ev["currency"],
            "impact": ev["impact"],
            "forecast": ev["forecast"],
            "previous": ev["previous"],
            "time": f"{ev['date_fmt']} {ev['time_fmt']}",
            "heuristic_bias": ev.get("bias"),
        })

    prompt = (
        "You are a senior forex / binary-options news analyst for QUANTEX-BOT.\n"
        "For each economic event, decide if the event currency is BULLISH or BEARISH "
        "for the next candle after release (pre-news bias from forecast vs previous).\n"
        "If data is insufficient (speeches without numbers), pick the more likely bias "
        "from typical market reaction or mark NEUTRAL.\n\n"
        f"Selected pairs: {', '.join(pairs[:40])}\n\n"
        f"Events JSON:\n{json.dumps(compact, ensure_ascii=False)}\n\n"
        "Respond ONLY with JSON (no markdown):\n"
        '{"results":[{"id":0,"bias":"BULLISH","confidence":85,'
        '"rationale":"1-2 sentences"}]}\n'
        "bias must be BULLISH, BEARISH, or NEUTRAL. confidence 60-95 integer."
    )

    keys = [k for k in gemini_keys if k]
    if not keys:
        return {}

    last_err = ""
    for _ in range(len(keys)):
        with _gemini_lock:
            key = keys[_gemini_idx % len(keys)]
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={key}"
        )
        try:
            resp = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 2048,
                        "responseMimeType": "application/json",
                    },
                },
                timeout=45,
            )
            raw = resp.json()
            if "error" in raw:
                msg = str(raw["error"].get("message", ""))
                last_err = msg
                if any(k in msg.lower() for k in ("quota", "rate", "resource", "429")):
                    with _gemini_lock:
                        _gemini_idx += 1
                    continue
                break
            cands = raw.get("candidates") or []
            if not cands:
                last_err = "no candidates"
                with _gemini_lock:
                    _gemini_idx += 1
                continue
            text = (cands[0].get("content") or {}).get("parts") or [{}]
            text_raw = str(text[0].get("text") or "")
            start = text_raw.find("{")
            end = text_raw.rfind("}") + 1
            if start < 0 or end <= 0:
                last_err = "no json"
                break
            data = json.loads(text_raw[start:end])
            out: dict[int, dict] = {}
            for row in data.get("results") or []:
                try:
                    idx = int(row.get("id"))
                except Exception:
                    continue
                bias = str(row.get("bias") or "NEUTRAL").upper()
                if bias not in ("BULLISH", "BEARISH", "NEUTRAL"):
                    bias = "NEUTRAL"
                conf = max(60, min(95, int(row.get("confidence") or 75)))
                out[idx] = {
                    "bias": bias,
                    "confidence": conf,
                    "rationale": str(row.get("rationale") or "").strip(),
                }
            return out
        except Exception as ex:
            last_err = str(ex)
            with _gemini_lock:
                _gemini_idx += 1
            continue
    if last_err:
        print(f"[NewsAI] Gemini failed: {last_err[:160]}")
    return {}


def _event_cache_key(ev: dict) -> str:

    return f"{ev.get('title','')}|{ev.get('currency','')}|{ev.get('date_fmt','')}|{ev.get('time_fmt','')}"


def _get_cached_analysis(event_key: str) -> dict | None:

    try:
        import db_postgres as _db
        raw = _db._db_news_cache_get(event_key)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


def _set_cached_analysis(event_key: str, data: dict, expires_at_iso: str):
    try:
        import db_postgres as _db
        _db._db_news_cache_set(event_key, json.dumps(data, ensure_ascii=False), expires_at_iso)
    except Exception:
        pass


def _fetch_30day_candles(pair: str, tz_offset: float = 6.0, days_back: int = 30) -> list[dict]:

    try:
        from quantex_checker_engine import _fetch_local_archive, _fetch_local_recent
    except Exception:
        return []
    today = datetime.now().date()
    out: list[dict] = []
    for d in range(days_back, 0, -1):
        ds = (today - timedelta(days=d)).strftime("%Y-%m-%d")
        try:
            cs = _fetch_local_archive(pair, ds, tz_offset)
        except Exception:
            cs = []
        if cs:
            out.extend(cs)
    try:
        recent = _fetch_local_recent(pair, tz_offset)
    except Exception:
        recent = []
    if recent:
        out.extend(recent)
    return out


def _technical_structure_bias(candles: list[dict]) -> tuple[str | None, int]:

    closes = [c.get("close") for c in candles if isinstance(c.get("close"), (int, float))]
    if len(closes) < 120:
        return None, 0

    recent_n = min(50, len(closes) // 4)
    older_n = min(500, len(closes))
    recent_avg = sum(closes[-recent_n:]) / recent_n
    older_avg = sum(closes[-older_n:]) / older_n
    trend_up = recent_avg > older_avg
    trend_gap = abs(recent_avg - older_avg) / (abs(older_avg) if older_avg else 1.0)

    mom_n = min(30, len(closes) - 1)
    momentum = closes[-1] - closes[-1 - mom_n]
    momentum_up = momentum > 0
    mom_gap = abs(momentum) / (abs(closes[-1 - mom_n]) if closes[-1 - mom_n] else 1.0)

    if trend_up == momentum_up:
        bias = "BULLISH" if trend_up else "BEARISH"
        strength = 55 + min(35, int((trend_gap + mom_gap) * 4000))
    else:

        bias = "BULLISH" if trend_up else "BEARISH"
        strength = 30 + min(15, int(trend_gap * 2000))
    return bias, min(95, strength)


def _blend_fundamental_technical(
    fund_bias: str, fund_conf: int, tech_bias: str | None, tech_strength: int,
) -> tuple[int, str]:

    if not tech_bias:
        return fund_conf, ""
    if tech_bias == fund_bias:
        boost = min(15, tech_strength // 6)
        return min(96, fund_conf + boost), (
            f"Technical structure agrees ({tech_bias.lower()}, "
            f"{tech_strength}% strength) — confidence raised."
        )
    penalty = min(20, tech_strength // 5)
    return max(45, fund_conf - penalty), (
        f"Technical structure disagrees ({tech_bias.lower()}) — "
        f"confidence reduced, treat with extra caution."
    )


def build_news_events(
    *,
    pairs: list[str],
    n_days: int = 1,
    newsfilter: str = "all",
    tz_hours: float = 6.0,
    use_ai: bool = True,
    gemini_keys: list[str] | None = None,
    use_technical: bool = True,
) -> dict[str, Any]:

    clean_pairs = []
    seen = set()
    for p in pairs or []:
        sp = slash_pair(p)
        if sp and sp not in seen:
            seen.add(sp)
            clean_pairs.append(sp)
    if not clean_pairs:
        return {"status": "error", "message": "No pairs selected."}

    try:
        calendar = fetch_ff_calendar()
    except Exception as ex:
        return {"status": "error", "message": f"Calendar fetch failed: {ex}"}

    filtered = filter_calendar_events(
        calendar,
        pairs=clean_pairs,
        n_days=n_days,
        newsfilter=newsfilter,
        tz_hours=tz_hours,
    )
    if not filtered:
        return {
            "status": "success",
            "events": [],
            "total": 0,
            "ai_used": False,
            "message": "No matching news events for your filters.",
        }

    cached_by_idx: dict[int, dict] = {}
    to_analyze_idx: list[int] = []
    for i, ev in enumerate(filtered):
        cached = _get_cached_analysis(_event_cache_key(ev))
        if cached:
            cached_by_idx[i] = cached
        else:
            to_analyze_idx.append(i)

    ai_map: dict[int, dict] = {}
    ai_used = any(c.get("ai_used") for c in cached_by_idx.values())
    if use_ai and gemini_keys and to_analyze_idx:
        to_analyze_events = [filtered[i] for i in to_analyze_idx]
        ai_map_local = analyze_events_with_gemini(to_analyze_events, clean_pairs, gemini_keys)
        ai_map = {to_analyze_idx[k]: v for k, v in ai_map_local.items()}
        if ai_map:
            ai_used = True


    _tech_cache: dict[str, tuple[str | None, int]] = {}
    technical_used = any(c.get("technical_used") for c in cached_by_idx.values())

    cards = []
    for i, ev in enumerate(filtered):
        if i in cached_by_idx:
            c = cached_by_idx[i]
            bias = c.get("bias")
            conf = int(c.get("confidence") or 75)
            full_rationale = c.get("rationale") or ""
            if not bias:
                continue
            call_pairs, put_pairs = _pairs_for_bias(clean_pairs, ev["currency"], bias)
            if not call_pairs and not put_pairs:
                continue
        else:
            bias = ev.get("bias")
            conf = int(ev.get("confidence") or 0)
            rationale = ""
            if i in ai_map:
                ai = ai_map[i]
                if ai.get("bias") in ("BULLISH", "BEARISH"):
                    bias = ai["bias"]
                    conf = int(ai.get("confidence") or conf or 75)
                    rationale = ai.get("rationale") or ""
                elif ai.get("bias") == "NEUTRAL" and not bias:
                    continue
            if not bias:
                continue
            call_pairs, put_pairs = _pairs_for_bias(clean_pairs, ev["currency"], bias)
            if not call_pairs and not put_pairs:
                continue
            conf = conf or 75

            tech_note = ""
            this_event_ai_used = i in ai_map
            this_event_tech_used = False
            if use_technical:
                ccy = ev["currency"]
                if ccy not in _tech_cache:
                    rep_pair = next(
                        (p for p in (call_pairs + put_pairs) if ccy in p.replace("/", " ").split()),
                        (call_pairs + put_pairs)[0] if (call_pairs + put_pairs) else None,
                    )
                    tech_bias, tech_strength = (None, 0)
                    if rep_pair:
                        candles = _fetch_30day_candles(rep_pair, tz_hours)
                        if candles:
                            tech_bias, tech_strength = _technical_structure_bias(candles)
                    _tech_cache[ccy] = (tech_bias, tech_strength)
                tbias, tstrength = _tech_cache[ccy]
                if tbias:
                    technical_used = True
                    this_event_tech_used = True
                    conf, tech_note = _blend_fundamental_technical(bias, conf, tbias, tstrength)

            full_rationale = " ".join(x for x in (rationale, tech_note) if x).strip()


            try:
                _set_cached_analysis(
                    _event_cache_key(ev),
                    {
                        "bias": bias, "confidence": conf, "rationale": full_rationale,
                        "ai_used": this_event_ai_used, "technical_used": this_event_tech_used,
                    },
                    (ev["dt_local"] + timedelta(minutes=5)).isoformat(),
                )
            except Exception:
                pass

        direction = "BUY-UP-CALL⬆️" if bias == "BULLISH" else "SELL-DOWN-PUT⬇️"
        entry_dt = ev["dt_local"] - timedelta(seconds=2)
        cards.append({
            "date": ev["date_fmt"],
            "time": ev["time_fmt"],
            "event": ev["title"],
            "impact": ev["impact"],
            "forecast": ev["forecast"],
            "previous": ev["previous"],
            "currency": ev["currency"],
            "direction": direction,
            "bias": bias,
            "confidence": conf,
            "rationale": full_rationale,
            "call_pairs": call_pairs,
            "put_pairs": put_pairs,
            "entry": entry_dt.strftime("%H:%M:%S"),
        })

    return {
        "status": "success",
        "events": cards,
        "total": len(cards),
        "ai_used": ai_used,
        "technical_used": technical_used,
        "tz_label": f"UTC{'+' if tz_hours >= 0 else ''}{int(tz_hours) if tz_hours == int(tz_hours) else tz_hours}",
        "calendar_count": len(filtered),
    }


def _wrap_pairs(pairs: list[str], per_line: int = 3) -> str:
    if not pairs:
        return "     —"
    lines = []
    for i in range(0, len(pairs), per_line):
        chunk = pairs[i:i + per_line]
        lines.append(" · ".join(chunk))
    return "\n".join(f"     {ln}" for ln in lines)


def _wrap_pairs_bullet(pairs: list[str], per_line: int = 3) -> str:

    if not pairs:
        return "—"
    lines = []
    for i in range(0, len(pairs), per_line):
        chunk = pairs[i:i + per_line]
        lines.append(" • ".join(chunk))
    return "\n".join(lines)


def _to_12h(time_str: str) -> str:

    s = str(time_str or "").strip()
    if not s:
        return "—"
    bits = s.split(":")
    try:
        hh = int(bits[0]); mm = int(bits[1]) if len(bits) > 1 else 0
        ss = int(bits[2]) if len(bits) > 2 else 0
    except (ValueError, IndexError):
        return s
    period = "AM" if hh < 12 else "PM"
    hh12 = hh % 12
    if hh12 == 0:
        hh12 = 12
    return f"{hh12:02d}:{mm:02d}:{ss:02d} {period}"


def _mono(value: Any) -> str:

    text = str(value)
    out = []
    for char in text:
        code = ord(char)
        if "A" <= char <= "Z":
            out.append(chr(0x1D670 + code - ord("A")))
        elif "a" <= char <= "z":
            out.append(chr(0x1D68A + code - ord("a")))
        elif "0" <= char <= "9":
            out.append(chr(0x1D7F6 + code - ord("0")))
        elif char == ":":
            out.append("∶")
        else:
            out.append(char)
    return "".join(out)


def build_news_signal_parts(
    event: dict,
    *,
    events_today: int,
    tz_label: str = "UTC+6",
    owner: str = "@X_Akash_Owner",
    bot_username: str = "QuantexBinaryTools_bot",
    ai_used: bool = False,
) -> list[tuple[str, str | None]]:
    impact = str(event.get("impact") or "LOW").upper()
    date_fmt = str(event.get("date") or "—")
    time_s = _to_12h((str(event.get("time") or "")) and f"{event.get('time')}:00")
    entry = _to_12h(event.get("entry") or event.get("time") or "")
    currency = str(event.get("currency") or "USD")
    flag_id = CURRENCY_EMOJI_IDS.get(currency)
    flag_char = _CURRENCY_FLAGS.get(currency, "🏳️")
    event_name = str(event.get("event") or "—")
    call_block = _wrap_pairs_bullet(list(event.get("call_pairs") or []))
    put_block = _wrap_pairs_bullet(list(event.get("put_pairs") or []))
    owner_disp = owner if str(owner).startswith("@") else f"@{owner}"
    bot = str(bot_username or "Fluixonpro_bot").lstrip("@")
    conf = event.get("confidence") or ""
    forecast = event.get("forecast") or "N/A"
    previous = event.get("previous") or "N/A"
    rationale = str(event.get("rationale") or "").strip()

    impact_icon, impact_key = {
        "HIGH": ("💥", "impact_high"),
        "MEDIUM": ("🟠", "impact_med"),
        "LOW": ("🔵", "impact_low"),
    }.get(impact, ("🟠", "impact_med"))

    flag_key = None
    if flag_id :
        flag_key =f"flag_{currency}"
        NEWS_EMOJI_IDS [flag_key ]=flag_id

    def _field(label: str) -> str:
        return _mono(label).ljust(12) + " ∶"

    call_block = _mono(call_block).replace("•", "·")
    put_block = _mono(put_block).replace("•", "·")

    parts: list[tuple[str, str | None]] = [
        ("╔═══════════════╗\n", None),
        ("   ", None), ("👑", "king"), (" 𝚉𝙴𝙱𝚁𝙾𝙽𝙸𝚇 𝙰𝙸 𝙽𝙴𝚆𝚂 𝚂𝙸𝙶𝙽𝙰𝙻", None), ("👑", "king"), ("\n", None),
        ("╚═══════════════╝\n\n", None),
        ("🔥", "fire2"), (f" {_mono(impact + ' IMPACT NEWS')}\n\n", None),
        ("📆", "calendar2"), (f" {_field('Date')} {_mono(date_fmt)}\n", None),
        ("🕒", "clock2"), (f" {_field('News Time')} {_mono(time_s)} ({_mono(tz_label)})\n\n", None),
        ("💎", "gem"), (f" {_field('Event')} {_mono(event_name)}\n", None),
        ("🌐", "world"), (f" {_field('Currency')} {_mono(currency)} ", None),
        (flag_char , flag_key ),
        ("\n", None),
        ("💥", impact_key), (f" {_field('Impact')} {_mono(impact)}\n", None),
        ("───────────────\n", None),
        ("🟢", "call_grn"), (" 𝙲𝙰𝙻𝙻 / 𝙱𝚄𝚈\n", None),
        (f"{call_block}\n\n", None),
        ("🔴", "put_red"), (" 𝙿𝚄𝚃 / 𝚂𝙴𝙻𝙻\n", None),
        (f"{put_block}\n", None),
        ("───────────────\n", None),
        ("⌛", "hourglass"), (f" {_field('Entry Time')} {_mono(entry)}\n", None),
        ("⏰", "alarm"), (" 𝙼𝙰𝚁𝚃𝙸𝙽𝙶𝙰𝙻𝙴 ∶ 𝟷 𝚂𝚃𝙴𝙿 𝚁𝙴𝚀𝚄𝙸𝚁𝙴𝙳", None),
        ("✏️", "writing"), ("\n", None),
        ("⏰", "stopwatch"), (" 𝙴𝚡𝚙𝚒𝚛𝚊𝚝𝚒𝚘𝚗 ∶ 𝟷 𝙼𝚒𝚗𝚞𝚝𝚎\n\n", None),
        ("╔════════════╗\n", None),
        ("📊", "chart_up"), (f" {_field('Forecast')} {_mono(forecast)}\n", None),
        ("📉", "chart_down"), (f" {_field('Previous')} {_mono(previous)}\n", None),
    ]
    if conf :
        parts .append (("🎯", "target"))
        parts .append ((f" {_field ('Confidence')} {_mono(conf)}%\n", None ))
    parts += [
        ("╚════════════╝\n\n", None),
        ("👑", "king"), (" 𝙿𝙾𝚆𝙴𝚁𝙴𝙳 𝙱𝚈 𝚉𝙴𝙱𝚁𝙾𝙽𝙸𝚇 𝙰𝙸 ", None), ("👑", "king"), ("\n", None),
    ]
    return parts


def parts_to_text_and_entities(
    parts: list[tuple[str, str | None]],
    *,
    use_prem: bool,
    extra_emoji_ids: dict | None = None,
) -> tuple[str, list[dict]]:
    ids = dict(NEWS_EMOJI_IDS)
    if extra_emoji_ids:
        ids.update(extra_emoji_ids)
    text = "".join(s for s, _ in parts)
    entities: list[dict] = [{"type": "bold", "offset": 0, "length": _u16len(text)}]
    if use_prem:
        offset = 0
        for s, key in parts:
            if key is not None:
                doc_id = ids.get(key, 0)
                if doc_id:
                    entities.append({
                        "type": "custom_emoji",
                        "offset": offset,
                        "length": _u16len(s),
                        "custom_emoji_id": str(doc_id),
                    })
            offset += _u16len(s)
    entities.sort(key=lambda x: (x["offset"], x["type"] != "bold"))
    return text, entities
