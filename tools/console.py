#!/usr/bin/env python3
"""/pnl/ source since 2026-10-31: the Tokay trading console (read-only). Aggregates only.

Every venue (kalshi, polymarket, hyperliquid, opensea) comes from one place: the console's settled P&L after fees,
by CT day, per venue, and per book category. Replaces kalshi_ledger.py (R2 bucket, gone 10/30), pm_published.py and
opensea_published.py (Tokay MCP, token dead 10/30).

Reads:
  GET  /api/dashboard   (the console dashboard's own read-only JSON): series = settled net by CT day per venue (full
                        history), strategies[].daily + cat = settled net by CT day per book, cat_labels
  POST /mcp overview    tiles.all (all-time settled net incl. today), categories[].all, problems: cross-checks
  POST /mcp activity    money[].settled.by_day (last 7 CT days per venue): cross-check

Token: env TOKAY_MCP_TOKEN_RO only (read-only console token). Console URL: env TOKAY_CONSOLE_URL, else the box file
/home/box/agent-data/shared/tokay/console_url (kept out of this public repo). Neither is ever printed or committed.

Written (aggregates only; never balances, open risk, positions, book or strategy names, params):
  data/pnl_history.json  {kalshi, polymarket, hyperliquid, opensea: [{date, net}], through, coverage, note}
  data/pnl_cats.json     rows {d, v (k/p/h/o), c, net}: per CT day x venue x category; for every venue-day the
                         categories' cents sum to the venue's day net exactly (largest remainder on the last cent)
Only CT days before today (and before the console's build day) are written: today is still settling.

Usage:
  python3 tools/console.py check    fetch + all checks, print a summary, write nothing
  python3 tools/console.py update   fetch + checks, then write data/pnl_history.json + data/pnl_cats.json
then python3 tools/build.py.
"""
import json, os, sys, urllib.request, urllib.error, datetime as dt
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
HIST, CATS = ROOT / "data/pnl_history.json", ROOT / "data/pnl_cats.json"
CT = ZoneInfo("America/Chicago")
URL_FILE = Path("/home/box/agent-data/shared/tokay/console_url")

# console venue -> (page key in pnl_history.json, one-letter code in pnl_cats.json, label)
VENUES = (("kalshi", "kalshi", "k", "kalshi"), ("pm", "polymarket", "p", "polymarket"),
          ("hl", "hyperliquid", "h", "hyperliquid"), ("os", "opensea", "o", "opensea"))
CODE = {v: c for v, _, c, _ in VENUES}

# category key -> light, dark color. Bernard's 14 dashboard categories first (colors unchanged), then the console's
# extra ones. Past the 8 reference hues a category reuses one with a dashed line + ring dot (never a 9th hue).
COLORS = {
    "wx_high": ("#2a78d6", "#3987e5"), "wx_low": ("#eb6834", "#d95926"), "wx_rain": ("#1baf7a", "#199e70"),
    "mention": ("#eda100", "#c98500"), "copy": ("#e87ba4", "#d55181"), "crypto": ("#008300", "#008300"),
    "nft": ("#6250d6", "#9085e9"), "golf": ("#e34948", "#e66767"), "rt": ("#e34948", "#e66767"),
    "cpi": ("#6250d6", "#9085e9"), "youtube": ("#1baf7a", "#199e70"), "basketball": ("#eb6834", "#d95926"),
    "wx_snow": ("#2a78d6", "#3987e5"), "manual": ("#898781", "#898781"),
    # added 2026-10-31 with the console (its categories are per book)
    "commodities": ("#008300", "#008300"), "lip": ("#e87ba4", "#d55181"), "football": ("#eda100", "#c98500"),
    "netflix": ("#eb6834", "#d95926"), "deadlines": ("#2a78d6", "#3987e5"),
}
DASH = {"rt", "cpi", "youtube", "basketball", "wx_snow", "commodities", "lip", "football", "netflix", "deadlines"}
ORDER = list(COLORS)

C = lambda x: int(round(x * 100))


class Console:
    def __init__(self):
        self.tok = os.environ.get("TOKAY_MCP_TOKEN_RO", "").strip()
        if not self.tok:
            raise SystemExit("TOKAY_MCP_TOKEN_RO is not set (the console's read-only token)")
        self.base = (os.environ.get("TOKAY_CONSOLE_URL") or (URL_FILE.read_text() if URL_FILE.exists() else "")).strip().rstrip("/")
        if not self.base:
            raise SystemExit(f"console URL not set (env TOKAY_CONSOLE_URL or {URL_FILE})")

    def _req(self, path, body=None):
        h = {"Authorization": "Bearer " + self.tok, "Accept": "application/json, text/event-stream"}
        if body is not None:
            h["Content-Type"] = "application/json"
        r = urllib.request.Request(self.base + path, data=None if body is None else json.dumps(body).encode(), headers=h)
        try:
            with urllib.request.urlopen(r, timeout=120) as f:
                ct, raw = f.headers.get("Content-Type", ""), f.read().decode()
        except urllib.error.HTTPError as e:     # never echo the request (it carries the token)
            raise SystemExit(f"console {path}: HTTP {e.code}" + (" (token rejected)" if e.code in (401, 403) else ""))
        if "text/event-stream" in ct:           # take the last data: line
            raw = [ln[5:].strip() for ln in raw.splitlines() if ln.startswith("data:")][-1]
        return json.loads(raw)

    def dashboard(self):
        return self._req("/api/dashboard")

    def tool(self, name, args=None):
        d = self._req("/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args or {}}})
        if "error" in d or d.get("result", {}).get("isError"):
            raise SystemExit(f"console tool {name} failed: {str(d.get('error') or d['result'])[:200]}")
        return json.loads(d["result"]["content"][0]["text"])


def split(day_c, groups):
    """groups {cat: raw net} -> {cat: cents} summing to day_c exactly (largest remainder)."""
    net = {c: C(x) for c, x in groups.items()}
    diff = day_c - sum(net.values())
    order = sorted(groups, key=lambda c: (groups[c] * 100 - net[c]) * (1 if diff > 0 else -1), reverse=True)
    for i in range(abs(diff)):
        net[order[i % len(order)]] += 1 if diff > 0 else -1
    return net


def fetch():
    """-> (doc to write, report lines). Raises SystemExit on any failed check."""
    con = Console()
    D, ov, act = con.dashboard(), con.tool("overview"), con.tool("activity", {"hours": 1})
    rep, warn = [], []
    today = dt.datetime.now(CT).date().isoformat()
    built_day = D["built"][:10]
    cut = min(today, built_day)                                  # first CT day NOT written (still settling)
    series = {v: {d: n for d, n in D["series"].get(v, [])} for v, *_ in VENUES}

    # check 1: the dashboard series and the MCP overview tile agree on the all-time total (both incl. today)
    s_all = sum(n for v in series.values() for n in v.values())
    if abs(s_all - ov["tiles"]["all"]) > 0.05:
        raise SystemExit(f"series all-time {s_all:.2f} != overview tiles.all {ov['tiles']['all']:.2f}")
    rep.append(f"check all-time: series {s_all:+.2f} == overview tiles.all {ov['tiles']['all']:+.2f} (incl. today {today})")

    # check 2: MCP activity by_day == dashboard series, per venue, every settled day it carries, to the cent
    n2 = 0
    for m in act["money"]:
        for d, n in m["settled"]["by_day"]:
            if d < cut:
                if C(series[m["venue"]].get(d, 0)) != C(n):
                    raise SystemExit(f"{m['venue']} {d}: activity {n} != series {series[m['venue']].get(d)}")
                n2 += 1
    rep.append(f"check by-day: activity by_day == series on {n2} venue-days")

    # categories: per book daily nets -> venue x day x category, reconciled to the venue day
    raw = defaultdict(lambda: defaultdict(float))
    cat_all = defaultdict(float)
    for s in D["strategies"]:
        for d, n in s.get("daily") or []:
            raw[(s["venue"], d)][s["cat"]] += n
            cat_all[s["cat"]] += n
    # check 3: Σ books per category == overview categories[].all (rounding per book allows a few cents)
    for c in ov["categories"]:
        if abs(cat_all.get(c["cat"], 0) - c["all"]) > 0.25:
            raise SystemExit(f"category {c['cat']}: books {cat_all.get(c['cat'], 0):.2f} != overview {c['all']:.2f}")
    rep.append(f"check categories: books' sums match overview categories[].all on {len(ov['categories'])} categories (±$0.25)")
    if ov.get("problems"):
        warn.append(f"WARNING console lists {len(ov['problems'])} settled market(s) not counted (overview.problems)")
    stl = (ov["tiles"].get("settling") or {})
    if stl.get("oldest") and stl["oldest"] < cut:
        warn.append(f"note: console still has open positions on event days from {stl['oldest']}; days from then on may "
                    "still restate (the next run prints 'restated' lines)")

    labels = D.get("cat_labels", {})
    cats_seen = set()
    out = {"source": "trading console (Tokay), settled P&L after fees by CT day", "through": None}
    rows = []
    worst = 0.0
    for v, key, code, _ in VENUES:
        days = []
        for d in sorted(series[v]):
            if d >= cut:
                continue
            n = series[v][d]
            days.append({"date": d, "net": round(n, 2)})
            g = raw.get((v, d)) or {"manual": n}
            worst = max(worst, abs(sum(g.values()) - n))
            # check 4: books' day sum within 10 cents of the venue day before the last-cent split
            if abs(sum(g.values()) - n) > 0.10:
                raise SystemExit(f"{v} {d}: books sum {sum(g.values()):.2f} != venue day {n:.2f}")
            for c, cents in split(C(n), {c: x for c, x in g.items()}).items():
                if cents or abs(g.get(c, 0)) > 0:
                    rows.append({"d": d, "v": code, "c": c, "net": cents / 100}); cats_seen.add(c)
        out[key] = days
    rep.append(f"check reconcile: books vs venue day off by at most ${worst:.2f} before the last-cent split")

    # check 5: categories == venue days to the cent, every venue x day
    by = defaultdict(int)
    for r in rows: by[(r["v"], r["d"])] += C(r["net"])
    for v, key, code, _ in VENUES:
        for d in out[key]:
            if by.pop((code, d["date"]), 0) != C(d["net"]):
                raise SystemExit(f"{key} {d['date']}: categories != day net")
    if any(by.values()):
        raise SystemExit("category rows without a venue day")
    last = max(d["date"] for _, key, _, _ in VENUES for d in out[key])
    out["through"] = last
    fmt = lambda d: dt.date.fromisoformat(d).strftime("%b %-d").lower()
    out["coverage"] = ", ".join(f"{lab} {fmt(out[key][0]['date'])} → {fmt(out[key][-1]['date'])}"
                                for _, key, _, lab in VENUES if out[key])
    out["note"] = ("aggregates only: settled net after fees per CT day and venue, from the trading console; "
                   f"restated 2026-10-31; days before {cut} only (today still settling).")
    cmeta = []
    for c in sorted(cats_seen | set(labels), key=lambda c: ORDER.index(c) if c in ORDER else 99):
        vs = sorted({r["v"] for r in rows if r["c"] == c}, key="kpho".index)
        cmeta.append({"k": c, "label": labels.get(c, c), "v": "".join(vs)})
    unknown = [c["k"] for c in cmeta if c["k"] not in COLORS]
    if unknown:
        warn.append(f"WARNING new console categories with no color yet (gray dashed): {unknown}")
    tot = {key: round(sum(d["net"] for d in out[key]), 2) for _, key, _, _ in VENUES}
    rep.append("through " + last + ": " + ", ".join(f"{k} {t:+.2f}" for k, t in tot.items())
               + f"; combined {sum(tot.values()):+.2f}")
    rep.append(f"{last}: " + ", ".join(f"{key} {next((d['net'] for d in out[key] if d['date'] == last), 0):+.2f}"
                                      for _, key, _, _ in VENUES))
    return out, rows, cmeta, rep + warn


def restated(out):
    """lines for days already on the page whose net changed (the console restates late settles)."""
    if not HIST.exists():
        return []
    H = json.loads(HIST.read_text()); lines = []
    for _, key, _, _ in VENUES:
        old = {d["date"]: d["net"] for d in H.get(key, [])}
        for d in out[key]:
            if d["date"] in old and C(old[d["date"]]) != C(d["net"]):
                lines.append(f"restated {key} {d['date']}: {old[d['date']]:+.2f} -> {d['net']:+.2f}")
        new = {d["date"] for d in out[key]}
        lines += [f"dropped {key} {d}: {n:+.2f} (the console has no settled net that day)" for d, n in sorted(old.items()) if d not in new]
    return lines


def update(write=True):
    out, rows, cmeta, rep = fetch()
    for ln in rep + restated(out): print(ln)
    if not write:
        return out
    order = {c["k"]: i for i, c in enumerate(cmeta)}
    rows.sort(key=lambda r: (r["d"], "kpho".index(r["v"]), order[r["c"]]))
    HIST.write_text(json.dumps(out, indent=1) + "\n")
    CATS.write_text('{"note":' + json.dumps("aggregates only: settled net per CT day, venue (k kalshi, p polymarket, "
                    "h hyperliquid, o opensea) and kind of trade; categories are per book, from the trading console.")
                    + ',"cats":' + json.dumps(cmeta, separators=(",", ":")) + ',"rows":[\n'
                    + ",\n".join(json.dumps(r, separators=(",", ":")) for r in rows) + "\n]}\n")
    print(f"wrote data/pnl_history.json + data/pnl_cats.json ({len(rows)} category rows) through {out['through']}")
    return out


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["update"]: update()
    elif cmd == ["check"]: update(write=False)
    else: print(__doc__)
