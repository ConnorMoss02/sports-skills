"""Gemini Predictions — public sports prediction-market events and prices.

Public read-only endpoints (https://api.gemini.com/v1/prediction-markets). No
API key, GET only. Never places, modifies, or cancels orders.

Each Gemini event is one market (moneyline, spread, total, ...) with contracts
priced as probabilities. A game's moneyline event nests its other markets as
child events. Prices are cached snapshots, not executable quotes; volume and
price say nothing about available liquidity.
"""

from __future__ import annotations

from sports_skills.gemini._connector import get_event as _get_event
from sports_skills.gemini._connector import get_events as _get_events
from sports_skills.gemini._connector import get_todays_events as _get_todays_events
from sports_skills.gemini._connector import search_markets as _search_markets


def _req(**kwargs):
    """Build request_data dict from kwargs."""
    return {"params": {k: v for k, v in kwargs.items() if v is not None}}


def get_events(*, league: str | None = None, status: str = "active", limit: int = 50, offset: int = 0) -> dict:
    """Get Gemini sports events (one upstream page), with nested child markets.

    Args:
        league: League code — 'nba', 'wnba', 'nfl', 'cfb', 'mlb', 'nhl', 'epl', 'laliga', 'mls', 'ligamx', 'ufc', 'f1', 'golf'.
        status: Event status — 'active' (default), 'approved', 'closed', 'under_review', 'settled', 'invalid'.
        limit: Max events per page (default: 50, max: 500).
        offset: Events to skip — the `next_offset` value from a previous response.
    """
    return _get_events(_req(league=league, status=status, limit=limit, offset=offset))


def get_event(*, event_ticker: str) -> dict:
    """Get one Gemini event with contracts, prices, and nested child markets.

    Args:
        event_ticker: Gemini event ticker, e.g. 'NBA-2610232300-MIN-ORL-M'.
    """
    return _get_event(_req(event_ticker=event_ticker))


def search_markets(
    *,
    query: str | None = None,
    league: str | None = None,
    market_type: str | None = None,
    limit: int = 50,
) -> dict:
    """Primary tool for finding Gemini markets by team/keyword and league (bounded scan, reports `truncated`).

    Args:
        query: Keywords; every token must appear in the title or a participant name (e.g. 'Timberwolves Magic').
        league: League code — 'nba', 'wnba', 'nfl', 'cfb', 'mlb', 'nhl', 'epl', 'laliga', 'mls', 'ligamx', 'ufc', 'f1', 'golf'.
        market_type: 'moneyline', 'spread', 'total', 'prop', 'correct_score', 'to_advance', 'futures', 'other'.
        limit: Max markets (default: 50, max: 500).
    """
    return _search_markets(_req(query=query, league=league, market_type=market_type, limit=limit))


def get_todays_events(*, league: str | None = None, limit: int = 50) -> dict:
    """Get active Gemini events starting today (UTC startTime), optionally by league.

    Args:
        league: League code — 'nba', 'wnba', 'nfl', 'cfb', 'mlb', 'nhl', 'epl', 'laliga', 'mls', 'ligamx', 'ufc', 'f1', 'golf'.
        limit: Max events (default: 50, max: 500).
    """
    return _get_todays_events(_req(league=league, limit=limit))
