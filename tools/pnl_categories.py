#!/usr/bin/env python3
"""P&L by kind of trade: tag every settled row with one of 8 categories, commit daily aggregates only.

Writes data/pnl_cats.json: rows {d, v, c, n, w, l, net, gw, gl} = per CT day, per venue (k kalshi, p polymarket,
o opensea), per category. Also writes data/pnl_history.json["opensea"] (daily venue totals, same shape as kalshi/polymarket).
Nothing else is committed: no tickers, books, strategies, positions, balances or keys.

Invariant (checked here and again in pnl_main.py): for every venue and day, the categories' cents sum to the venue's
day net on /pnl/ exactly. Every row lands in exactly one category; manual is the catch-all.

Sources:
  kalshi      R2 kalshi-exec-reports ledger (kalshi_ledger.py), strategy_leg rows, only for days already on the page.
              Days on the page from before the ledger (jul 6-19 hand trades) are manual.
  polymarket  R2 pm-private latest release closes.jsonl (same rows as the page), book = strategy_id, metric from slug.
  opensea     Tokay opensea-ledger job, published ledger (opensea_published.py): fully settled CT days only (before the pull's CT date). If Tokay can't be
              reached, the last committed OpenSea days are kept and a warning is printed.

Usage: python3 tools/pnl_categories.py update   (kalshi_ledger.py update calls this too)
"""
import json, sys, datetime as dt
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent
HIST, CATS = ROOT / "data/pnl_history.json", ROOT / "data/pnl_cats.json"
CT = ZoneInfo("America/Chicago")

# key, label, venues, light color, dark color (fixed order, never cycled)
CATEGORIES = [
    ("wx_high", "Weather · highs", "kp", "#2a78d6", "#3987e5"),
    ("wx_low", "Weather · lows", "kp", "#eb6834", "#d95926"),
    ("wx_rain", "Weather · rain", "kp", "#1baf7a", "#199e70"),
    ("mention", "Mentions", "k", "#eda100", "#c98500"),
    ("copy", "Copy trading", "p", "#e87ba4", "#d55181"),
    ("crypto", "Crypto", "p", "#008300", "#008300"),
    ("nft", "NFT flips", "o", "#6250d6", "#9085e9"),
    ("manual", "Manual / other", "kp", "#898781", "#898781"),
]


# ---- category rules: logic copied exactly from the handoff README (its example names left out of this public repo) ----
def kalshi_cat(ticker, strategy=""):
    t = (ticker or "").upper()
    if strategy in ("manual", "unattributed"): return "manual"
    if t.startswith("KXHIGH"): return "wx_high"
    if t.startswith("KXLOWT"): return "wx_low"
    if t.startswith("KXRAIN"): return "wx_rain"
    if "MENTION" in t or (strategy or "").startswith("mention"): return "mention"   # earnings-mention series and mention books
    return "manual"                                                               # old hand trades


def pm_cat(book, metric=None):
    if book.startswith("pm_copy"):   return "copy"     # copy-trading books
    if book.startswith("pm_crypto"): return "crypto"   # crypto books
    if book == "unattributed":       return "manual"
    if "rain" in book or metric == "rain":                      return "wx_rain"
    if metric == "low" or "_low" in book or "dawn" in book:     return "wx_low"
    return "wx_high"


def pm_metric(slug):
    s = (slug or "").lower()
    if "lowest-temperature" in s: return "low"
    if "rain" in s or "precipitation" in s: return "rain"
    return "high"


C = lambda x: int(round(x * 100))


def split(day_net, groups):
    """groups {cat: [net, ...]} -> {cat: dict(n, w, l, net_c, gw_c, gl_c)} whose net_c sum to C(day_net) exactly
    (largest remainder on the last cent). Fails loudly if the rows don't add up to the page's day within 1 cent."""
    raw = {c: sum(v) for c, v in groups.items()}
    if abs(sum(raw.values()) - day_net) > 0.011:
        raise SystemExit(f"category rows sum {sum(raw.values()):.4f} != page day {day_net}")
    net = {c: C(x) for c, x in raw.items()}
    diff = C(day_net) - sum(net.values())
    order = sorted(raw, key=lambda c: (raw[c] * 100 - net[c]) * (1 if diff > 0 else -1), reverse=True)
    for i in range(abs(diff)):
        net[order[i % len(order)]] += 1 if diff > 0 else -1
    out = {}
    for c, v in groups.items():
        gw = C(sum(x for x in v if x > 0))
        out[c] = dict(n=len(v), w=sum(x > 0 for x in v), l=sum(x < 0 for x in v), net_c=net[c], gw_c=gw, gl_c=net[c] - gw)
    return out


def row(d, v, c, a):
    return {"d": d, "v": v, "c": c, "n": a["n"], "w": a["w"], "l": a["l"],
            "net": a["net_c"] / 100, "gw": a["gw_c"] / 100, "gl": a["gl_c"] / 100}


def kalshi_rows(H, jsonl, old):
    legs = defaultdict(lambda: defaultdict(list))
    for line in open(jsonl):
        r = json.loads(line)
        if r.get("row_type") == "strategy_leg" and r.get("status") == "settled":
            legs[r["settled_time_ct"][:10]][kalshi_cat(r.get("ticker"), r.get("strategy"))].append(r["net_pnl"])
    keep = defaultdict(list)
    for r in old:
        if r["v"] == "k": keep[r["d"]].append(r)
    out = []
    for day in H["kalshi"]:
        d = day["date"]
        if d in legs:
            out += [row(d, "k", c, a) for c, a in split(day["net"], legs[d]).items()]
        elif keep.get(d):                       # tagged on an earlier run, ledger no longer carries it
            out += keep[d]
        else:                                   # before the settled ledger: jul hand trades
            out.append({"d": d, "v": "k", "c": "manual", "n": day["n"], "w": day["w"], "l": day["l"],
                        "net": day["net"], "gw": day["gw"], "gl": round(day["net"] - day["gw"], 2)})
    return out


def pm_closes():
    import kalshi_ledger
    s3 = kalshi_ledger.client(); B = "pm-private"
    latest = json.loads(s3.get_object(Bucket=B, Key="private/polymarket/psyslo/releases/latest.json")["Body"].read())
    man = json.loads(s3.get_object(Bucket=B, Key=latest["manifest_key"])["Body"].read())
    key = next(o["key"] for o in man["objects"] if o["key"].endswith("closes.jsonl"))
    body = s3.get_object(Bucket=B, Key=key)["Body"].read()
    return latest["release_id"], [json.loads(l) for l in body.splitlines() if l.strip()]


def pm_rows(H, closes):
    g = defaultdict(lambda: defaultdict(list))
    for r in closes:
        d = dt.datetime.fromisoformat(r["accounting_time_utc"].replace("Z", "+00:00")).astimezone(CT).date().isoformat()
        g[d][pm_cat(r.get("strategy_id") or "unattributed", pm_metric(r.get("market_slug")))].append(float(r["net_trading_pnl_usd"]))
    out = []
    for day in H["polymarket"]:
        if day["date"] not in g:
            raise SystemExit(f"polymarket {day['date']} on the page but not in the release")
        out += [row(day["date"], "p", c, a) for c, a in split(day["net"], g[day["date"]]).items()]
    return out


def opensea():
    """-> (H['opensea'] day list, cat rows, info) for fully settled CT days before the pull's CT date."""
    import opensea_ledger as O, opensea_published as P
    led, _ = P.fetch()                     # THE OpenSea ledger, published by Tokay's opensea-ledger job
    pull = led                             # its pulledAt is the CT-day cutoff
    cut = dt.datetime.fromtimestamp(pull["pulledAt"], CT).date().isoformat()
    days, rows = [], []
    for d, a in O.days(led).items():
        if d >= cut:
            continue
        f = lambda c: None if c is None else c / 100
        days.append({"date": d, "n": a["n"], "w": a["w"], "l": a["l"], "net": a["net_c"] / 100, "fees": a["fees_c"] / 100,
                     "gw": a["gw_c"] / 100, "gl": a["gl_c"] / 100,
                     "best": f(a["best_c"]) if a["best_c"] is not None else a["net_c"] / 100,
                     "worst": f(a["worst_c"]) if a["worst_c"] is not None else a["net_c"] / 100})
        rows.append(row(d, "o", "nft", a))
    info = dict(pulled=dt.datetime.fromtimestamp(pull["pulledAt"], CT).strftime("%Y-%m-%d %H:%M CT"),
                lifetime=led["totals"]["net_usd"], through=days[-1]["date"] if days else None,
                sum_days=round(sum(x["net"] for x in days), 2))
    return days, rows, info


def check(H, rows):
    """for each venue and day: categories' cents == the page's day cents."""
    by = defaultdict(int)
    for r in rows: by[(r["v"], r["d"])] += C(r["net"])
    for v, key in (("k", "kalshi"), ("p", "polymarket"), ("o", "opensea")):
        for day in H.get(key, []):
            if by.pop((v, day["date"]), None) != C(day["net"]):
                raise SystemExit(f"{key} {day['date']}: categories != day net")
    if by:
        raise SystemExit(f"category rows without a page day: {sorted(by)[:5]}")


def update(kalshi_jsonl=None):
    import kalshi_ledger
    if kalshi_jsonl is None:
        kalshi_jsonl = "/tmp/kalshi_settled_by_strategy.jsonl"; kalshi_ledger.fetch(kalshi_jsonl)
    H = json.loads(HIST.read_text())
    old = json.loads(CATS.read_text())["rows"] if CATS.exists() else []
    rel, closes = pm_closes()
    rows = kalshi_rows(H, kalshi_jsonl, old) + pm_rows(H, closes)
    try:
        osd, osr, info = opensea()
        H["opensea"] = osd
        print(f"opensea: pull {info['pulled']}, days through {info['through']}, sum {info['sum_days']:+.2f} "
              f"(ledger lifetime incl. the open CT day {info['lifetime']:+.2f})")
    except Exception as e:  # noqa: BLE001 -- keep the last good OpenSea days rather than fail the nightly update
        print(f"WARNING opensea not refreshed ({type(e).__name__}: {str(e)[:160]}); keeping committed days", file=sys.stderr)
        osr = [r for r in old if r["v"] == "o"]
    rows += osr
    check(H, rows)
    order = {k: i for i, (k, *_) in enumerate(CATEGORIES)}
    rows.sort(key=lambda r: (r["d"], "kpo".index(r["v"]), order[r["c"]]))
    if H.get("opensea"):
        o = H["opensea"]
        H["os_coverage"] = (f"opensea from the Tokay NFT ledger (opensea-ledger job, published), {o[0]['date']} → {o[-1]['date']}, "
                            "fully settled CT days, net after OpenSea fees and gas incl. overhead gas")
    HIST.write_text(json.dumps(H, indent=1) + "\n")
    note = ("aggregates only: daily net, settled count, wins/losses, gross win/loss per CT day, venue and kind of trade. "
            "pm release " + rel + ".")
    CATS.write_text('{"note":' + json.dumps(note) + ',"rows":[\n' + ",\n".join(json.dumps(r, separators=(",", ":")) for r in rows) + "\n]}\n")
    tot = defaultdict(float)
    for r in rows: tot[r["v"]] += r["net"]
    print("categories:", len(rows), "rows;", ", ".join(f"{v} {tot[v]:+.2f}" for v in "kpo"))


if __name__ == "__main__":
    if sys.argv[1:2] == ["update"]:
        update()
    else:
        print(__doc__)
