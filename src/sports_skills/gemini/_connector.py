"""Gemini Predictions — public read-only prediction-market events.

Wraps the unauthenticated Gemini prediction-markets API
(https://api.gemini.com/v1/prediction-markets). GET only, no credentials,
plain ``requests`` (redirects refused).

Upstream behavior (probed 2026-10-23):
- ``/events`` lists are ``{"data": [...], "pagination": {limit, offset, total}}``;
  ``limit`` is 1-500, paging is by ``offset``. ``search`` matches titles only.
- ``/events/{ticker}`` returns the event object itself.
- ``startTime`` is kickoff. ``effectiveDate`` is the listing date and
  ``expiryDate`` the settlement deadline; neither is kickoff.
- A game event (the moneyline) may nest child events (spreads, totals, props)
  under ``events``; each is a different market with its own contracts.
- Contract prices are probability strings, any of which may be absent.
"""

import json
import re
import threading
import time
import urllib.parse
from datetime import datetime, timezone

import requests

from sports_skills import _replay, _response

BASE_URL = "https://api.gemini.com/v1/prediction-markets"

_PAGE_LIMIT = 100
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 500
_MAX_PAGES = 5  # bounded scan for search/today

# Sport codes -> (Gemini ticker prefix, sportsMarket.sport). Only pairs seen
# together in the full live Sports listing (2026-10-23). Futures with other
# prefixes (NFLMVP2026, NBAF-..., CFBSEC26) carry no sportsMarket and stay
# reachable only through the unfiltered listing.
# ponytail: add a league once its live ticker prefix is verified.
LEAGUES = {
    "nba": ("NBA", "basketball"),
    "wnba": ("WNBA", "basketball"),
    "nfl": ("NFL", "american_football"),
    "cfb": ("NCAAF", "american_football"),
    "mlb": ("MLB", "baseball"),
    "nhl": ("NHL", "hockey"),
    "epl": ("EPL", "soccer"),
    "laliga": ("LALIGA", "soccer"),
    "mls": ("MLS", "soccer"),
    "ligamx": ("LIGAMX", "soccer"),
    "ufc": ("UFC", "mixed_martial_arts"),
    "f1": ("F1", "motorsports"),
    "golf": ("GOLF", "golf"),
}

STATUSES = ("approved", "active", "closed", "under_review", "settled", "invalid")
MARKET_TYPES = ("moneyline", "spread", "total", "prop", "correct_score", "to_advance", "futures", "other")

_TICKER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")

# ============================================================
# HTTP (cached, throttled, replay-aware)
# ============================================================

_cache = {}
_throttle_lock = threading.Lock()
_last_request = [0.0]
_MIN_INTERVAL = 0.25


def _get(path, params=None, ttl=15, meta=None):
    """GET a public path. Returns parsed JSON or an ``{"error": True, ...}`` dict.

    ``meta``, when given, receives ``retrieved_at`` — the original retrieval
    time, preserved across cache hits.

    The cache holds response bytes, so every caller parses its own copy, and
    is used only with replay off: record/replay/fill must reach ``_replay``.
    """
    url = BASE_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    cacheable = _replay.mode() == _replay.OFF
    hit = _cache.get(url) if cacheable else None
    if hit and hit[1] > time.monotonic():
        raw, retrieved_at = hit[0], hit[2]
    else:
        raw, err = _replay.fetch(url, lambda: _live_fetch(url))
        if err is not None:
            return err
        retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        hit = None
    try:
        data = json.loads(raw.decode())
    except (ValueError, UnicodeDecodeError) as exc:
        return {"error": True, "message": f"Malformed JSON from upstream: {exc}"}
    if cacheable and hit is None:
        if len(_cache) > 500:
            _cache.clear()
        _cache[url] = (raw, time.monotonic() + ttl, retrieved_at)
    if meta is not None:
        meta["retrieved_at"] = retrieved_at
    return data


def _live_fetch(url):
    with _throttle_lock:
        wait = _last_request[0] + _MIN_INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_request[0] = time.monotonic()
    try:
        # A callable auth is truthy, so requests skips ~/.netrc; it adds nothing.
        resp = requests.get(
            url, headers={"Accept": "application/json"}, timeout=20, allow_redirects=False, auth=lambda r: r
        )
    except Exception as e:
        return None, {"error": True, "message": str(e)}
    if 300 <= resp.status_code < 400:
        return None, {"error": True, "status_code": resp.status_code, "message": "Redirect refused"}
    if resp.status_code >= 400:
        return None, {"error": True, "status_code": resp.status_code, "message": str(resp.reason)}
    return resp.content, None


def _fail(err):
    code = err.get("status_code", "n/a")
    return _response.wrap({**err, "message": f"Gemini API error ({code}): {err.get('message', '')}"})


def _is_error(response):
    return isinstance(response, dict) and response.get("error") is True


# ============================================================
# Validation + normalization
# ============================================================


def _resolve_league(league):
    """(ticker prefix, sport) for a league code, or None when unknown."""
    return LEAGUES.get(str(league).strip().lower())


def _league_error(league):
    return _response.error(f"Unknown league '{league}'. Valid: {', '.join(LEAGUES)}")


def _int(value, default, low, high=None):
    """Validated int in [low, high], or None when invalid (bools, fractions, inf/NaN)."""
    if value is None:
        return default
    if (
        isinstance(value, float)
        and value.is_integer()
        or isinstance(value, str)
        and re.fullmatch(r"[+-]?\d+", value.strip())
    ):
        value = int(value)
    if not isinstance(value, int) or isinstance(value, bool):
        return None
    if value < low or (high is not None and value > high):
        return None
    return value


def _prob(value):
    """Probability in [0, 1] from a price string, or None for missing/bad values."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if 0 <= number <= 1 else None  # NaN fails the comparison


def _iso(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _dict(value):
    return value if isinstance(value, dict) else {}


def _league_of(ticker):
    return ticker.split("-", 1)[0].upper() if isinstance(ticker, str) else ""


def _normalize_contract(contract):
    prices = _dict(contract.get("prices"))
    buy, sell = _dict(prices.get("buy")), _dict(prices.get("sell"))
    is_combo = contract.get("isCombo")
    return {
        "id": contract.get("id"),
        "ticker": contract.get("ticker"),
        "label": contract.get("label", ""),
        "side": contract.get("sportsSide"),
        "status": contract.get("status", ""),
        "market_state": contract.get("marketState"),
        "is_combo": is_combo if isinstance(is_combo, bool) else None,
        "instrument_symbol": contract.get("instrumentSymbol"),
        "strike": contract.get("strike"),
        "best_bid": _prob(prices.get("bestBid")),
        "best_ask": _prob(prices.get("bestAsk")),
        "buy_yes": _prob(buy.get("yes")),
        "buy_no": _prob(buy.get("no")),
        "sell_yes": _prob(sell.get("yes")),
        "sell_no": _prob(sell.get("no")),
        "last_trade_price": _prob(prices.get("lastTradePrice")),
    }


def _normalize_event(event, retrieved_at, parent_ticker=None):
    sports_market = _dict(event.get("sportsMarket"))
    title = event.get("title")
    return {
        "id": event.get("id"),
        "ticker": event.get("ticker"),
        "parent_ticker": parent_ticker,
        "name": title if isinstance(title, str) else "",
        "league": _league_of(event.get("ticker")),
        "sport": sports_market.get("sport"),
        "status": event.get("status", ""),
        "market_type": sports_market.get("type"),
        "market_subject": sports_market.get("subject"),
        "market_scope": _dict(sports_market.get("scope")).get("type"),
        "start_time": _iso(event.get("startTime")),
        "participants": [
            {"name": p.get("name", ""), "abbreviation": p.get("abbreviation"), "side": p.get("side")}
            for p in event.get("participants") or []
            if isinstance(p, dict)
        ],
        "contracts": [_normalize_contract(c) for c in event.get("contracts") or [] if isinstance(c, dict)],
        "child_events": [
            _normalize_event(child, retrieved_at, event.get("ticker"))
            for child in event.get("events") or []
            if isinstance(child, dict)
        ],
        "price_basis": "cached_snapshot",
        "execution_guaranteed": False,
        "retrieved_at": retrieved_at,
        "_raw": event,
    }


def _page(response):
    """(items, total) from a list envelope; items is None on schema drift."""
    if not isinstance(response, dict) or not isinstance(response.get("data"), list):
        return None, None
    total = _dict(response.get("pagination")).get("total")
    return response["data"], total if isinstance(total, int) and not isinstance(total, bool) else None


def _short_page_warning(items, offset, total):
    """Warning for an empty page before the reported total (listing incomplete), else None."""
    if items or total is None or offset >= total:
        return None
    return {
        "stage": "events_page",
        "offset": offset,
        "message": f"Gemini returned no events at offset {offset} of a reported {total}; listing is incomplete",
    }


def _list_query(league, status="active"):
    """Upstream /events filters -> (query, prefix, error)."""
    query = {"category": "Sports", "status": status}
    if not league:
        return query, None, None
    resolved = _resolve_league(league)
    if resolved is None:
        return None, None, _league_error(league)
    prefix, sport = resolved
    query["sport"] = sport
    return query, prefix, None


def _in_league(event, prefix):
    return prefix is None or _league_of(event.get("ticker")) == prefix


# ============================================================
# Commands
# ============================================================


def get_events(request_data):
    try:
        params = request_data.get("params", {})
        status = str(params.get("status") or "active").strip().lower()
        if status not in STATUSES:
            return _response.error(f"Unknown status '{params.get('status')}'. Valid: {', '.join(STATUSES)}")
        limit = _int(params.get("limit"), _DEFAULT_LIMIT, 1, _MAX_LIMIT)
        if limit is None:
            return _response.error(f"limit must be an integer from 1 to {_MAX_LIMIT}, got '{params.get('limit')}'")
        offset = _int(params.get("offset"), 0, 0)
        if offset is None:
            return _response.error(f"offset must be a non-negative integer, got '{params.get('offset')}'")
        query, prefix, err = _list_query(params.get("league"), status)
        if err:
            return err

        meta = {}
        response = _get("/events", dict(query, limit=limit, offset=offset), meta=meta)
        if _is_error(response):
            return _fail(response)
        items, total = _page(response)
        if items is None:
            return _response.error("Unexpected Gemini events payload shape (schema drift)")
        events = [
            _normalize_event(e, meta.get("retrieved_at"))
            for e in items
            if isinstance(e, dict) and _in_league(e, prefix)
        ]
        next_offset = offset + len(items)
        data = {
            "events": events,
            "count": len(events),
            "pagination": {"limit": limit, "offset": offset, "total": total},
            "next_offset": next_offset if items and (total is None or next_offset < total) else None,
        }
        warning = _short_page_warning(items, offset, total)
        if warning:
            data["warnings"] = [warning]
        return _response.success(data, f"Retrieved {len(events)} events" + (" (listing incomplete)" if warning else ""))
    except Exception as e:
        return _response.error(f"Error fetching Gemini events: {e}")


def get_event(request_data):
    try:
        ticker = request_data.get("params", {}).get("event_ticker")
        if not isinstance(ticker, str) or not _TICKER_RE.fullmatch(ticker):
            return _response.error(f"event_ticker must be a Gemini event ticker, got '{ticker}'")
        meta = {}
        response = _get(f"/events/{urllib.parse.quote(ticker, safe='')}", meta=meta)
        if _is_error(response):
            return _fail(response)
        if not isinstance(response, dict) or not isinstance(response.get("ticker"), str):
            return _response.error("Unexpected Gemini event payload shape (schema drift)")
        return _response.success(_normalize_event(response, meta.get("retrieved_at")), "Retrieved event")
    except Exception as e:
        return _response.error(f"Error fetching Gemini event: {e}")


def _scan_events(query, prefix):
    """Up to _MAX_PAGES event pages -> (normalized events, truncated, error, warnings)."""
    events, offset = [], 0
    for _ in range(_MAX_PAGES):
        meta = {}
        response = _get("/events", dict(query, limit=_PAGE_LIMIT, offset=offset), meta=meta)
        if _is_error(response):
            if offset and not (response.get("replay_miss") or response.get("replay_error")):
                warning = {"stage": "events_page", "offset": offset, "message": _fail(response)["message"]}
                return events, True, None, [warning]
            return [], False, _fail(response), []
        items, total = _page(response)
        if items is None:
            return [], False, _response.error("Unexpected Gemini events payload shape (schema drift)"), []
        retrieved_at = meta.get("retrieved_at")
        events.extend(_normalize_event(e, retrieved_at) for e in items if isinstance(e, dict) and _in_league(e, prefix))
        warning = _short_page_warning(items, offset, total)
        if warning:
            return events, True, None, [warning]
        offset += len(items)
        if not items or (total is not None and offset >= total):
            return events, False, None, []
    return events, True, None, []


def _flatten(events):
    """Each event and its child events once, children carrying parent_ticker."""
    seen = set()
    for event in events:
        for market in [event] + event["child_events"]:
            if market["ticker"] in seen:
                continue
            seen.add(market["ticker"])
            yield {k: v for k, v in market.items() if k != "child_events"}


def _haystack(market):
    names = [market["name"]] + [f"{p['name']} {p['abbreviation'] or ''}" for p in market["participants"]]
    return " ".join(names).lower()


def search_markets(request_data):
    """Token-AND keyword search (title + participants) over a bounded event scan."""
    try:
        params = request_data.get("params", {})
        market_type = params.get("market_type")
        if market_type is not None and market_type not in MARKET_TYPES:
            return _response.error(f"Unknown market_type '{market_type}'. Valid: {', '.join(MARKET_TYPES)}")
        limit = _int(params.get("limit"), _DEFAULT_LIMIT, 1, _MAX_LIMIT)
        if limit is None:
            return _response.error(f"limit must be an integer from 1 to {_MAX_LIMIT}, got '{params.get('limit')}'")
        query, prefix, err = _list_query(params.get("league"))
        if err:
            return err
        tokens = str(params.get("query") or "").lower().split()

        events, truncated, err, warnings = _scan_events(query, prefix)
        if err:
            return err
        markets = [
            m
            for m in _flatten(events)
            if _in_league(m["_raw"], prefix)
            and (market_type is None or m["market_type"] == market_type)
            and all(t in _haystack(m) for t in tokens)
        ]
        markets.sort(key=lambda m: m["start_time"] or "9999")
        if len(markets) > limit:
            truncated = True
        markets = markets[:limit]
        data = {"markets": markets, "count": len(markets), "events_scanned": len(events), "truncated": truncated}
        if warnings:
            data["warnings"] = warnings
        return _response.success(
            data,
            f"Retrieved {len(markets)} markets"
            + (" (scan truncated)" if truncated else "")
            + (f" ({len(warnings)} partial-coverage warnings)" if warnings else ""),
        )
    except Exception as e:
        return _response.error(f"Error searching Gemini markets: {e}")


def get_todays_events(request_data):
    """Events whose startTime falls on today's UTC date, from a bounded scan."""
    try:
        params = request_data.get("params", {})
        limit = _int(params.get("limit"), _DEFAULT_LIMIT, 1, _MAX_LIMIT)
        if limit is None:
            return _response.error(f"limit must be an integer from 1 to {_MAX_LIMIT}, got '{params.get('limit')}'")
        query, prefix, err = _list_query(params.get("league"))
        if err:
            return err
        events, truncated, err, warnings = _scan_events(query, prefix)
        if err:
            return err
        today = datetime.now(timezone.utc).date().isoformat()
        todays = sorted(
            (e for e in events if (e["start_time"] or "").startswith(today)),
            key=lambda e: e["start_time"],
        )
        if len(todays) > limit:
            truncated = True
        todays = todays[:limit]
        data = {"events": todays, "count": len(todays), "date": today, "truncated": truncated}
        if warnings:
            data["warnings"] = warnings
        return _response.success(data, f"Retrieved {len(todays)} events for {today}")
    except Exception as e:
        return _response.error(f"Error fetching today's Gemini events: {e}")
