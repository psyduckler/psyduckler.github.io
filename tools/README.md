# tools

- `build.py` builds the site (incl. `/pnl/` via `pnl_main.py`) from `data/*.json`.
- `kalshi_ledger.py update` appends fully settled Kalshi CT days to `data/pnl_history.json`, then refreshes
  P&L by kind of trade and OpenSea (`pnl_categories.py update`); then run `build.py`.

## Refresh command (nightly routine, or by hand)

    python3 tools/kalshi_ledger.py update && python3 tools/build.py

One command refreshes everything on /pnl/: Kalshi days, the 8 categories for Kalshi + Polymarket, and OpenSea
(days + category). `python3 tools/pnl_categories.py update` alone re-tags categories and refreshes OpenSea without
adding Kalshi days. If Tokay can't be reached, the last committed OpenSea days are kept (a WARNING is printed).

## P&L by kind of trade (since 2026-10-18)

`pnl_categories.py` tags every settled row with one of 8 categories (wx_high, wx_low, wx_rain, mention, copy, crypto,
nft, manual; rules + colors from Bernard's handoff) and writes `data/pnl_cats.json`: one row per CT day x venue x
category with n, w, l, net, gw, gl. For every venue and day the categories' cents equal the day on the page exactly;
the update and `pnl_main.py` (every venue x window) both refuse to build otherwise. Kalshi days before the settled
ledger (jul hand trades) are manual. Polymarket categories come from the same release rows as the page.

## OpenSea source (since 2026-10-18)

`opensea_ledger.py` reads, through the Tokay MCP (token `/home/box/agent-data/shared/tokay/mcp_token`, read at runtime,
never printed or committed): opensea-bots `/tokay/data/research/nft_ledger/pull.json.gz` (sales), opensea-advisor's
cached gas / ETH-USD / attribution (`/tokay/data/advisor/ledger/`) and its `ledger.py` (the Tokay copy of nft_ledger),
then runs that ledger locally in a temp dir. Flips count on their CT sale day; overhead gas on the CT day it was spent,
so all days sum to the ledger's `totals.net_usd`. Only fully settled CT days (before the pull's CT date) are written to
`data/pnl_history.json["opensea"]`.

## Kalshi PnL source (since 2026-10-18)

Kalshi moved to Tokay on 2026-10-16 and the GitHub `settled_ledger/settled_by_strategy.jsonl`
stopped updating. The settled ledger now lives in Cloudflare R2, bucket `kalshi-exec-reports`:
`ledger/latest.json` -> `prefix` (newest good run) -> `settled_by_strategy.jsonl` (same schema).
Tokay's ledger job runs daily around 10:30 CT. `kalshi_ledger.py` reads it with the shared
read-only R2 key on the box, sums `strategy_leg` rows by `settled_time_ct` date, leaves out the
current CT day, and refuses to write if a day already on the page doesn't match.
Only daily aggregates are committed; never commit keys, strategy names or positions. A day is only added once the
ledger run itself happened after that CT day ended.

Polymarket still comes from the pm-private R2 release (`closes.jsonl`), updated by hand.

`data/pnl_history.json` `pm_status`: optional short note shown on the polymarket view and under recent days. Set it to "" once a new pm release lands.
