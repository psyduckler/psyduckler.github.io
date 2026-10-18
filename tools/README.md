# tools

- `build.py` builds the site (incl. `/pnl/` via `pnl_main.py`) from `data/*.json`.
- `kalshi_ledger.py update` appends fully settled Kalshi CT days to `data/pnl_history.json`,
  then run `build.py`.

## Kalshi PnL source (since 2026-10-18)

Kalshi moved to Tokay on 2026-10-16 and the GitHub `settled_ledger/settled_by_strategy.jsonl`
stopped updating. The settled ledger now lives in Cloudflare R2, bucket `kalshi-exec-reports`:
`ledger/latest.json` -> `prefix` (newest good run) -> `settled_by_strategy.jsonl` (same schema).
Tokay's ledger job runs daily around 10:30 CT. `kalshi_ledger.py` reads it with the shared
read-only R2 key on the box, sums `strategy_leg` rows by `settled_time_ct` date, leaves out the
current CT day, and refuses to write if a day already on the page doesn't match.
Only daily aggregates are committed; never commit keys, strategy names or positions.

Polymarket still comes from the pm-private R2 release (`closes.jsonl`), updated by hand.

`data/pnl_history.json` `pm_status`: optional short note shown on the polymarket view and under recent days. Set it to "" once a new pm release lands.
