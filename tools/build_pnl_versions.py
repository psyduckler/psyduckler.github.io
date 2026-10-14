#!/usr/bin/env python3
"""Build 5 PnL page prototypes at /pnl/v1..v5 + /pnl/versions/ from data/pnl_history.json.
noindex, not linked from nav. Aggregates only. Run: python3 tools/build_pnl_versions.py"""
import json, statistics as st, datetime as dt, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build, theme
ROOT = build.ROOT
H = json.loads((ROOT / "data/pnl_history.json").read_text())
K, P = H["kalshi"], H["polymarket"]
money = build.money
cls = lambda v: "pos" if v >= 0 else "neg"

def metrics(days, tr):
    nets = [d["net"] for d in days]; c = pk = dd = 0; curve = []
    for n in nets:
        c += n; pk = max(pk, c); dd = min(dd, c - pk); curve.append(c)
    nw, sw, nl, sl = tr["nw"], tr["sw"], tr["nl"], tr["sl"]
    fees = sum(d["fees"] for d in days); gross = sum(nets) + fees
    sd = st.pstdev(nets) or 1
    return dict(days=len(days), net=sum(nets), trades=nw + nl, wr=nw / (nw + nl) * 100,
                pf=sw / -sl, best=max(nets), worst=min(nets), dd=dd,
                sharpe=st.mean(nets) / sd * 365 ** .5, fees=fees, gross=gross,
                feepct=(fees / gross * 100) if gross > 0 else None, avgw=sw / nw, avgl=sl / nl,
                exp=(sw + sl) / (nw + nl), green=sum(n > 0 for n in nets), curve=curve)
MK, MP = metrics(K, H["ksum"]), metrics(P, H["psum"])
COMB = {k: H["ksum"][k] + H["psum"][k] for k in ("nw", "sw", "nl", "sl", "clipped")}
COMB["hist"] = [a + b for a, b in zip(H["ksum"]["hist"], H["psum"]["hist"])]
ALL = {}
for src in (K, P):
    for d in src:
        a = ALL.setdefault(d["date"], dict(date=d["date"], net=0, fees=0, n=0, w=0, l=0))
        for k in ("net", "fees", "n", "w", "l"): a[k] += d[k]
ALLD = [ALL[k] for k in sorted(ALL)]
MA = metrics(ALLD, COMB)
f = lambda d: build.fmt_date(d)

# ---------- svg helpers ----------
def scale(vals, lo, hi):
    mn, mx = min(vals + [0]), max(vals + [0]); r = (mx - mn) or 1
    return lambda v: hi - (v - mn) / r * (hi - lo)

def line(series, w=640, h=200, colors=("var(--accent)",), labels=None, zero=True):
    allv = [v for s in series for v in s]; y = scale(allv, 10, h - 10); out = []
    n = max(len(s) for s in series)
    for s, col in zip(series, colors):
        pts = " ".join(f"{i * (w / (max(n - 1, 1))):.1f},{y(v):.1f}" for i, v in enumerate(s))
        out.append(f'<polyline fill="none" stroke="{col}" stroke-width="2" points="{pts}"/>')
    z = f'<line x1="0" x2="{w}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="var(--border)" stroke-dasharray="3 3"/>' if zero else ""
    return f'<svg viewBox="0 0 {w} {h}" width="100%" role="img">{z}{"".join(out)}</svg>'

def area(vals, w=640, h=160, col="var(--neg)"):
    y = scale(vals, 6, h - 6); n = len(vals)
    pts = " ".join(f"{i * w / max(n - 1, 1):.1f},{y(v):.1f}" for i, v in enumerate(vals))
    return f'<svg viewBox="0 0 {w} {h}" width="100%"><polygon fill="{col}" fill-opacity=".35" stroke="{col}" points="0,{y(0):.1f} {pts} {w},{y(0):.1f}"/></svg>'

def bars(vals, w=640, h=200, colors=None, overlay=None):
    y = scale(vals, 10, h - 10); bw = w / len(vals); out = []
    for i, v in enumerate(vals):
        col = colors[i] if colors else ("var(--pos)" if v >= 0 else "var(--neg)")
        out.append(f'<rect x="{i * bw + 1:.1f}" width="{max(bw - 2, 1):.1f}" y="{min(y(v), y(0)):.1f}" height="{abs(y(v) - y(0)):.1f}" fill="{col}"><title>{money(v)}</title></rect>')
    if overlay:  # values 0..100 plotted on own axis
        pts = " ".join(f"{i * bw + bw / 2:.1f},{h - 10 - v / 100 * (h - 20):.1f}" for i, v in enumerate(overlay))
        out.append(f'<polyline fill="none" stroke="var(--accent)" stroke-width="2" points="{pts}"/>')
    return f'<svg viewBox="0 0 {w} {h}" width="100%">{"".join(out)}</svg>'

def stacked(dates, a, b, w=640, h=200):
    tops = [max(x, 0) + max(y_, 0) for x, y_ in zip(a, b)]; bots = [min(x, 0) + min(y_, 0) for x, y_ in zip(a, b)]
    y = scale(tops + bots, 10, h - 10); bw = w / len(dates); out = []
    for i in range(len(dates)):
        up = dn = 0
        for v, col in ((a[i], "var(--accent)"), (b[i], "var(--link-2,#6aa7ff)")):
            if v >= 0: y0, y1 = up, up + v; up = y1
            else: y0, y1 = dn, dn + v; dn = y1
            out.append(f'<rect x="{i * bw + 1:.1f}" width="{max(bw - 2, 1):.1f}" y="{min(y(y0), y(y1)):.1f}" height="{abs(y(y1) - y(y0)):.1f}" fill="{col}"/>')
    return f'<svg viewBox="0 0 {w} {h}" width="100%"><line x1="0" x2="{w}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="var(--border)"/>{"".join(out)}</svg>'

def heatmap(days):
    by = {d["date"]: d["net"] for d in days}; d0 = dt.date.fromisoformat(days[0]["date"]); d1 = dt.date.fromisoformat(days[-1]["date"])
    d0 -= dt.timedelta(days=d0.weekday()); cs = 14; out = []; mx = max(abs(v) for v in by.values())
    i = 0; d = d0
    while d <= d1:
        v = by.get(d.isoformat()); x = (i // 7) * (cs + 2); yy = d.weekday() * (cs + 2)
        if v is None: fill, op = "var(--border-soft)", 1
        else: fill, op = ("var(--pos)" if v >= 0 else "var(--neg)"), .25 + .75 * abs(v) / mx
        out.append(f'<rect x="{x}" y="{yy}" width="{cs}" height="{cs}" fill="{fill}" fill-opacity="{op:.2f}"><title>{d} {money(v) if v is not None else "no settles"}</title></rect>')
        d += dt.timedelta(days=1); i += 1
    return f'<svg viewBox="0 0 {(i // 7 + 1) * (cs + 2)} {7 * (cs + 2)}" width="100%">{"".join(out)}</svg>'

def hist(b, clipped, lo=-100, hi=100, w=640, h=180):
    nb = len(b)
    mx = max(b); bw = w / nb
    r = "".join(f'<rect x="{i * bw + .5:.1f}" width="{bw - 1:.1f}" y="{h - 10 - c / mx * (h - 20):.1f}" height="{c / mx * (h - 20):.1f}" fill="{"var(--pos)" if lo + (i + .5) * (hi - lo) / nb > 0 else "var(--neg)"}"><title>{c}</title></rect>' for i, c in enumerate(b))
    return f'<svg viewBox="0 0 {w} {h}" width="100%">{r}</svg>', clipped

EXTRA = """
.strip{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:.5rem;margin:1rem 0}
.stat{background:var(--card);border:1px solid var(--border);padding:.7rem}
.stat b{display:block;font-size:1.15rem;font-weight:400}.stat span{font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.1em}
.big{font-size:3.2rem;line-height:1.1;margin:.5rem 0}.huge{font-size:4.5rem;line-height:1}
.legend{font-size:.75rem;color:var(--muted)}.sw{display:inline-block;width:.8em;height:.8em;margin:0 .3em 0 .8em;vertical-align:middle}
.proto{font-size:.75rem;color:var(--muted);border:1px dashed var(--border);padding:.4rem .6rem;margin-bottom:1.5rem}
"""
def stat(label, val, c=""): return f'<div class="stat"><b class="{c}">{val}</b><span>{label}</span></div>'
SRC = (f'<p class="small">sources: kalshi settled ledger, {f(K[0]["date"])} → {f(K[-1]["date"])}; polymarket settled release from R2, '
       f'{f(P[0]["date"])} → {f(P[-1]["date"])}. net after fees. aggregates only. today\'s partial days left out.</p>')

def page(n, title, tagline, body):
    path = f"/pnl/v{n}/" if n else "/pnl/versions/"
    out = f"pnl/v{n}/index.html" if n else "pnl/versions/index.html"
    # reuse the shared layout, then mark noindex
    build.CSS_EXTRA = EXTRA
    old = build.CSS; build.CSS = old + EXTRA
    build.page(path, out, title, "PnL page prototype. Not final.", title.split(" ·")[0], tagline,
               '<div class="proto">prototype ' + (f"v{n}" if n else "index") + ' · not linked · <a href="/pnl/versions/">all versions</a></div>' + body + SRC, f(K[-1]["date"]))
    build.CSS = old
    p = ROOT / out; s = p.read_text().replace("<head>", '<head>\n  <meta name="robots" content="noindex, nofollow">', 1); p.write_text(s)

pc = lambda v: f"{v:.1f}%"

def main():
    # v1: equity curve + stat strip
    page(1, "pnl v1 · the curve", "one line, all the sins", f"""<div class="section"><h2>combined equity</h2>
    <div class="strip">{stat("total net", money(MA["net"]), cls(MA["net"]))}{stat("win rate", pc(MA["wr"]))}{stat("profit factor", f'{MA["pf"]:.2f}')}{stat("best day", money(MA["best"]), "pos")}{stat("worst day", money(MA["worst"]), "neg")}{stat("max drawdown", money(MA["dd"]), "neg")}{stat("sharpe-ish", f'{MA["sharpe"]:.2f}')}{stat("settled", f'{MA["trades"]:,}')}</div>
    {line([MA["curve"]])}
    <p>{MA["days"]} trading days. up {money(MA["net"])}. the drawdown was {money(MA["dd"])} deep, so the ride was worse than the destination.</p></div>""")

    # v2: daily bars + heatmap
    page(2, "pnl v2 · red/green", "every day gets a color, no hiding", f"""<div class="section"><h2>daily net · both teams</h2>{bars([d["net"] for d in ALLD])}
    <p>{sum(d["net"] > 0 for d in ALLD)} green days, {sum(d["net"] <= 0 for d in ALLD)} red. biggest green {money(MA["best"])}, biggest red {money(MA["worst"])}.</p></div>
    <div class="section"><h2>calendar</h2>{heatmap(ALLD)}<p class="small">brighter = bigger. grey = nothing settled. mon at top.</p></div>""")

    # v3: split
    dates = sorted(ALL); kby = {d["date"]: d["net"] for d in K}; pby = {d["date"]: d["net"] for d in P}
    recent = [d for d in dates if d >= P[0]["date"]]
    kc = pcum = 0; kcur, pcur, ccur = [], [], []
    for d in recent:
        kc += kby.get(d, 0); pcum += pby.get(d, 0); kcur.append(kc); pcur.append(pcum); ccur.append(kc + pcum)
    page(3, "pnl v3 · two teams", "kalshi vs polymarket. one is carrying.", f"""<div class="section"><h2>side by side</h2>
    <table><tr><th></th><th>kalshi</th><th>polymarket</th><th>combined</th></tr>
    <tr><td>days</td><td>{MK["days"]}</td><td>{MP["days"]}</td><td>{MA["days"]}</td></tr>
    <tr><td>settled</td><td>{MK["trades"]:,}</td><td>{MP["trades"]:,}</td><td>{MA["trades"]:,}</td></tr>
    <tr><td>net</td><td class="{cls(MK["net"])}">{money(MK["net"])}</td><td class="{cls(MP["net"])}">{money(MP["net"])}</td><td class="{cls(MA["net"])}">{money(MA["net"])}</td></tr>
    <tr><td>win rate</td><td>{pc(MK["wr"])}</td><td>{pc(MP["wr"])}</td><td>{pc(MA["wr"])}</td></tr>
    <tr><td>fees</td><td>${MK["fees"]:,.2f}</td><td>${MP["fees"]:,.2f}</td><td>${MA["fees"]:,.2f}</td></tr></table></div>
    <div class="section"><h2>overlap window · daily stack</h2>{stacked(recent, [kby.get(d, 0) for d in recent], [pby.get(d, 0) for d in recent])}
    <p class="legend"><span class="sw" style="background:var(--accent)"></span>kalshi<span class="sw" style="background:#6aa7ff"></span>polymarket</p></div>
    <div class="section"><h2>overlap window · cumulative</h2>{line([kcur, pcur, ccur], colors=("var(--accent)", "#6aa7ff", "var(--fg)"))}
    <p class="legend"><span class="sw" style="background:var(--accent)"></span>kalshi<span class="sw" style="background:#6aa7ff"></span>polymarket<span class="sw" style="background:var(--fg)"></span>combined</p>
    <p>since {f(recent[0])}: kalshi {money(kcur[-1])}, polymarket {money(pcur[-1])}. polymarket is the new kid and it's paying tuition.</p></div>""")

    # v4: brutal honesty
    wr = [d["w"] / d["n"] * 100 for d in ALLD]  # per-day win rate
    page(4, "pnl v4 · brutal honesty", "the numbers don't care about your feelings", f"""<div class="section"><h2>the headline</h2>
    <div class="huge {cls(MA["net"])}">{money(MA["net"])}</div><p>{MA["days"]} days. {MA["trades"]:,} settled bets. that's it. that's the whole pile.</p></div>
    <div class="section"><h2>the paradox</h2><div class="big">{pc(MA["wr"])} wins</div>
    <p>we win most bets and still barely move. avg win {money(MA["avgw"])}, avg loss {money(MA["avgl"])}. right twice, wrong once, net: a shrug.</p>
    {bars([d["net"] for d in ALLD], overlay=wr)}<p class="legend">bars = daily net · gold line = daily win rate (0–100%)</p></div>
    <div class="section"><h2>the toll</h2><div class="big">${MA["fees"]:,.0f}</div>
    <p>paid in fees. that's {pc(MA["fees"] / (MA["net"] + MA["fees"]) * 100)} of gross profit going to the house before we see a cent.</p></div>
    <div class="section"><h2>the pain</h2>{area([c - max(MA["curve"][:i + 1] + [0]) for i, c in enumerate(MA["curve"])])}
    <p>max drawdown {money(MA["dd"])}. underwater chart: every dip is a day someone wanted to turn it off.</p></div>""")

    # v5: distribution
    hsvg, clip = hist(COMB["hist"], COMB["clipped"])
    roll = [sum(d["net"] for d in ALLD[max(0, i - 6):i + 1]) for i in range(len(ALLD))]
    page(5, "pnl v5 · the distribution", "averages lie, shapes don't", f"""<div class="section"><h2>every settled bet</h2>{hsvg}
    <p class="small">{MA["trades"]:,} bets, binned -$100 → +$100. {clip} outliers past the edges, clamped in.</p>
    <div class="strip">{stat("avg win", money(MA["avgw"]), "pos")}{stat("avg loss", money(MA["avgl"]), "neg")}{stat("expectancy / bet", money(MA["exp"]), cls(MA["exp"]))}{stat("profit factor", f'{MA["pf"]:.2f}')}</div>
    <p>tall green hump of small wins, long red tail of fat losses. the tail eats the hump. barely.</p></div>
    <div class="section"><h2>rolling 7-day net</h2>{line([roll])}<p>last 7 days: <span class="{cls(roll[-1])}">{money(roll[-1])}</span>.</p></div>""")

    items = [("v1", "the curve", "equity curve + stat strip"), ("v2", "red/green", "daily bars + calendar heatmap"),
             ("v3", "two teams", "kalshi vs polymarket, stacked + cumulative"), ("v4", "brutal honesty", "big numbers, win-rate paradox, fees, drawdown"),
             ("v5", "the distribution", "bet histogram, avg win/loss, rolling 7d")]
    page(0, "pnl versions · pick one", "five ways to show the same pain",
         '<div class="section"><h2>prototypes</h2>' + "".join(f'<div class="project"><a class="project-title" href="/pnl/{v}/">{v} · {t}</a><p>{d}</p></div>' for v, t, d in items) + "</div>")
    print("built pnl versions")


if __name__ == "__main__":
    main()
