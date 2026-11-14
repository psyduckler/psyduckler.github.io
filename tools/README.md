# tools

- `build.py` builds the site (incl. `/pnl/` via `pnl_main.py`) from `data/*.json`.
- `console.py update` refreshes `/pnl/` data from the trading console (every venue), then run `build.py`.

## Refresh command (daily routine, or by hand) — since 2026-10-31

    python3 tools/console.py update && python3 tools/build.py

`console.py` reads the trading console (Tokay), read-only: settled P&L after fees by CT day for kalshi, polymarket,
hyperliquid, opensea and robinhood, and per book category. It writes `data/pnl_history.json` (`{kalshi, polymarket, hyperliquid,
opensea, robinhood: [{date, net}]}`) and `data/pnl_cats.json` (rows `{d, v, c, net}`, v = k/p/h/o/e). Only CT days before today are
written. Every run replaces the whole history, so late settles restate old days; the run prints a `restated ...` /
`dropped ...` line for each day that changed. `python3 tools/console.py check` runs everything without writing.

Checks (the update refuses to write if any fails):
1. Σ of the per-venue daily series == the console overview's all-time tile (both incl. today), ±$0.05.
2. the console's last-7-days by-day nets == the series, per venue, to the cent (days before today).
3. Σ books per category == the overview's per-category all-time, ±$0.25 (books round per day).
4. per venue-day, Σ books within $0.10 of the venue day; then the categories are split to the cent (largest remainder),
   and `pnl_main.py` re-checks Σ categories == venue for every view and window.

Token: env `TOKAY_MCP_TOKEN_RO` only; console URL: env `TOKAY_CONSOLE_URL` or a box file outside this repo. Never print
or commit either. Never write the console's balances, open risk, positions, book or strategy names or params.

Categories are the console's (per book): Bernard's 14 (weather highs / lows / rain / snow, mentions, copy, crypto, nft,
golf, rotten tomatoes, cpi, youtube, basketball, manual) plus commodities, liquidity rewards, football, netflix and
deadlines. A new console category shows up gray-dashed with a warning until it gets a color in `console.py`.

## Retired 2026-10-31 (kept for history; their `update` entry points exit)

`kalshi_ledger.py` (R2 bucket kalshi-exec-reports, gone 2026-10-30), `pnl_categories.py` (ticker-based category rules),
`pm_published.py` (dashboard pub/pm_ledger.json), `opensea_published.py` / `opensea_ledger.py` (Tokay MCP service files,
old token dead 2026-10-30).

## No-token refresh (scheduled run via the console connector) — since 2026-11-13

When `TOKAY_MCP_TOKEN_RO` isn't on the box, call the "Tokay PnL console" connector's `pnl` tool 24 times
(windows all/90d/30d/7d x venues all/kalshi/pm/hl/os/eq), save each result to a file, then:

    python3 tools/console_pnl.py save /workspace/psy/pnl_refresh/YYYYMMDD <24 result files>
    python3 tools/console_pnl.py update /workspace/psy/pnl_refresh/YYYYMMDD && python3 tools/build.py && python3 tools/test_pnl_public.py

`console_pnl.py` never talks to the console; it only reads the saved tool output. It refuses to write if the 24
responses disagree on `today`, a running total doesn't step by its day net, categories don't sum to the net, venues
don't sum to combined (per window and per day), or a shorter window's day nets differ from the all-time window's.
It prints `restated` / `dropped` lines against the current `data/pnl_history.json` and a suggested commit message.
Full routine: /workspace/psy/pnl_refresh/ROUTINE_CONNECTOR.md (box only, not in this repo).
