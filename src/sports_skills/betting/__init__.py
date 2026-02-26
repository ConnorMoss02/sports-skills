"""Betting analysis — odds conversion, de-vigging, edge detection, Kelly criterion.

Source-agnostic: works with odds from ESPN, Polymarket, Kalshi, or any sportsbook.
Pure computation — no network calls, no auth required.
"""

from __future__ import annotations

from sports_skills.betting._calcs import convert_odds as _convert_odds
from sports_skills.betting._calcs import devig as _devig
from sports_skills.betting._calcs import evaluate_bet as _evaluate_bet
from sports_skills.betting._calcs import find_arbitrage as _find_arbitrage
from sports_skills.betting._calcs import find_edge as _find_edge
from sports_skills.betting._calcs import kelly_criterion as _kelly_criterion
from sports_skills.betting._calcs import line_movement as _line_movement
from sports_skills.betting._calcs import parlay_analysis as _parlay_analysis


def _req(**kwargs):
    """Build request_data dict from kwargs."""
    return {"params": {k: v for k, v in kwargs.items() if v is not None}}


def convert_odds(*, odds: float, from_format: str = "american") -> dict:
    """Convert odds between American, decimal, and probability formats."""
    return _convert_odds(_req(odds=odds, from_format=from_format))


def devig(*, odds: str, format: str = "american") -> dict:
    """Remove vig/juice from sportsbook odds to get fair probabilities."""
    return _devig(_req(odds=odds, format=format))


def find_edge(*, fair_prob: float, market_prob: float) -> dict:
    """Compare fair probability to market price — compute edge, EV, and Kelly."""
    return _find_edge(_req(fair_prob=fair_prob, market_prob=market_prob))


def kelly_criterion(*, fair_prob: float, market_prob: float) -> dict:
    """Compute the Kelly fraction from fair and market probabilities."""
    return _kelly_criterion(_req(fair_prob=fair_prob, market_prob=market_prob))


def evaluate_bet(
    *,
    book_odds: str,
    market_prob: float,
    book_format: str = "american",
    outcome: int = 0,
) -> dict:
    """Full bet evaluation: book odds + market price → devig → edge → Kelly."""
    return _evaluate_bet(
        _req(
            book_odds=book_odds,
            market_prob=market_prob,
            book_format=book_format,
            outcome=outcome,
        )
    )


def find_arbitrage(
    *, market_probs: str, labels: str | None = None
) -> dict:
    """Detect arbitrage opportunities across outcomes."""
    return _find_arbitrage(_req(market_probs=market_probs, labels=labels))


def parlay_analysis(
    *,
    legs: str,
    parlay_odds: float,
    odds_format: str = "american",
    correlation: float = 0.0,
) -> dict:
    """Analyze a multi-leg parlay: combined probability, EV, and Kelly."""
    return _parlay_analysis(
        _req(
            legs=legs,
            parlay_odds=parlay_odds,
            odds_format=odds_format,
            correlation=correlation,
        )
    )


def line_movement(
    *,
    open_odds: float | None = None,
    close_odds: float | None = None,
    open_line: float | None = None,
    close_line: float | None = None,
    market_type: str = "moneyline",
) -> dict:
    """Analyze line movement between open and close."""
    return _line_movement(
        _req(
            open_odds=open_odds,
            close_odds=close_odds,
            open_line=open_line,
            close_line=close_line,
            market_type=market_type,
        )
    )
