"""Bounded Polymarket UCL pagination; synthetic listings, real adapter shape."""
from unittest.mock import patch

import pytest

from sports_skills import markets, polymarket
from tests.test_ucl_market_urls import KALSHI_URL, _ok, _poly_event
from tests.test_ucl_market_urls import env as _env_fixture

env = _env_fixture


def full_page():
    return [_poly_event(), *[{"id": f"prop-{i}", "slug": f"prop-{i}", "markets": []} for i in range(99)]]


def test_second_polymarket_page_finishes_unique_search(env):
    env["poly_list"].side_effect = [_ok({"events": full_page()}), _ok({"events": []})]
    data = markets.compare_market_url(url=KALSHI_URL)["data"]
    assert data["sources"]["polymarket"]["outcome"] == "ok"
    assert data["completeness"]["complete"] is True
    assert env["poly_list"].call_count == 2
    assert env["poly_list"].call_args.kwargs["offset"] == 100
    assert all({q["venue"] for q in side["quotes"]} == {"polymarket", "kalshi"} for side in data["side_prices"].values())


def test_later_polymarket_page_failure_never_selects_first_match(env):
    env["poly_list"].side_effect = [_ok({"events": full_page()}), {"status": False, "data": None, "message": "HTTP 503"}]
    data = markets.compare_market_url(url=KALSHI_URL)["data"]
    assert env["poly_list"].call_count == 2
    assert data["sources"]["polymarket"]["outcome"] == "incomplete"
    assert data["completeness"]["complete"] is False
    assert all(q["venue"] == "kalshi" for side in data["side_prices"].values() for q in side["quotes"])


def test_adapter_forwards_validated_offset():
    with patch("sports_skills.polymarket._connector._get_sports_config", return_value={"ucl": {"series": "fixture-series"}}), patch("sports_skills.polymarket._connector._gamma_request", return_value=[]) as request:
        result = polymarket.get_todays_events(sport="ucl", limit=100, offset=100)
    assert result["status"] is True
    assert request.call_args.kwargs["params"]["offset"] == 100
    assert request.call_args.args == ("/events",)


@pytest.mark.parametrize("offset", [-1, True, "oops", 0.5])
def test_invalid_offset_never_reaches_provider(offset):
    with patch("sports_skills.polymarket._connector._gamma_request") as request:
        result = polymarket.get_todays_events(sport="ucl", offset=offset)
    assert result["status"] is False
    request.assert_not_called()


def _distinct_full_page(tag):
    return [{"id": f"{tag}-{i}", "slug": f"{tag}-{i}", "markets": []} for i in range(100)]


def test_duplicate_candidate_on_second_page_is_ambiguous(env):
    twin = _poly_event()
    twin["id"] = "1149400"
    env["poly_list"].side_effect = [_ok({"events": full_page()}), _ok({"events": [twin]})]
    data = markets.compare_market_url(url=KALSHI_URL)["data"]
    assert env["poly_list"].call_count == 2
    assert data["sources"]["polymarket"]["outcome"] != "ok"
    assert "ambiguous" in data["sources"]["polymarket"]["detail"].lower()
    assert all(q["venue"] == "kalshi" for side in data["side_prices"].values() for q in side["quotes"])


def test_repeated_page_is_incomplete(env):
    page = _ok({"events": full_page()})
    env["poly_list"].side_effect = [page, page]
    data = markets.compare_market_url(url=KALSHI_URL)["data"]
    assert env["poly_list"].call_count == 2
    assert data["sources"]["polymarket"]["outcome"] == "incomplete"
    assert data["completeness"]["complete"] is False


def test_page_cap_is_incomplete_and_bounded(env):
    env["poly_list"].side_effect = [
        _ok({"events": full_page()}),
        _ok({"events": _distinct_full_page("b")}),
        _ok({"events": _distinct_full_page("c")}),
        _ok({"events": []}),
    ]
    data = markets.compare_market_url(url=KALSHI_URL)["data"]
    assert env["poly_list"].call_count == 3
    assert [c.kwargs["offset"] for c in env["poly_list"].call_args_list] == [0, 100, 200]
    assert data["sources"]["polymarket"]["outcome"] == "incomplete"
    assert all(q["venue"] == "kalshi" for side in data["side_prices"].values() for q in side["quotes"])


def test_short_first_page_needs_one_call(env):
    data = markets.compare_market_url(url=KALSHI_URL)["data"]
    assert env["poly_list"].call_count == 1
    assert env["poly_list"].call_args.kwargs["offset"] == 0
    assert data["sources"]["polymarket"]["outcome"] == "ok"


@pytest.mark.parametrize("kwargs", [{}, {"offset": 0}])
def test_default_offset_keeps_the_original_query(kwargs):
    config = {"ucl": {"series": "fixture-series"}}
    with patch("sports_skills.polymarket._connector._get_sports_config", return_value=config), patch(
        "sports_skills.polymarket._connector._gamma_request", return_value=[]
    ) as request:
        result = polymarket.get_todays_events(sport="ucl", **kwargs)
    assert result["status"] is True
    params = request.call_args.kwargs["params"]
    assert "offset" not in params
    assert params["limit"] == 30
