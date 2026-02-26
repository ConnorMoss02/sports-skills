"""Polymarket sports prediction markets — prices, order books, events, and series.

Uses Gamma API (public, no auth) and CLOB API (public reads) via stdlib only.
Extended with Polymarket CLI subprocess wrapper for analytics, trading, and
on-chain operations.
"""

from __future__ import annotations

from sports_skills.polymarket._cli import (
    approve_check as _cli_approve_check,
)
from sports_skills.polymarket._cli import (
    approve_set as _cli_approve_set,
)
from sports_skills.polymarket._cli import (
    cancel_all_orders as _cli_cancel_all_orders,
)
from sports_skills.polymarket._cli import (
    cancel_order as _cli_cancel_order,
)
from sports_skills.polymarket._cli import (
    cli_search_markets as _cli_search_markets,
)
from sports_skills.polymarket._cli import (
    cli_sports_list as _cli_sports_list,
)
from sports_skills.polymarket._cli import (
    cli_sports_teams as _cli_sports_teams,
)
from sports_skills.polymarket._cli import (
    configure as configure,
)
from sports_skills.polymarket._cli import (
    create_order as _cli_create_order,
)
from sports_skills.polymarket._cli import (
    ctf_merge as _cli_ctf_merge,
)
from sports_skills.polymarket._cli import (
    ctf_redeem as _cli_ctf_redeem,
)
from sports_skills.polymarket._cli import (
    ctf_split as _cli_ctf_split,
)
from sports_skills.polymarket._cli import (
    get_activity as _cli_get_activity,
)
from sports_skills.polymarket._cli import (
    get_balance as _cli_get_balance,
)
from sports_skills.polymarket._cli import (
    get_closed_positions as _cli_get_closed_positions,
)
from sports_skills.polymarket._cli import (
    get_comment as _cli_get_comment,
)
from sports_skills.polymarket._cli import (
    get_comments as _cli_get_comments,
)
from sports_skills.polymarket._cli import (
    get_fee_rate as _cli_get_fee_rate,
)
from sports_skills.polymarket._cli import (
    get_holders as _cli_get_holders,
)
from sports_skills.polymarket._cli import (
    get_leaderboard as _cli_get_leaderboard,
)
from sports_skills.polymarket._cli import (
    get_open_interest as _cli_get_open_interest,
)
from sports_skills.polymarket._cli import (
    get_orders as _cli_get_orders,
)
from sports_skills.polymarket._cli import (
    get_portfolio_value as _cli_get_portfolio_value,
)
from sports_skills.polymarket._cli import (
    get_positions as _cli_get_positions,
)
from sports_skills.polymarket._cli import (
    get_profile as _cli_get_profile,
)
from sports_skills.polymarket._cli import (
    get_related_tags as _cli_get_related_tags,
)
from sports_skills.polymarket._cli import (
    get_tag as _cli_get_tag,
)
from sports_skills.polymarket._cli import (
    get_tags as _cli_get_tags,
)
from sports_skills.polymarket._cli import (
    get_tick_size as _cli_get_tick_size,
)
from sports_skills.polymarket._cli import (
    get_trade_history as _cli_get_trade_history,
)
from sports_skills.polymarket._cli import (
    get_traded as _cli_get_traded,
)
from sports_skills.polymarket._cli import (
    get_user_comments as _cli_get_user_comments,
)
from sports_skills.polymarket._cli import (
    get_user_trades as _cli_get_user_trades,
)
from sports_skills.polymarket._cli import (
    get_volume as _cli_get_volume,
)
from sports_skills.polymarket._cli import (
    is_cli_available as is_cli_available,
)
from sports_skills.polymarket._cli import (
    market_order as _cli_market_order,
)
from sports_skills.polymarket._connector import (
    get_event_details as _get_event_details,
)
from sports_skills.polymarket._connector import (
    get_last_trade_price as _get_last_trade_price,
)
from sports_skills.polymarket._connector import (
    get_market_details as _get_market_details,
)
from sports_skills.polymarket._connector import (
    get_market_prices as _get_market_prices,
)
from sports_skills.polymarket._connector import (
    get_order_book as _get_order_book,
)
from sports_skills.polymarket._connector import (
    get_price_history as _get_price_history,
)
from sports_skills.polymarket._connector import (
    get_series as _get_series,
)
from sports_skills.polymarket._connector import (
    get_sports_events as _get_sports_events,
)
from sports_skills.polymarket._connector import (
    get_sports_market_types as _get_sports_market_types,
)
from sports_skills.polymarket._connector import (
    get_sports_markets as _get_sports_markets,
)
from sports_skills.polymarket._connector import (
    search_markets as _search_markets,
)


def _req(**kwargs):
    """Build request_data dict from kwargs."""
    return {"params": {k: v for k, v in kwargs.items() if v is not None}}


# ============================================================
# Original Connector Commands (Gamma/CLOB API — no CLI needed)
# ============================================================


def get_sports_markets(
    *,
    limit: int = 50,
    offset: int = 0,
    sports_market_types: str | None = None,
    game_id: str | None = None,
    active: bool = True,
    closed: bool = False,
    order: str = "volume",
    ascending: bool = False,
) -> dict:
    """Get active sports prediction markets with optional filtering."""
    return _get_sports_markets(
        _req(
            limit=limit,
            offset=offset,
            sports_market_types=sports_market_types,
            game_id=game_id,
            active=active,
            closed=closed,
            order=order,
            ascending=ascending,
        )
    )


def get_sports_events(
    *,
    limit: int = 50,
    offset: int = 0,
    active: bool = True,
    closed: bool = False,
    order: str = "volume",
    ascending: bool = False,
    series_id: str | None = None,
) -> dict:
    """Get sports events (each event groups related markets)."""
    return _get_sports_events(
        _req(
            limit=limit,
            offset=offset,
            active=active,
            closed=closed,
            order=order,
            ascending=ascending,
            series_id=series_id,
        )
    )


def get_series(*, limit: int = 100, offset: int = 0) -> dict:
    """Get all series (leagues, recurring event groups)."""
    return _get_series(_req(limit=limit, offset=offset))


def get_market_details(
    *, market_id: str | None = None, slug: str | None = None
) -> dict:
    """Get detailed information for a specific market."""
    return _get_market_details(_req(market_id=market_id, slug=slug))


def get_event_details(*, event_id: str | None = None, slug: str | None = None) -> dict:
    """Get detailed information for a specific event (includes nested markets)."""
    return _get_event_details(_req(event_id=event_id, slug=slug))


def get_market_prices(
    *, token_id: str | None = None, token_ids: list[str] | None = None
) -> dict:
    """Get current prices for one or more markets from the CLOB API."""
    return _get_market_prices(_req(token_id=token_id, token_ids=token_ids))


def get_order_book(*, token_id: str) -> dict:
    """Get the full order book for a market."""
    return _get_order_book(_req(token_id=token_id))


def get_sports_market_types() -> dict:
    """Get all valid sports market types (moneyline, spreads, totals, props, etc.)."""
    return _get_sports_market_types(_req())


def search_markets(
    *,
    query: str | None = None,
    sports_market_types: str | None = None,
    tag_id: int | None = None,
    limit: int = 20,
) -> dict:
    """Find sports markets by keyword and filters."""
    return _search_markets(
        _req(
            query=query,
            sports_market_types=sports_market_types,
            tag_id=tag_id,
            limit=limit,
        )
    )


def get_price_history(
    *, token_id: str, interval: str = "max", fidelity: int = 120
) -> dict:
    """Get historical price data for a market over time."""
    return _get_price_history(
        _req(token_id=token_id, interval=interval, fidelity=fidelity)
    )


def get_last_trade_price(*, token_id: str) -> dict:
    """Get the most recent trade price for a market."""
    return _get_last_trade_price(_req(token_id=token_id))


# ============================================================
# CLI Commands: Data & Analytics (requires polymarket CLI)
# ============================================================


def get_leaderboard(
    *, period: str = "month", order_by: str = "pnl", limit: int = 20
) -> dict:
    """Get the Polymarket trader leaderboard (requires CLI)."""
    return _cli_get_leaderboard(period=period, order_by=order_by, limit=limit)


def get_positions(*, address: str) -> dict:
    """Get open positions for a wallet address (requires CLI)."""
    return _cli_get_positions(address=address)


def get_closed_positions(*, address: str) -> dict:
    """Get closed positions for a wallet address (requires CLI)."""
    return _cli_get_closed_positions(address=address)


def get_portfolio_value(*, address: str) -> dict:
    """Get portfolio value for a wallet address (requires CLI)."""
    return _cli_get_portfolio_value(address=address)


def get_trade_history(*, address: str, limit: int = 50) -> dict:
    """Get trade history for a wallet address (requires CLI)."""
    return _cli_get_trade_history(address=address, limit=limit)


def get_activity(*, address: str) -> dict:
    """Get activity feed for a wallet address (requires CLI)."""
    return _cli_get_activity(address=address)


def get_holders(*, condition_id: str) -> dict:
    """Get position holders for a market (requires CLI)."""
    return _cli_get_holders(condition_id=condition_id)


def get_open_interest(*, condition_id: str) -> dict:
    """Get open interest for a market (requires CLI)."""
    return _cli_get_open_interest(condition_id=condition_id)


def get_volume(*, event_id: str) -> dict:
    """Get volume data for an event (requires CLI)."""
    return _cli_get_volume(event_id=event_id)


def get_traded(*, address: str) -> dict:
    """Get markets traded by a wallet address (requires CLI)."""
    return _cli_get_traded(address=address)


# ============================================================
# CLI Commands: Enhanced Search & Tags (requires polymarket CLI)
# ============================================================


def cli_search_markets(*, query: str, limit: int = 20) -> dict:
    """Full-text market search via CLI (more powerful than search_markets)."""
    return _cli_search_markets(query=query, limit=limit)


def get_tags(*, limit: int | None = None) -> dict:
    """List all Polymarket tags (requires CLI)."""
    return _cli_get_tags(limit=limit)


def get_tag(*, tag: str) -> dict:
    """Get details for a specific tag (requires CLI)."""
    return _cli_get_tag(tag=tag)


def get_related_tags(*, tag: str) -> dict:
    """Get tags related to a given tag (requires CLI)."""
    return _cli_get_related_tags(tag=tag)


# ============================================================
# CLI Commands: Comments & Profiles (requires polymarket CLI)
# ============================================================


def get_comments(*, entity_type: str, entity_id: str) -> dict:
    """Get comments on an entity (requires CLI)."""
    return _cli_get_comments(entity_type=entity_type, entity_id=entity_id)


def get_comment(*, comment_id: str) -> dict:
    """Get a single comment by ID (requires CLI)."""
    return _cli_get_comment(comment_id=comment_id)


def get_user_comments(*, address: str) -> dict:
    """Get all comments by a user (requires CLI)."""
    return _cli_get_user_comments(address=address)


def get_profile(*, address: str) -> dict:
    """Get a public user profile (requires CLI)."""
    return _cli_get_profile(address=address)


# ============================================================
# CLI Commands: Sports Metadata (requires polymarket CLI)
# ============================================================


def cli_sports_list() -> dict:
    """List all sports on Polymarket (requires CLI)."""
    return _cli_sports_list()


def cli_sports_teams(*, league: str, limit: int = 50) -> dict:
    """Get teams for a league (requires CLI)."""
    return _cli_sports_teams(league=league, limit=limit)


# ============================================================
# CLI Commands: CLOB Extras (requires polymarket CLI)
# ============================================================


def get_tick_size(*, token_id: str) -> dict:
    """Get the minimum tick size for a market (requires CLI)."""
    return _cli_get_tick_size(token_id=token_id)


def get_fee_rate(*, token_id: str) -> dict:
    """Get the fee rate for a market (requires CLI)."""
    return _cli_get_fee_rate(token_id=token_id)


# ============================================================
# CLI Commands: Trading (requires polymarket CLI + wallet)
# ============================================================


def create_order(
    *,
    token_id: str,
    side: str,
    price: str,
    size: str,
    order_type: str = "GTC",
) -> dict:
    """Place a limit order (requires CLI + wallet)."""
    return _cli_create_order(
        token_id=token_id, side=side, price=price, size=size, order_type=order_type
    )


def market_order(*, token_id: str, side: str, amount: str) -> dict:
    """Place a market order (requires CLI + wallet)."""
    return _cli_market_order(token_id=token_id, side=side, amount=amount)


def cancel_order(*, order_id: str) -> dict:
    """Cancel a specific order (requires CLI + wallet)."""
    return _cli_cancel_order(order_id=order_id)


def cancel_all_orders() -> dict:
    """Cancel all open orders (requires CLI + wallet)."""
    return _cli_cancel_all_orders()


def get_balance(
    *, asset_type: str = "collateral", token_id: str | None = None
) -> dict:
    """Check wallet balance (requires CLI + wallet)."""
    return _cli_get_balance(asset_type=asset_type, token_id=token_id)


def get_orders(*, market: str | None = None) -> dict:
    """View open orders (requires CLI + wallet)."""
    return _cli_get_orders(market=market)


def get_user_trades() -> dict:
    """View your recent trades (requires CLI + wallet)."""
    return _cli_get_user_trades()


# ============================================================
# CLI Commands: On-Chain Operations (requires polymarket CLI + wallet)
# ============================================================


def ctf_split(*, condition_id: str, amount: str) -> dict:
    """Split USDC into YES/NO conditional tokens (requires CLI + wallet)."""
    return _cli_ctf_split(condition_id=condition_id, amount=amount)


def ctf_merge(*, condition_id: str, amount: str) -> dict:
    """Merge YES/NO tokens back into USDC (requires CLI + wallet)."""
    return _cli_ctf_merge(condition_id=condition_id, amount=amount)


def ctf_redeem(*, condition_id: str) -> dict:
    """Redeem winning tokens after market resolution (requires CLI + wallet)."""
    return _cli_ctf_redeem(condition_id=condition_id)


def approve_check(*, address: str | None = None) -> dict:
    """Check current contract approvals (requires CLI)."""
    return _cli_approve_check(address=address)


def approve_set() -> dict:
    """Approve all Polymarket contracts for trading (requires CLI + wallet)."""
    return _cli_approve_set()
