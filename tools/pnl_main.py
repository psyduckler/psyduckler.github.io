"""The live /pnl/ page: equity curve + stat strip, daily bars + calendar heatmap,
recent rows and a Polymarket section, with a combined / kalshi / polymarket toggle.
Data: data/pnl_history.json (aggregates only). Called from tools/build.py."""
import build_pnl_versions as V
import build

import html as _h, datetime as _dt

def _tips(days, kby, pby, split):
    out = []; c = pk = 0
    for d in days:
        c += d["net"]; pk = max(pk, c)
        k, p = kby.get(d["date"]), pby.get(d["date"])
        parts = [x for x in (k, p) if x] if split else [d]
        best = max(x["best"] for x in parts if "best" in x) if any("best" in x for x in parts) else None
        worst = min(x["worst"] for x in parts if "worst" in x) if any("worst" in x for x in parts) else None
        day = (f'<b>{V.f(d["date"])}</b><br>net {V.money(d["net"])} · {d["n"]} settled · {d["w"]}W/{d["l"]}L '
               f'({d["w"] / d["n"] * 100:.0f}%)<br>fees ${d["fees"]:,.2f}')
        if best is not None: day += f'<br>best {V.money(best)} · worst {V.money(worst)}'
        if split: day += f'<br>kalshi {V.money(k["net"]) if k else "–"} · polymarket {V.money(p["net"]) if p else "–"}'
        eq = f'<b>{V.f(d["date"])}</b><br>running total {V.money(c)}<br>day {V.money(d["net"])}<br>drawdown {V.money(c - pk)}'
        out.append((day, eq, c))
    return out

def _a(t): return _h.escape(t, quote=True)

def eq_svg(days, tips, w=640, h=200):
    """cumulative bars: one bar per day, height = running total."""
    cur = [t[2] for t in tips]; y = V.scale(cur, 10, h - 10); bw = w / len(cur); out = []
    for i, (v, t) in enumerate(zip(cur, tips)):
        out.append(f'<rect x="{i * bw + 1:.1f}" width="{max(bw - 2, 1):.1f}" y="{min(y(v), y(0)):.1f}" height="{max(abs(y(v) - y(0)), 1):.1f}" fill="{"var(--pos)" if v >= 0 else "var(--neg)"}"/>'
                   f'<rect class="hit" x="{i * bw:.1f}" y="0" width="{bw:.1f}" height="{h}" data-tip="{_a(t[1])}"/>')
    return (f'<svg class="chart" viewBox="0 0 {w} {h}" width="100%">{"".join(out)}'
            f'<line x1="0" x2="{w}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="var(--muted)" stroke-dasharray="3 3"/></svg>')

def bar_svg(days, tips, w=640, h=200):
    vals = [d["net"] for d in days]; y = V.scale(vals, 10, h - 10); bw = w / len(vals); out = []
    for i, (v, t) in enumerate(zip(vals, tips)):
        out.append(f'<rect x="{i * bw + 1:.1f}" width="{max(bw - 2, 1):.1f}" y="{min(y(v), y(0)):.1f}" height="{max(abs(y(v) - y(0)), 1):.1f}" fill="{"var(--pos)" if v >= 0 else "var(--neg)"}"/>'
                   f'<rect class="hit" x="{i * bw:.1f}" y="0" width="{bw:.1f}" height="{h}" data-tip="{_a(t[0])}"/>')
    return f'<svg class="chart" viewBox="0 0 {w} {h}" width="100%">{"".join(out)}</svg>'

def heat_svg(days, tips):
    tip = {d["date"]: t[0] for d, t in zip(days, tips)}; by = {d["date"]: d["net"] for d in days}
    d0 = _dt.date.fromisoformat(days[0]["date"]); d1 = _dt.date.fromisoformat(days[-1]["date"])
    d0 -= _dt.timedelta(days=d0.weekday()); cs = 14; out = []; mx = max(abs(v) for v in by.values()) or 1; i = 0; d = d0
    while d <= d1:
        k = d.isoformat(); v = by.get(k); x = (i // 7) * (cs + 2); yy = d.weekday() * (cs + 2)
        if v is None:
            out.append(f'<rect x="{x}" y="{yy}" width="{cs}" height="{cs}" fill="var(--border-soft)" class="hit2" data-tip="{_a("<b>" + V.f(k) + "</b><br>nothing settled")}"/>')
        else:
            out.append(f'<rect x="{x}" y="{yy}" width="{cs}" height="{cs}" fill="{"var(--pos)" if v >= 0 else "var(--neg)"}" fill-opacity="{.25 + .75 * abs(v) / mx:.2f}" class="hit2" data-tip="{_a(tip[k])}"/>')
        d += _dt.timedelta(days=1); i += 1
    return f'<svg class="chart" viewBox="0 0 {(i // 7 + 1) * (cs + 2)} {7 * (cs + 2)}" width="100%">{"".join(out)}</svg>'

TIPJS = """<div id="tip" hidden></div><script>(function(){var t=document.getElementById('tip'),pin=null;
function show(el,ev){t.innerHTML=el.dataset.tip;t.hidden=false;var r=el.getBoundingClientRect(),x=(ev&&ev.clientX)||r.left+r.width/2,y=(ev&&ev.clientY)||r.top;
t.style.left=Math.max(8,Math.min(window.innerWidth-t.offsetWidth-8,x+12))+'px';t.style.top=Math.max(8,y-t.offsetHeight-12)+window.scrollY+'px';
var s=el.ownerSVGElement,dot=s&&s.querySelector('.dot');if(dot&&el.dataset.x){dot.setAttribute('cx',el.dataset.x);dot.setAttribute('cy',el.dataset.y)}}
function hide(){if(pin)return;t.hidden=true;document.querySelectorAll('.dot').forEach(function(d){d.setAttribute('cx',-9)})}
document.querySelectorAll('[data-tip]').forEach(function(el){el.addEventListener('mousemove',function(e){if(!pin)show(el,e)});el.addEventListener('mouseleave',hide);
el.addEventListener('click',function(e){e.stopPropagation();pin=el;show(el,e)})});
document.addEventListener('click',function(){pin=null;hide()})})();</script>"""

def strip(M):
    s = V.stat
    return (f'<div class="strip">{s("total net", V.money(M["net"]), V.cls(M["net"]))}{s("win rate", f"{M["wr"]:.1f}%")}'
            f'{s("profit factor", f"{M["pf"]:.2f}")}{s("best day", V.money(M["best"]), "pos")}{s("worst day", V.money(M["worst"]), "neg")}'
            f'{s("max drawdown", V.money(M["dd"]), "neg")}{s("sharpe-ish", f"{M["sharpe"]:.2f}")}{s("settled", f"{M["trades"]:,}")}'
            f'{s("fees", f"${M["fees"]:,.2f}")}{s("green days", f"{M["green"]}/{M["days"]}")}</div>')

def dmetrics(days):
    """metrics from daily rows only (each row carries w, l, gw, gl, fees, best, worst)."""
    import statistics as st
    nets = [d["net"] for d in days]; c = pk = dd = 0; curve = []
    for n in nets:
        c += n; pk = max(pk, c); dd = min(dd, c - pk); curve.append(c)
    nw = sum(d["w"] for d in days); nl = sum(d["l"] for d in days)
    gw = sum(d["gw"] for d in days); gl = sum(d["gl"] for d in days)
    sd = st.pstdev(nets) if len(nets) > 1 else 0
    return dict(days=len(days), net=sum(nets), trades=nw + nl, wr=nw / max(nw + nl, 1) * 100,
                pf=gw / -gl if gl else float("inf"), best=max(nets), worst=min(nets), dd=dd,
                sharpe=(st.mean(nets) / sd * 365 ** .5) if sd else 0.0, fees=sum(d["fees"] for d in days),
                green=sum(n > 0 for n in nets), curve=curve)

def combine(K, P):
    out = {}
    for d in K + P:
        a = out.setdefault(d["date"], dict(date=d["date"], n=0, w=0, l=0, net=0.0, fees=0.0, gw=0.0, gl=0.0, best=-1e18, worst=1e18))
        for k in ("n", "w", "l", "net", "fees", "gw", "gl"): a[k] += d[k]
        a["best"] = max(a["best"], d["best"]); a["worst"] = min(a["worst"], d["worst"])
    return [out[k] for k in sorted(out)]

RANGES = (("all", "all", None), ("90", "90d", 90), ("30", "30d", 30), ("7", "7d", 7))

def panel(key, label, days, M, span, kby=None, pby=None, rng="all"):
    tips = _tips(days, kby or {}, pby or {}, key == "all")
    return (f'<div class="view" data-view="{key}" data-range="{rng}"{"" if (key == "all" and rng == "90") else " hidden"}>'
            f'<div class="section"><h2>{label} · equity</h2>{strip(M)}{eq_svg(days, tips)}'
            f'<p class="small">{span}. net after fees. max drawdown is peak-to-trough on the running total.</p></div>'
            f'<div class="section"><h2>{label} · daily net</h2>{bar_svg(days, tips)}'
            f'<p>{M["green"]} green days, {M["days"] - M["green"]} red. best {V.money(M["best"])}, worst {V.money(M["worst"])}.</p></div>'
            f'<div class="section"><h2>{label} · calendar</h2>{heat_svg(days, tips)}<p class="small">brighter = bigger. grey = nothing settled. mon at top.</p></div></div>')

def pm_table(P):
    import datetime as dt
    m = V.money
    rows = ""
    nxt = (dt.date.fromisoformat(P[-1]["date"]) + dt.timedelta(days=1)).isoformat()
    rows += (f'<tr><td>{V.f(nxt)}</td><td colspan="6" style="text-align:right;color:var(--muted)">pending: resolutions still landing</td></tr>')
    for d in reversed(P):
        rows += (f'<tr><td>{V.f(d["date"])}</td><td>{d["n"]}</td><td>{d["w"]}/{d["l"]}</td>'
                 f'<td class="{V.cls(d["net"])}">{m(d["net"])}</td><td>${d["fees"]:,.2f}</td>'
                 f'<td class="pos">{m(d["best"])}</td><td class="neg">{m(d["worst"])}</td></tr>')
    return ('<h2>polymarket · daily totals</h2><table><tr><th>day</th><th>settled</th><th>w/l</th>'
            f'<th>net</th><th>fees</th><th>best</th><th>worst</th></tr>{rows}</table>')

def render(H_meta):
    K, P, A = V.K, V.P, V.ALLD
    f = V.f
    kby = {d["date"]: d for d in K}; pby = {d["date"]: d for d in P}
    rows = ""
    for d in reversed(A[-5:]):
        k, p = kby.get(d["date"]), pby.get(d["date"])
        cell = lambda x: f'<td class="{V.cls(x["net"])}">{V.money(x["net"])}</td>' if x else "<td>–</td>"
        rows += (f'<tr><td>{f(d["date"])}</td><td>{d["n"]}</td><td>{d["w"]}/{d["l"]}</td>{cell(k)}{cell(p)}'
                 f'<td class="{V.cls(d["net"])}">{V.money(d["net"])}</td><td>${d["fees"]:,.2f}</td></tr>')
    toggle = ('<div class="vt" role="tablist">' + "".join(
        f'<button type="button" class="vbtn{" on" if k == "all" else ""}" data-v="{k}">{t}</button>'
        for k, t in (("all", "combined"), ("k", "kalshi"), ("p", "polymarket"))) + "</div>")
    js = ("<script>(function(){var v='all',r='90';function upd(){document.querySelectorAll('.view').forEach(function(p){p.hidden=!(p.dataset.view===v&&p.dataset.range===r)});"
          "document.querySelectorAll('.vbtn').forEach(function(b){b.classList.toggle('on',b.dataset.v===v)});document.querySelectorAll('.rbtn').forEach(function(b){b.classList.toggle('on',b.dataset.r===r)})}"
          "document.querySelectorAll('.vbtn').forEach(function(b){b.onclick=function(){v=b.dataset.v;upd()}});document.querySelectorAll('.rbtn').forEach(function(b){b.onclick=function(){r=b.dataset.r;upd()}});"
          "var m=location.hash.match(/r=(all|90|30|7)/);if(m){r=m[1];upd()}})()</script>")
    css = ('<style>' + V.EXTRA + '.vt{margin:0 0 1.5rem}.vbtn{font:inherit;font-size:.8rem;background:none;color:var(--muted);border:1px solid var(--border);padding:.25rem .7rem;margin-right:.4rem;cursor:pointer}'
           '.vbtn.on,.rbtn.on{color:var(--accent);border-color:var(--accent)}.ctl{display:flex;flex-wrap:wrap;gap:.5rem 1.25rem;margin:0 0 1.5rem}.ctl .vt{margin:0}.rbtn{font:inherit;font-size:.8rem;background:none;color:var(--muted);border:1px solid var(--border);padding:.25rem .6rem;margin-right:.3rem;cursor:pointer}'
           '.strip{grid-template-columns:repeat(5,1fr);gap:.4rem}.strip .stat{padding:.55rem .5rem;min-width:0}.strip .stat b{font-size:.92rem;white-space:nowrap}.strip .stat span{font-size:.62rem;letter-spacing:.06em}@media(max-width:600px){.strip{grid-template-columns:repeat(2,1fr)}}'
           '.hit{fill:transparent;cursor:crosshair}.hit2{cursor:crosshair}.hit2:hover{stroke:var(--fg)}'
           '#tip{position:absolute;z-index:9;background:var(--card);color:var(--fg);border:1px solid var(--accent);padding:.45rem .6rem;font-size:.75rem;line-height:1.5;pointer-events:none;max-width:280px}</style>')
    import datetime as dt
    latest = dt.date.fromisoformat(max(K[-1]["date"], P[-1]["date"]))
    A = combine(K, P)
    panels = ""
    for rk, rl, n in RANGES:
        cut = (latest - dt.timedelta(days=n - 1)).isoformat() if n else ""
        sub = lambda ds: [d for d in ds if d["date"] >= cut]
        for key, label, ds in (("all", "combined", A), ("k", "kalshi", K), ("p", "polymarket", P)):
            r = sub(ds)
            if not r:
                panels += f'<div class="view" data-view="{key}" data-range="{rk}" hidden><p>nothing settled in this window.</p></div>'; continue
            span = f"{rl} · {f(r[0]['date'])} → {f(r[-1]['date'])}" + ("" if not n else f" (window counts back from {f(latest.isoformat())})")
            panels += panel(key, f"{label} · {rl}", r, dmetrics(r), span, kby=kby, pby=pby, rng=rk)
    rtoggle = ('<div class="vt rt">' + "".join(
        f'<button type="button" class="rbtn vbtn2{" on" if k == "90" else ""}" data-r="{k}">{t}</button>' for k, t, _ in RANGES) + "</div>")
    body = (css + '<p>receipts for both teams. settled bets only, net after fees, red days included. aggregates only: no positions, no strategies, no balances.</p>'
            + '<div class="ctl">' + toggle + rtoggle + '</div>' + panels
            + f'<div class="section"><h2>recent days</h2><table><tr><th>day</th><th>settled</th><th>w/l</th><th>kalshi</th><th>polymarket</th><th>net</th><th>fees</th></tr>{rows}</table></div>'
            + js + TIPJS)
    build.page("/pnl/", "pnl/index.html", "PnL · Bernard's Grok Bot team",
               "Daily prediction-market PnL from Bernard's Grok Bot teams (Kalshi + Polymarket). Totals only, red days included.",
               "pnl", "the receipts", body)
