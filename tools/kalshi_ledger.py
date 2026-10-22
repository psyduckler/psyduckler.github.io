#!/usr/bin/env python3
"""Fetch the settled Kalshi ledger from Tokay's R2 bucket (read-only).

Source (since 2026-10-18; the old GitHub settled_ledger/settled_by_strategy.jsonl
stopped updating 2026-10-16 when Kalshi moved to Tokay):
  bucket kalshi-exec-reports -> ledger/latest.json -> {prefix}settled_by_strategy.jsonl
Same row schema as the old GitHub file. Tokay's ledger job publishes hourly 07:25–23:25 CT
(the 07:25 CT run is the first with all of yesterday). OpenSea comes from Tokay's opensea-ledger job (opensea_published.py).

Credentials: shared read-only R2 key in /home/box/agent-data/shared/r2-readonly/
(access_key_id, secret_access_key), account from shared/cloudflare/account_id.
Keys are read from disk only and never printed or committed.

Usage:
  python3 tools/kalshi_ledger.py fetch OUT.jsonl   download only (prints prefix + row count)
  python3 tools/kalshi_ledger.py update            append fully settled CT days to data/pnl_history.json
update aggregates strategy_leg rows by settled_time_ct date (net_pnl, fees), skips the
current CT day (still open) and any day not over when the ledger run happened, and refuses to write if any day
already on the page disagrees. It then runs pnl_categories.update() (categories for kalshi/polymarket + OpenSea).
"""
import json, sys, datetime as dt
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

SHARED = Path("/home/box/agent-data/shared")
BUCKET = "kalshi-exec-reports"


def client():
    import boto3
    rd = lambda p: (SHARED / p).read_text().strip()
    return boto3.client("s3", region_name="auto",
                        endpoint_url=f"https://{rd('cloudflare/account_id')}.r2.cloudflarestorage.com",
                        aws_access_key_id=rd("r2-readonly/access_key_id"),
                        aws_secret_access_key=rd("r2-readonly/secret_access_key"))


HIST = Path(__file__).resolve().parent.parent / "data/pnl_history.json"


def fetch(out):
    s3 = client()
    latest = json.loads(s3.get_object(Bucket=BUCKET, Key="ledger/latest.json")["Body"].read())
    if latest.get("ok") is False:
        sys.exit(f"latest run not ok: {latest.get('prefix')}")
    prefix = latest["prefix"].rstrip("/") + "/"
    body = s3.get_object(Bucket=BUCKET, Key=prefix + "settled_by_strategy.jsonl")["Body"].read()
    Path(out).write_bytes(body)
    return prefix, body.count(b"\n")


def day_agg(date, v, fees):
    r = lambda x: round(x, 2)
    return {"date": date, "n": len(v), "w": sum(x > 0 for x in v), "l": sum(x < 0 for x in v),
            "net": r(sum(v)), "fees": r(fees), "gw": r(sum(x for x in v if x > 0)),
            "gl": r(sum(x for x in v if x < 0)), "best": r(max(v)), "worst": r(min(v))}


def update(tmp="/tmp/kalshi_settled_by_strategy.jsonl"):
    prefix, _ = fetch(tmp)
    legs = defaultdict(list)
    for line in open(tmp):
        row = json.loads(line)
        if row.get("row_type") == "strategy_leg" and row.get("status") == "settled":
            legs[row["settled_time_ct"][:10]].append(row)
    H = json.loads(HIST.read_text())
    K, S = H["kalshi"], H["ksum"]
    have = {d["date"]: d for d in K}
    for date, d in have.items():  # parity guard: never overwrite history silently
        if date in legs and abs(sum(x["net_pnl"] for x in legs[date]) - d["net"]) > 0.01:
            sys.exit(f"mismatch on {date}: page {d['net']} vs ledger; not writing")
    today = dt.datetime.now(ZoneInfo("America/Chicago")).date().isoformat()
    try:  # a day is only complete if the ledger run itself happened after it ended (run id 20261018T160738Z_...)
        ran = dt.datetime.strptime(prefix.rstrip("/").rsplit("/", 1)[-1][:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
        today = min(today, ran.astimezone(ZoneInfo("America/Chicago")).date().isoformat())
    except ValueError:
        pass
    added = []
    for date in sorted(legs):
        if date <= K[-1]["date"] or date >= today:
            continue
        v = [x["net_pnl"] for x in legs[date]]
        K.append(day_agg(date, v, sum(x["fees"] for x in legs[date]))); added.append(date)
        for x in v:  # same histogram as ksum: 5$ bins over [lo, hi], tails clamped into the end bins
            S["nw" if x > 0 else "nl"] += x > 0 or x < 0
            if x > 0: S["sw"] = round(S["sw"] + x, 2)
            if x < 0: S["sl"] = round(S["sl"] + x, 2)
            S["clipped"] += not (S["lo"] <= x <= S["hi"])
            S["hist"][min(len(S["hist"]) - 1, max(0, int((x - S["lo"]) // 5)))] += 1
    if added:
        run = prefix.rstrip("/").rsplit("/", 1)[-1]
        last = dt.date.fromisoformat(K[-1]["date"]); nxt = last + dt.timedelta(days=1)
        fmt = lambda d: d.strftime("%b %-d").lower()
        H["note"] = (f"aggregates only. kalshi: Tokay R2 kalshi-exec-reports {run}/settled_by_strategy.jsonl "
                     f"strategy_leg rows by CT settle date, through {last}. polymarket:" + H["note"].split("polymarket:", 1)[1])
        cov = H["coverage"].split(". polymarket", 1)[1]
        H["coverage"] = (f"kalshi from the settled ledger, {fmt(dt.date.fromisoformat(K[0]['date']))} → {fmt(last)} "
                         f"({fmt(nxt)} left out: CT settle day still open). polymarket" + cov)
        HIST.write_text(json.dumps(H, indent=1) + "\n")
    print(f"{BUCKET}/{prefix} added={added or 'none'}")
    import pnl_categories  # P&L by kind of trade + OpenSea (writes data/pnl_cats.json, pnl_history.json["opensea"])
    pnl_categories.update(tmp)
    return added


if __name__ == "__main__":
    if sys.argv[1:2] == ["update"]:
        update()
    else:
        args = [a for a in sys.argv[1:] if a != "fetch"]
        prefix, n = fetch(args[0] if args else "settled_by_strategy.jsonl")
        print(f"{BUCKET}/{prefix} rows={n}")
