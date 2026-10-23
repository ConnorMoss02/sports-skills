# Gemini Predictions — API Reference

Public, unauthenticated endpoints under `https://api.gemini.com/v1/prediction-markets` (GET only).

## Commands

| Command | Required | Optional | Description |
|---|---|---|---|
| `get_events` | | league, status, limit, offset | One upstream page of Sports events. `status`: `active` (default), `approved`, `closed`, `under_review`, `settled`, `invalid`. `limit` 1-500 (default 50). `offset` ≥ 0. Returns `events`, `pagination` (`limit`, `offset`, `total`), `next_offset` (`null` on the last page) and `warnings` when the page is empty before `total` (listing incomplete, not exhausted) |
| `get_event` | event_ticker | | One event by ticker (letters, digits, `-`, `_`; e.g. `NBA-2610232300-MIN-ORL-M`) |
| `search_markets` | | query, league, market_type, limit | Active markets whose title or participant names contain every query token. `market_type`: `moneyline`, `spread`, `total`, `prop`, `correct_score`, `to_advance`, `futures`, `other`. `limit` 1-500 (default 50). Returns `markets`, `events_scanned`, `truncated`, optional `warnings` |
| `get_todays_events` | | league, limit | Active events whose `startTime` falls on today's UTC date. Returns `events`, `date`, `truncated`, optional `warnings` |

Invalid input (unknown league/status/market_type, `limit`/`offset` that is not a whole number in range — fractions, booleans and infinities included — or a malformed ticker) fails before any request.

## Leagues

Each code below was verified against the full live Sports listing (2026-10-23).

| Code | Ticker prefix | `sport` filter |
|---|---|---|
| `nba` | `NBA` | basketball |
| `wnba` | `WNBA` | basketball |
| `nfl` | `NFL` | american_football |
| `cfb` | `NCAAF` | american_football |
| `mlb` | `MLB` | baseball |
| `nhl` | `NHL` | hockey |
| `epl` | `EPL` | soccer |
| `laliga` | `LALIGA` | soccer |
| `mls` | `MLS` | soccer |
| `ligamx` | `LIGAMX` | soccer |
| `ufc` | `UFC` | mixed_martial_arts |
| `f1` | `F1` | motorsports |
| `golf` | `GOLF` | golf |

Upstream filters by sport only, so results are also filtered by exact ticker prefix (e.g. a `WNBA-` event never appears under `nba`, nor `NCAAF-` under `nfl`). Futures with other prefixes and no `sportsMarket` (`NFLMVP2026`, `NBAF-2627CHAMP`, `CFBSEC26`, ...) match no league; list them with `get_events` and no `league`.

## Event fields

| Field | Meaning |
|---|---|
| `ticker`, `id`, `name` | Event identity and title |
| `league` | Ticker prefix (`NBA`, `NCAAF`, `EPL`, ...) |
| `sport`, `market_type`, `market_subject`, `market_scope` | From upstream `sportsMarket` (`sport`, `type`, `subject`, `scope.type`), e.g. `moneyline` / `contest` / `full_contest` |
| `status` | Event status |
| `start_time` | Kickoff (`startTime`, UTC) or `null`. Not `effectiveDate` (listing) or `expiryDate` (settlement deadline) |
| `participants` | `name`, `abbreviation`, `side` (`home`/`away`) |
| `contracts` | See below |
| `child_events` | Other markets for the same game (spreads, totals, props), each normalized the same way with `parent_ticker` |
| `price_basis`, `execution_guaranteed`, `retrieved_at` | `cached_snapshot`, `false`, original retrieval time (kept on cache hits) |
| `_raw` | Full upstream payload (untrusted text) |

## Contract fields

`id`, `ticker`, `label`, `side` (`home`/`away`/`tie` from `sportsSide`, may be `null`), `status`, `market_state` (`open`/...), `is_combo`, `instrument_symbol`, `strike`, and prices `buy_yes`, `buy_no`, `sell_yes`, `sell_no`, `best_bid`, `best_ask`, `last_trade_price`.

Prices are probabilities in [0, 1]. Any absent, non-numeric, NaN/infinite or out-of-range value is `null` — never coerced to 0. One-sided books are common (e.g. a `best_ask` with no `best_bid`).

## Caveats

- Prices are reference snapshots, not executable quotes; no size, depth or fill is implied, and volume says nothing about liquidity.
- Soccer moneylines are three-way (home/away/tie) settled on regulation time; never reduce them to two-way.
- Search and today scans are bounded (5 pages of 100 events). Check `truncated` and `warnings` before treating an empty result as "no markets". A failed first page is an error; an empty page before the reported total ends the scan as partial (`truncated`, `warnings`).
- Errors: redirects are refused, HTTP errors (e.g. 403, 429) are reported once without retry, malformed JSON and unexpected payload shapes are errors.
- Supports `SPORTS_SKILLS_REPLAY=record|replay|fill` like other modules. The in-process cache is used only with replay off, so a replay run never serves a live-cached response.
