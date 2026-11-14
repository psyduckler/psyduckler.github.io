#!/usr/bin/env python3
"""/pnl/ refresh from saved outputs of the console's `pnl` tool (no token needed).

The scheduled run has no TOKAY_MCP_TOKEN_RO, but it can call the "Tokay PnL console" MCP connector's `pnl` tool.
This file turns those 24 saved tool results (4 windows x 6 venues) into the page's data files, with every check
the page relies on. It never talks to the console itself and never sees a token or the console URL.

Usage (from the repo root):
  python3 tools/console_pnl.py save  DIR FILE...   pull the JSON out of each saved connector result
                                                   (write_to_file output or a raw paste) into DIR/pnl_<window>_<venue>.json
  python3 tools/console_pnl.py check DIR           all checks + summary + restated/dropped lines, writes nothing
  python3 tools/console_pnl.py update DIR          same, then writes data/pnl_public.json, data/pnl_history.json,
                                                   data/pnl_cats.json (then run: python3 tools/build.py)
  add --any-day to check/update to accept a DIR whose `today` is not today's CT date (re-running an old snapshot).

Published (aggregates only, exactly the `pnl` tool's fields): per window x venue net, days, day_wins, winrate,
avg_day, best/worst day, sharpe, series [CT date, day net, running net], and the same per category (label, venues).
Today's CT day stays in, labeled "today, not final" on the page (the page's convention since Nov 11, 2026).
"""
import json, sys, datetime as dt
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import console as SRC   # colors / category order / VENUES only; nothing here calls the console

PUB_F, HIST, CATS = ROOT / "data/pnl_public.json", ROOT / "data/pnl_history.json", ROOT / "data/pnl_cats.json"
CT = ZoneInfo("America/Chicago")
WINDOWS = ("all", "90d", "30d", "7d")
VEN = ("kalshi", "pm", "hl", "os", "eq")
VENUES = ("all",) + VEN
KEY = {v: key for v, key, _c, _l in SRC.VENUES}       # pm -> polymarket ...
CODE = {v: c for v, _k, c, _l in SRC.VENUES}          # pm -> p ...
KEEP_TOP = ("window", "venue", "today", "from", "to", "combined", "categories")
KEEP_COMB = ("net", "days", "day_wins", "winrate", "avg_day", "best_day", "worst_day", "sharpe", "series")
KEEP_CAT = ("cat", "label", "venues") + KEEP_COMB
FORBIDDEN = ("tokay.io", "tokay.app", "bearer", "console_url", "api_key", "secret", "wallet", "ticker", "0x",
             "balance\"", "position\"", "book\"", "strategy", "token")
C = lambda x: int(round(x * 100))


def die(msg):
    raise SystemExit("REFUSED: " + msg)


def extract(text):
    """first JSON object in a connector result that looks like a pnl response."""
    dec = json.JSONDecoder()
    i = text.find("{")
    while i >= 0:
        try:
            obj, _ = dec.raw_decode(text, i)
            if isinstance(obj, dict) and {"window", "venue", "combined"} <= set(obj):
                return obj
        except ValueError:
            pass
        i = text.find("{", i + 1)
    return None


def save(d, files):
    d = Path(d); d.mkdir(parents=True, exist_ok=True)
    got = {}
    for f in files:
        obj = extract(Path(f).read_text())
        if obj is None:
            die(f"{f}: no pnl response JSON found")
        k = f"{obj['window']}:{obj['venue']}"
        if k in got:
            die(f"{f}: duplicate {k} (also in {got[k]})")
        got[k] = f
        (d / f"pnl_{obj['window']}_{obj['venue']}.json").write_text(json.dumps(obj, indent=1) + "\n")
    missing = [f"{w}:{v}" for w in WINDOWS for v in VENUES if f"{w}:{v}" not in got]
    print(f"saved {len(got)} responses to {d}" + (f"; MISSING {missing}" if missing else " (all 24)"))
    if missing:
        raise SystemExit(1)


def load(d):
    R = {}
    for w in WINDOWS:
        for v in VENUES:
            p = Path(d) / f"pnl_{w}_{v}.json"
            if not p.exists():
                die(f"missing {p.name} (need all 24: windows {WINDOWS} x venues {VENUES})")
            r = json.loads(p.read_text())
            if r.get("window") != w or r.get("venue") != v:
                die(f"{p.name} holds {r.get('window')}:{r.get('venue')}")
            R[f"{w}:{v}"] = r
    return R


def checks(R, any_day):
    rep = []
    todays = {r["today"] for r in R.values()}
    if len(todays) != 1:
        die(f"responses disagree on today: {sorted(todays)} (fetch all 24 in one sitting)")
    today = todays.pop()
    ct_today = dt.datetime.now(CT).date().isoformat()
    if today != ct_today and not any_day:
        die(f"snapshot today {today} != CT today {ct_today} (refetch, or pass --any-day for an old snapshot)")
    for k, r in R.items():
        blob = json.dumps(r).lower()
        for bad in FORBIDDEN:
            if bad in blob:
                die(f"{k} contains '{bad}': not a pure pnl aggregate, do not publish")
        cb, s = r["combined"], r["combined"].get("series") or []
        if not s:
            if cb.get("net") or cb.get("days"):
                die(f"{k}: totals without a series")
            continue
        if len(s) != cb["days"]:
            die(f"{k}: {len(s)} series points != days {cb['days']}")
        if s[-1][0] != r["to"] or s[0][0] < (r["from"] or ""):
            die(f"{k}: series {s[0][0]}..{s[-1][0]} outside from/to {r['from']}..{r['to']}")
        prev, run = 0, 0
        for d, n, rr in s:                         # step check: running moves by the day net (±1¢ rounding)
            run += C(n)
            if abs(C(rr) - prev - C(n)) > 1:
                die(f"{k} {d}: running {rr} moved {(C(rr) - prev) / 100:.2f}, day net {n}")
            prev = C(rr)
        if abs(run - C(s[-1][2])) > 50:            # rounded day nets vs the unrounded running total
            die(f"{k}: Σ rounded day nets {run / 100:.2f} drifts > $0.50 from running {s[-1][2]}")
        if abs(C(s[-1][2]) - C(cb["net"])) > 1:
            die(f"{k}: last running {s[-1][2]} != net {cb['net']}")
        cs = sum(C(c["net"]) for c in r["categories"])
        if abs(cs - C(cb["net"])) > 5:
            die(f"{k}: categories sum {cs / 100:.2f} != net {cb['net']:.2f}")
        for c in r["categories"]:
            cser = c.get("series") or []
            if c.get("days") and len(cser) != c["days"]:
                die(f"{k} {c['label']}: series length != days")
    rep.append(f"check shape: 24 responses, today {today}, series length == days, running steps == day nets (±1¢), last running == net")
    rep.append("check categories: Σ category nets == combined net (±$0.05) in all 24 views")
    for w in WINDOWS:
        parts = sum(C(R[f"{w}:{v}"]["combined"]["net"]) for v in VEN)
        if abs(parts - C(R[f"{w}:all"]["combined"]["net"])) > 5:
            die(f"{w}: Σ venues {parts / 100:.2f} != all {R[f'{w}:all']['combined']['net']:.2f}")
        byd = defaultdict(int)
        for v in VEN:
            for d, n, _ in R[f"{w}:{v}"]["combined"]["series"] or []:
                byd[d] += C(n)
        alld = {d: C(n) for d, n, _ in R[f"{w}:all"]["combined"]["series"] or []}
        if set(byd) != set(alld) or any(abs(byd[d] - alld[d]) > 2 for d in alld):
            die(f"{w}: per-day Σ venues != combined series")
    rep.append("check venues: Σ venue nets == combined net (±$0.05) and Σ venue day nets == combined day net (±$0.02), every window")
    for v in VENUES:
        full = {d: C(n) for d, n, _ in R[f"all:{v}"]["combined"]["series"] or []}
        for w in WINDOWS[1:]:
            for d, n, _ in R[f"{w}:{v}"]["combined"]["series"] or []:
                if full.get(d) != C(n):
                    die(f"{w}:{v} {d}: day net {n} != all-time window's {full.get(d)}")
    rep.append("check windows: 90d/30d/7d day nets == the all-time window's, to the cent, every venue")
    # categories per venue add up to the combined view's categories
    tot = defaultdict(int)
    for v in VEN:
        for c in R[f"all:{v}"]["categories"]:
            tot[c["cat"]] += C(c["net"])
    for c in R["all:all"]["categories"]:
        if abs(tot.pop(c["cat"], 0) - C(c["net"])) > 5:
            die(f"category {c['cat']}: Σ venues != combined")
    if any(abs(x) > 5 for x in tot.values()):
        die(f"categories on a venue but not in combined: {[k for k, x in tot.items() if abs(x) > 5]}")
    rep.append("check category venues: Σ per-venue category nets == combined category nets (±$0.05)")
    return today, rep


def split(day_c, groups):
    net = {c: C(x) for c, x in groups.items()}
    diff = day_c - sum(net.values())
    order = sorted(groups, key=lambda c: (groups[c] * 100 - net[c]) * (1 if diff > 0 else -1), reverse=True)
    for i in range(abs(diff)):
        net[order[i % len(order)]] += 1 if diff > 0 else -1
    return net


def build(R, today):
    fmt = lambda d: dt.date.fromisoformat(d).strftime("%b %-d").lower()
    hist = {"source": "settled P&L after fees by CT day", "through": None}
    for v in VEN:
        hist[KEY[v]] = [{"date": d, "net": round(n, 2)} for d, n, _ in R[f"all:{v}"]["combined"]["series"] or []]
    hist["through"] = max(x["date"] for v in VEN for x in hist[KEY[v]])
    hist["coverage"] = ", ".join(f"{KEY[v]} {fmt(hist[KEY[v]][0]['date'])} → {fmt(hist[KEY[v]][-1]['date'])}"
                                 for v in VEN if hist[KEY[v]])
    hist["note"] = (f"aggregates only: settled net after fees per CT day and venue. the series includes {today}, which is "
                    "today (central time) and not final. headline metrics on /pnl/ are the precomputed values in "
                    "data/pnl_public.json, not a fresh sum of these day nets.")
    rows, labels, worst = [], {}, 0.0
    for v in VEN:
        per = defaultdict(dict)
        for c in R[f"all:{v}"]["categories"]:
            labels[c["cat"]] = c["label"]
            for d, n, _ in c.get("series") or []:
                per[d][c["cat"]] = per[d].get(c["cat"], 0) + n
        for x in hist[KEY[v]]:
            g = per.get(x["date"]) or {"manual": x["net"]}
            worst = max(worst, abs(sum(g.values()) - x["net"]))
            if abs(sum(g.values()) - x["net"]) > 0.10:
                die(f"{v} {x['date']}: categories {sum(g.values()):.2f} != day {x['net']:.2f}")
            for c, cents in split(C(x["net"]), g).items():
                if cents or g.get(c):
                    rows.append({"d": x["date"], "v": CODE[v], "c": c, "net": cents / 100})
        extra = set(per) - {x["date"] for x in hist[KEY[v]]}
        if extra:
            die(f"{v}: category days {sorted(extra)} with no venue day")
    for c in R["all:all"]["categories"]:
        labels[c["cat"]] = c["label"]
    # keep the page's existing category list and order (stable colors/rows); new console categories go last
    prev = json.loads(CATS.read_text())["cats"] if CATS.exists() else []
    for c in prev:
        labels.setdefault(c["k"], c["label"])
    order = [c["k"] for c in prev] + [c for c in SRC.ORDER if c not in {x["k"] for x in prev}]
    cmeta = []
    for k in sorted(labels, key=lambda c: (order.index(c) if c in order else len(order), c)):
        vs = sorted({r["v"] for r in rows if r["c"] == k}, key="kphoe".index)
        cmeta.append({"k": k, "label": labels[k], "v": "".join(vs)})
    oi = {c["k"]: i for i, c in enumerate(cmeta)}
    rows.sort(key=lambda r: (r["d"], "kphoe".index(r["v"]), oi[r["c"]]))
    pub = {"source_today": today,
           "fetched_at_ct": dt.datetime.now(CT).strftime("%Y-%m-%d %H:%M:%S %Z"),
           "basis": "settled legs only, net after fees, CT days; open positions and balances are not counted",
           "today_label": "today, not final", "windows": list(WINDOWS), "venues": list(VENUES), "responses": {}}
    for w in WINDOWS:
        for v in VENUES:
            r = R[f"{w}:{v}"]
            o = {k: r.get(k) for k in KEEP_TOP}
            o["combined"] = {k: r["combined"].get(k) for k in KEEP_COMB}
            o["categories"] = [{k: c.get(k) for k in KEEP_CAT} for c in r["categories"]]
            pub["responses"][f"{w}:{v}"] = o
    unknown = [c["k"] for c in cmeta if c["k"] not in SRC.COLORS]
    return pub, hist, rows, cmeta, worst, unknown


def restated(hist, today):
    if not HIST.exists():
        return [], []
    H = json.loads(HIST.read_text()); old_today = H.get("through")
    lines, flagged = [], []
    for v in VEN:
        key = KEY[v]
        old = {d["date"]: d["net"] for d in H.get(key, [])}
        new = {d["date"]: d["net"] for d in hist[key]}
        for d in sorted(set(old) | set(new)):
            if d in old and d in new and C(old[d]) == C(new[d]):
                continue
            if d not in old:
                continue                                    # a new day, not a restatement
            age = (dt.date.fromisoformat(today) - dt.date.fromisoformat(d)).days
            if d not in new:
                ln, delta = f"dropped {key} {d}: {old[d]:+.2f} (no settled net now)", abs(old[d])
            else:
                delta = new[d] - old[d]
                ln = f"restated {key} {d}: {old[d]:+.2f} -> {new[d]:+.2f} (Δ {delta:+.2f})"
            if d == old_today:
                ln += " [was today, not final, on the last publish]"
            lines.append(ln)
            if age > 7 or abs(delta) > 50:
                flagged.append(ln + f" [age {age}d]")
    return lines, flagged


def run(d, write, any_day):
    R = load(d)
    today, rep = checks(R, any_day)
    pub, hist, rows, cmeta, worst, unknown = build(R, today)
    rep.append(f"check reconcile: per venue-day category sums within ${worst:.2f} of the day net before the last-cent split")
    for ln in rep: print(ln)
    a = lambda w, v: R[f"{w}:{v}"]["combined"]["net"]
    print(f"today (CT, not final): {today}")
    print("all-time: " + ", ".join(f"{v} {a('all', v):+.2f}" for v in VEN) + f"; combined {a('all', 'all'):+.2f}")
    y = (dt.date.fromisoformat(today) - dt.timedelta(days=1)).isoformat()
    for dd in (y, today):
        vals = {v: next((n for x, n, _ in R[f"all:{v}"]["combined"]["series"] or [] if x == dd), 0) for v in VENUES}
        print(f"{dd}{' (today)' if dd == today else ''}: " + ", ".join(f"{v} {vals[v]:+.2f}" for v in VEN) + f"; combined {vals['all']:+.2f}")
    lines, flagged = restated(hist, today)
    for ln in lines: print(ln)
    print(f"FLAG (over 7 days old or over $50): {len(flagged)}")
    for ln in flagged: print("  " + ln)
    if unknown:
        print(f"WARNING new categories with no color yet (gray dashed): {unknown}")
    msg = (f"pnl: through {dt.date.fromisoformat(y).strftime('%b %-d')} from console: "
           + ", ".join(f"{v} {a('all', v):+.2f}" for v in VEN if R[f'all:{v}']['combined']['days'])
           + f"; combined all-time {a('all', 'all'):+.2f}"
           + (f"; restated {len({l.split()[2] for l in lines if l.startswith('restated')})} days" if lines else ""))
    print("commit message: " + msg)
    if not write:
        return
    PUB_F.write_text(json.dumps(pub, indent=1) + "\n")
    HIST.write_text(json.dumps(hist, indent=1) + "\n")
    CATS.write_text('{"note":' + json.dumps("aggregates only: settled net per CT day, venue (k kalshi, p polymarket, "
                    "h hyperliquid, o opensea, e robinhood) and kind of trade. day nets are the published series points. "
                    f"includes {today}, today (central time), which is not final.")
                    + ',"cats":' + json.dumps(cmeta, separators=(",", ":")) + ',"rows":[\n'
                    + ",\n".join(json.dumps(r, separators=(",", ":")) for r in rows) + "\n]}\n")
    print(f"wrote data/pnl_public.json, data/pnl_history.json, data/pnl_cats.json ({len(rows)} category rows); now run tools/build.py")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if x != "--any-day"]; anyd = "--any-day" in sys.argv
    if len(a) >= 3 and a[0] == "save": save(a[1], a[2:])
    elif len(a) == 2 and a[0] in ("check", "update"): run(a[1], a[0] == "update", anyd)
    else: print(__doc__)
