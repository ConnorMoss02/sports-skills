"""Regression checks for independent review findings; offline provider mutations."""
import pytest

from sports_skills import markets
from tests.test_ucl_market_urls import (
    KALSHI_URL,
    POLY_URL,
    _kalshi_child,
    _kalshi_event,
    _ok,
    _poly_child,
    _poly_event,
    _set_kalshi_listing,
    _set_kalshi_source,
    _set_poly_listing,
    _set_poly_source,
)
from tests.test_ucl_market_urls import env as _env_fixture

env = _env_fixture


@pytest.mark.parametrize("side", ["home", "away", "draw"])
def test_rules_matchup_must_agree_with_every_contract(env, side):
    event = _kalshi_event()
    child = _kalshi_child(event, side)
    assert "PSG vs Barcelona" in child["rules_primary"]
    child["rules_primary"] = child["rules_primary"].replace("PSG vs Barcelona", "PSG vs Liverpool")
    _set_kalshi_source(env, event)
    assert markets.compare_market_url(url=KALSHI_URL)["status"] is False


@pytest.mark.parametrize("mode", ["later_failure", "page_limit", "empty_page_with_cursor"])
def test_incomplete_search_does_not_select_counterpart(env, mode):
    first = _ok({"events": [_kalshi_event()], "cursor": "another-page"})
    if mode == "later_failure":
        env["kalshi_list"].side_effect = [first, {"status": False, "data": None, "message": "HTTP 503"}]
    elif mode == "empty_page_with_cursor":
        env["kalshi_list"].side_effect = [first, _ok({"events": [], "cursor": "still-more"})]
    else:
        env["kalshi_list"].return_value = first
    result = markets.compare_market_url(url=POLY_URL)
    assert result["status"] is True
    data = result["data"]
    assert data["completeness"]["complete"] is False
    assert data["sources"]["kalshi"]["outcome"] != "ok"
    assert data["sources"]["kalshi"]["detail"]
    for view in data["side_prices"].values():
        assert all(q["venue"] != "kalshi" for q in view["quotes"])


def test_missing_venue_outcome_is_explicit_partial(env):
    event = _poly_event()
    _poly_child(event, "draw")["outcomes"][0]["price"] = None
    _set_poly_source(env, event)
    result = markets.compare_market_url(url=POLY_URL)
    assert result["status"] is True
    data = result["data"]
    assert data["completeness"]["complete"] is False
    assert data["sources"]["polymarket"]["missing_sides"] == ["draw"]
    assert data["sources"]["polymarket"]["outcome"] != "ok"
    assert {q["venue"] for q in data["side_prices"]["home"]["quotes"]} == {"polymarket", "kalshi"}


@pytest.mark.parametrize("field", ["id", "clob_token_id"])
def test_duplicate_poly_identity_is_rejected(env, field):
    event = _poly_event()
    home, away = _poly_child(event, "home"), _poly_child(event, "away")
    if field == "id":
        away[field] = home[field]
    else:
        away["outcomes"][0][field] = home["outcomes"][0][field]
    _set_poly_source(env, event)
    assert markets.compare_market_url(url=POLY_URL)["status"] is False


@pytest.mark.parametrize("value", [None, "", "   "])
def test_empty_poly_contract_identity_is_rejected(env, value):
    event = _poly_event()
    _poly_child(event, "home")["id"] = value
    _set_poly_source(env, event)
    assert markets.compare_market_url(url=POLY_URL)["status"] is False


# ------------------------------------------------------------
# The same findings on the normalized adapter shape. polymarket.get_event_details /
# get_todays_events return _normalize_market output (outcomes[].price,
# outcomes[].clob_token_id, clob_token_ids), never Gamma's raw outcomePrices /
# clobTokenIds JSON strings.
# ------------------------------------------------------------


def test_missing_normalized_yes_price_is_explicit_partial(env):
    event = _poly_event()
    # _normalize_market omits "price" when Gamma's outcomePrices entry is null.
    del _poly_child(event, "draw")["outcomes"][0]["price"]
    _set_poly_source(env, event)
    result = markets.compare_market_url(url=POLY_URL)
    assert result["status"] is True
    data = result["data"]
    assert data["completeness"]["complete"] is False
    assert data["sources"]["polymarket"]["outcome"] == "partial"
    assert data["sources"]["polymarket"]["missing_sides"] == ["draw"]
    assert "polymarket" in data["completeness"]["usable_sources"]
    assert data["sources"]["kalshi"]["outcome"] == "ok"
    assert data["sources"]["kalshi"]["missing_sides"] == []
    assert {q["venue"] for q in data["side_prices"]["home"]["quotes"]} == {"polymarket", "kalshi"}
    assert {q["venue"] for q in data["side_prices"]["draw"]["quotes"]} == {"kalshi"}
    assert any("partial" in w for w in data["warnings"])


def test_counterpart_missing_sides_are_in_fixed_side_order(env):
    event = _kalshi_event()
    for side in ("away", "home"):
        _kalshi_child(event, side)["last_price_dollars"] = ""
    _set_kalshi_listing(env, [event])
    data = markets.compare_market_url(url=POLY_URL)["data"]
    assert data["sources"]["kalshi"]["outcome"] == "partial"
    assert data["sources"]["kalshi"]["missing_sides"] == ["home", "away"]
    assert "kalshi" in data["completeness"]["usable_sources"]
    assert data["completeness"]["complete"] is False


def test_all_sides_priced_is_complete(env):
    data = markets.compare_market_url(url=POLY_URL)["data"]
    assert data["completeness"]["complete"] is True
    assert {name: r["missing_sides"] for name, r in data["sources"].items()} == {"polymarket": [], "kalshi": []}


def test_duplicate_normalized_yes_token_is_rejected(env):
    event = _poly_event()
    home, away = _poly_child(event, "home"), _poly_child(event, "away")
    away["outcomes"][0]["clob_token_id"] = home["outcomes"][0]["clob_token_id"]
    _set_poly_source(env, event)
    assert markets.compare_market_url(url=POLY_URL)["status"] is False


def test_whitespace_padded_duplicate_id_is_rejected(env):
    event = _poly_event()
    _poly_child(event, "away")["id"] = f"  {_poly_child(event, 'home')['id']} "
    _set_poly_source(env, event)
    assert markets.compare_market_url(url=POLY_URL)["status"] is False


@pytest.mark.parametrize("value", [True, False, ["5409678"], {"id": "5409678"}])
def test_non_scalar_or_bool_poly_contract_id_is_rejected(env, value):
    event = _poly_event()
    _poly_child(event, "home")["id"] = value
    _set_poly_source(env, event)
    assert markets.compare_market_url(url=POLY_URL)["status"] is False


def test_poly_contract_id_is_stripped_and_case_preserved(env):
    event = _poly_event()
    _poly_child(event, "home")["id"] = " 5409678Ab "
    _set_poly_source(env, event)
    data = markets.compare_market_url(url=POLY_URL)["data"]
    assert data["source_market"]["contracts"]["home"] == "5409678Ab"


def test_missing_token_is_absent_not_blank(env):
    event = _poly_event()
    del _poly_child(event, "draw")["outcomes"][0]["clob_token_id"]
    _set_poly_source(env, event)
    data = markets.compare_market_url(url=POLY_URL)["data"]
    draw = [q for q in data["side_prices"]["draw"]["quotes"] if q["venue"] == "polymarket"]
    assert len(draw) == 1 and "token_id" not in draw[0]


def test_full_polymarket_listing_page_does_not_select_counterpart(env):
    filler = [{"slug": f"ucl-aaa-bbb-2026-09-{d:02d}-total-corners", "markets": []} for d in range(1, 100)]
    _set_poly_listing(env, [_poly_event(), *filler])
    data = markets.compare_market_url(url=KALSHI_URL)["data"]
    assert data["sources"]["polymarket"]["outcome"] == "incomplete"
    assert data["sources"]["polymarket"]["detail"]
    assert data["completeness"]["complete"] is False
    assert all(q["venue"] != "polymarket" for view in data["side_prices"].values() for q in view["quotes"])
    assert data["sources"]["kalshi"]["outcome"] == "ok"


def test_repeating_kalshi_cursor_is_bounded(env):
    page = _ok({"events": [_kalshi_event()], "cursor": "loop"})
    env["kalshi_list"].return_value = page
    data = markets.compare_market_url(url=POLY_URL)["data"]
    assert env["kalshi_list"].call_count == 2
    assert data["sources"]["kalshi"]["outcome"] == "incomplete"


def test_tie_rules_naming_another_matchup_is_rejected_as_counterpart(env):
    event = _kalshi_event()
    tie = _kalshi_child(event, "draw")
    tie["rules_primary"] = tie["rules_primary"].replace("PSG vs Barcelona", "Liverpool vs Barcelona")
    _set_kalshi_listing(env, [event])
    data = markets.compare_market_url(url=POLY_URL)["data"]
    assert data["sources"]["kalshi"]["outcome"] != "ok"
    assert all(q["venue"] != "kalshi" for view in data["side_prices"].values() for q in view["quotes"])


def test_rules_matchup_in_either_order_is_accepted(env):
    event = _kalshi_event()
    for m in event["markets"]:
        m["rules_primary"] = m["rules_primary"].replace("PSG vs Barcelona", "Barcelona vs PSG")
    _set_kalshi_source(env, event)
    assert markets.compare_market_url(url=KALSHI_URL)["status"] is True
