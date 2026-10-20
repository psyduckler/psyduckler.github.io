"""The live /pnl/ page: stat strip (incl. sharpe), cumulative bars, daily bars + calendar heatmap, P&L by kind of
trade (cumulative per-category lines + sortable category table) and recent days, with a
combined / kalshi / polymarket / opensea toggle and all / 90d / 30d / 7d windows.
Data: data/pnl_history.json + data/pnl_cats.json (aggregates only; see pnl_categories.py). Called from tools/build.py."""
import build_pnl_versions as V
import build

import html as _h, datetime as _dt

def _tips(days, kby, pby, split, oby=None):
    out = []; c = pk = 0; oby = oby or {}
    for d in days:
        c += d["net"]; pk = max(pk, c)
        k, p, o = kby.get(d["date"]), pby.get(d["date"]), oby.get(d["date"])
        parts = [x for x in (k, p, o) if x] if split else [d]
        best = max(x["best"] for x in parts if "best" in x) if any("best" in x for x in parts) else None
        worst = min(x["worst"] for x in parts if "worst" in x) if any("worst" in x for x in parts) else None
        day = (f'<b>{V.f(d["date"])}</b><br>net {V.money(d["net"])} · {d["n"]} settled · {d["w"]}W/{d["l"]}L '
               f'({d["w"] / d["n"] * 100:.0f}%)<br>fees ${d["fees"]:,.2f}')
        if best is not None: day += f'<br>best {V.money(best)} · worst {V.money(worst)}'
        if split: day += (f'<br>kalshi {V.money(k["net"]) if k else "–"} · polymarket {V.money(p["net"]) if p else "–"}'
                          f' · opensea {V.money(o["net"]) if o else "–"}')
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
            f'{s("max drawdown", V.money(M["dd"]), "neg")}{s("sharpe ratio", f"{M["sharpe"]:.2f}")}{s("settled", f"{M["trades"]:,}")}'
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

def combine(*venues):
    out = {}
    for d in [x for v in venues for x in v]:
        a = out.setdefault(d["date"], dict(date=d["date"], n=0, w=0, l=0, net=0.0, fees=0.0, gw=0.0, gl=0.0, best=-1e18, worst=1e18))
        for k in ("n", "w", "l", "net", "fees", "gw", "gl"): a[k] += d[k]
        a["best"] = max(a["best"], d["best"]); a["worst"] = min(a["worst"], d["worst"])
    return [out[k] for k in sorted(out)]

RANGES = (("all", "all", None), ("90", "90d", 90), ("30", "30d", 30), ("7", "7d", 7))
VENUES = (("all", "combined"), ("k", "kalshi"), ("p", "polymarket"), ("o", "opensea"))

PM_STATUS = V.H.get("pm_status", "")  # set in data/pnl_history.json; clear it ("") once a new pm release lands

def pm_note(): return f'<p class="small pmnote">{_h.escape(PM_STATUS)}</p>' if PM_STATUS else ""

OS_NOTE = "opensea: nft flips, fully settled CT days, net after opensea fees and gas (incl. cancels and approvals)."
def os_note(): return f'<p class="small pmnote">{OS_NOTE}</p>'

# ---------------------------------------------------------------- P&L by kind of trade
import json as _json, pnl_categories as PC
CATS = PC.CATEGORIES
CAT_ROWS = _json.loads((build.ROOT / "data/pnl_cats.json").read_text())["rows"]
SHORT = {"wx_high": "Wx highs", "wx_low": "Wx lows", "wx_rain": "Wx rain", "mention": "Mentions", "copy": "Copy trading",
         "crypto": "Crypto", "nft": "NFT flips", "manual": "Manual"}
CHIP = {"k": "kalshi", "p": "pm", "o": "opensea"}
C = PC.C

def short_money(v):
    a = abs(v); sgn = "+" if v > 0 else ("-" if v < 0 else "")
    return sgn + (f"${a / 1000:.1f}k" if a >= 1000 else f"${a:,.0f}")

def cat_css():
    dark = "".join(f"--c-{k}:{d};" for k, _, _, l, d in CATS); light = "".join(f"--c-{k}:{l};" for k, _, _, l, d in CATS)
    return (f":root{{{dark}}}@media (prefers-color-scheme: light){{:root:not([data-theme=dark]){{{light}}}}}:root[data-theme=light]{{{light}}}")

def cat_view(vkey, start, end, days_net_c):
    """per-category aggregates for one venue view and window [start, end]; checks Σ categories == venue to the cent."""
    cats = [c for c in CATS if vkey == "all" or vkey in c[2]]
    rows = [r for r in CAT_ROWS if (vkey == "all" or r["v"] == vkey) and start <= r["d"] <= end]
    total = sum(C(r["net"]) for r in rows)
    if total != days_net_c:
        raise SystemExit(f"category sum {total} != venue {days_net_c} cents for view {vkey} {start}..{end}")
    d0, d1 = _dt.date.fromisoformat(start), _dt.date.fromisoformat(end)
    dates = [(d0 + _dt.timedelta(days=i)).isoformat() for i in range((d1 - d0).days + 1)]
    ix = {d: i for i, d in enumerate(dates)}
    out = []
    for k, label, ven, _, _ in cats:
        mine = [r for r in rows if r["c"] == k]
        daily = [0] * len(dates)
        for r in mine: daily[ix[r["d"]]] += C(r["net"])
        cum, c = [], 0
        for x in daily: c += x; cum.append(c)
        n = sum(r["n"] for r in mine); w = sum(r["w"] for r in mine); l = sum(r["l"] for r in mine)
        gw = sum(C(r["gw"]) for r in mine); gl = sum(C(r["gl"]) for r in mine)
        out.append(dict(k=k, label=label, ven=[v for v in "kpo" if v in ven and (vkey == "all" or v == vkey)],
                        net=sum(daily), n=n, w=w, l=l, wr=(w / n * 100) if n else None,
                        pf=(gw / -gl if gl else (float("inf") if gw else None)) if n else None, cum=cum))
    return dates, out

def line_svg(dates, cats, w=640, h=260, L=46, R=122, cls="lcd", xt=4):
    T, B = 12, 24
    pw, ph = w - L - R, h - T - B
    allv = [v for c in cats for v in c["cum"]] + [0]
    lo, hi = min(allv), max(allv)
    step = max(1, (hi - lo) / 4 / 100)
    mag = 10 ** len(str(int(step))) / 10; step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= step) * 100
    lo = (lo // step) * step; hi = -((-hi) // step) * step
    if hi == lo: hi = lo + step
    y = lambda v: T + (hi - v) / (hi - lo) * ph
    n = len(dates); x = lambda i: L + (i / (n - 1) * pw if n > 1 else pw / 2)
    g = []
    t = lo
    while t <= hi + 1e-9:
        g.append(f'<line x1="{L}" x2="{L + pw}" y1="{y(t):.1f}" y2="{y(t):.1f}" class="{"g0" if t == 0 else "g"}"/>'
                 f'<text x="{L - 6}" y="{y(t) + 4:.1f}" text-anchor="end" class="ax">{short_money(t / 100).lstrip("+")}</text>')
        t += step
    for i in sorted({0, n - 1, *range(0, n, max(1, n // xt))}):
        if 0 < i < n - 1 and ((n - 1 - i) < n / (2 * xt) or i < n / (2 * xt)): continue
        g.append(f'<text x="{x(i):.1f}" y="{h - 6}" text-anchor="{"start" if i == 0 else ("end" if i == n - 1 else "middle")}" class="ax">'
                 f'{_dt.date.fromisoformat(dates[i]).strftime("%b %-d").lower()}</text>')
    lines, ends = [], []
    for c in cats:
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(c["cum"]))
        if n == 1: pts = f"{L},{y(0):.1f} " + pts
        lines.append(f'<polyline points="{pts}" fill="none" stroke="var(--c-{c["k"]})" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
        ends.append([y(c["cum"][-1]), c])
    ends.sort(key=lambda e: e[0])
    gap, top, bot = 13, T + 4, T + ph
    for i in range(len(ends)):                  # push down to keep >= 13px apart ...
        if i and ends[i][0] < ends[i - 1][0] + gap: ends[i][0] = ends[i - 1][0] + gap
        ends[i][0] = max(ends[i][0], top)
    if ends and ends[-1][0] > bot:             # ... then pull back up inside the plot
        ends[-1][0] = bot
        for i in range(len(ends) - 2, -1, -1): ends[i][0] = min(ends[i][0], ends[i + 1][0] - gap)
    labs = "".join(f'<circle cx="{L + pw:.1f}" cy="{y(c["cum"][-1]):.1f}" r="2.5" fill="var(--c-{c["k"]})"/>'
                   f'<text x="{L + pw + 6}" y="{ly + 4:.1f}" class="el">{SHORT[c["k"]]} {short_money(c["cum"][-1] / 100)}</text>' for ly, c in ends)
    return (f'<svg class="chart lc {cls}" viewBox="0 0 {w} {h}" width="100%" data-l="{L}" data-pw="{pw}" role="img" '
            f'aria-label="cumulative net by kind of trade">{"".join(g)}{"".join(lines)}{labs}'
            f'<line class="xh" x1="-9" x2="-9" y1="{T}" y2="{T + ph}"/><rect class="lchit" x="{L}" y="{T}" width="{pw}" height="{ph}"/></svg>')

def spark(cum, k, w=84, h=22):
    if not cum: return ""
    lo, hi = min(cum + [0]), max(cum + [0]); r = (hi - lo) or 1; n = len(cum)
    pts = " ".join(f"{(i / (n - 1) * (w - 4) + 2) if n > 1 else w / 2:.1f},{h - 2 - (v - lo) / r * (h - 4):.1f}" for i, v in enumerate(cum))
    if n == 1: pts = f"2,{h - 2 - (0 - lo) / r * (h - 4):.1f} " + pts
    z = h - 2 - (0 - lo) / r * (h - 4)
    return (f'<svg class="spark" viewBox="0 0 {w} {h}" width="{w}" height="{h}" aria-hidden="true"><line x1="0" x2="{w}" y1="{z:.1f}" y2="{z:.1f}" class="g"/>'
            f'<polyline points="{pts}" fill="none" stroke="var(--c-{k})" stroke-width="1.5" stroke-linejoin="round"/></svg>')

def cat_table(cats, rl):
    def num(v, txt, c=""): return f'<td data-v="{"" if v is None else v}"{f" class={chr(34)}{c}{chr(34)}" if c else ""}>{txt}</td>'
    body = ""
    for i, c in enumerate(cats):
        empty = c["n"] == 0
        chips = "".join(f'<span class="chip">{CHIP[v]}</span>' for v in c["ven"])
        pf = c["pf"]
        body += (f'<tr data-i="{i}"><td data-v="{_a(c["label"].lower())}"><span class="dot" style="background:var(--c-{c["k"]})"></span>{_h.escape(c["label"].lower())}</td>'
                 f'<td data-v="{" ".join(CHIP[v] for v in c["ven"])}" class="chips">{chips}</td>'
                 + num(None if empty else c["net"] / 100, "—" if empty else V.money(c["net"] / 100), "" if empty else V.cls(c["net"]))
                 + num(None if empty else c["n"], "—" if empty else f'{c["n"]:,}')
                 + num(None if empty else round(c["wr"], 2), "—" if empty else f'{c["wr"]:.0f}%')
                 + num(None if pf is None else (1e9 if pf == float("inf") else round(pf, 4)), "—" if pf is None else ("∞" if pf == float("inf") else f"{pf:.2f}"))
                 + num(None if empty else c["net"] / 100, spark(c["cum"], c["k"]) if not empty else "—") + "</tr>")
    th = lambda t, typ: f'<th scope="col" data-t="{typ}" tabindex="0" aria-sort="none">{t}</th>'
    return ('<div class="tw"><table class="ctab"><thead><tr>' + th("category", "txt") + th("venues", "txt") + th(f"net {rl}", "num")
            + th("settled", "num") + th("win %", "num") + th("pf", "num") + th(f"trend {rl}", "num") + f'</tr></thead><tbody>{body}</tbody></table></div>')

def cat_section(vkey, label, rl, start, end, days):
    dates, cats = cat_view(vkey, start, end, sum(C(d["net"]) for d in days))
    legend = "".join(f'<span class="lg"><span class="dot" style="background:var(--c-{c["k"]})"></span>{_h.escape(c["label"].lower())}</span>' for c in cats)
    data = _a(_json.dumps({"d": dates, "s": [[c["label"], c["k"], c["cum"]] for c in cats]}, separators=(",", ":")))
    charts = (f'<div class="lcw" data-lc="{data}">{line_svg(dates, cats)}'
              f'{line_svg(dates, cats, w=360, h=300, L=40, R=104, cls="lcm", xt=2)}</div>')
    return (f'<div class="section"><h2>{label} · by kind of trade</h2>{charts}<p class="legend2">{legend}</p>'
            f'{cat_table(cats, rl)}<p class="small cnote">cumulative net per kind of trade inside the window, each line starting at $0. '
            'kalshi by market series; polymarket by book type (copy, crypto, and weather split by high / low / rain); opensea = nft flips. '
            'win % = settled rows with net &gt; 0 (kalshi per leg, polymarket per ticket, opensea per flip). pf = gross wins / gross losses. '
            'click a column to sort.</p></div>')

def panel(key, label, days, M, span, kby=None, pby=None, oby=None, rng="all", cats=""):
    tips = _tips(days, kby or {}, pby or {}, key == "all", oby or {})
    note = pm_note() if key == "p" else (os_note() if key == "o" else "")
    return (f'<div class="view" data-view="{key}" data-range="{rng}"{"" if (key == "all" and rng == "90") else " hidden"}>'
            f'<div class="section"><h2>{label} · equity</h2>{note}{strip(M)}{eq_svg(days, tips)}'
            f'<p class="small">{span}. net after fees. max drawdown is peak-to-trough on the running total.</p></div>'
            + cats +
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

LCJS = """<script>(function(){var t=document.getElementById('tip');
document.querySelectorAll('svg.lc').forEach(function(s){var D=JSON.parse(s.parentNode.dataset.lc),L=+s.dataset.l,PW=+s.dataset.pw,n=D.d.length,
xh=s.querySelector('.xh'),hit=s.querySelector('.lchit');
function fmt(c){var v=c/100,a=Math.abs(v);return (v>0?'+':v<0?'-':'')+'$'+a.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})}
function mv(e){var p=s.createSVGPoint();p.x=e.clientX;p.y=e.clientY;var q=p.matrixTransform(s.getScreenCTM().inverse());
var i=n>1?Math.round((q.x-L)/PW*(n-1)):0;i=Math.max(0,Math.min(n-1,i));var x=L+(n>1?i/(n-1)*PW:PW/2);xh.setAttribute('x1',x);xh.setAttribute('x2',x);
var r=D.s.map(function(c){return [c[0],c[1],c[2][i]]}).sort(function(a,b){return b[2]-a[2]});
var d=new Date(D.d[i]+'T12:00:00');t.innerHTML='<b>'+d.toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}).toLowerCase()+'</b>'+
r.map(function(c){return '<br><span class="dot" style="background:var(--c-'+c[1]+')"></span>'+c[0].toLowerCase()+' <span class="'+(c[2]>=0?'pos':'neg')+'">'+fmt(c[2])+'</span>'}).join('');
t.hidden=false;t.style.left=Math.max(8,Math.min(window.innerWidth-t.offsetWidth-8,e.clientX+12))+'px';t.style.top=Math.max(8,e.clientY-t.offsetHeight-12)+window.scrollY+'px'}
hit.addEventListener('mousemove',mv);hit.addEventListener('click',function(e){e.stopPropagation();mv(e)});
hit.addEventListener('mouseleave',function(){t.hidden=true;xh.setAttribute('x1',-9);xh.setAttribute('x2',-9)})})})();</script>"""

SORTJS = """<script>(function(){var K='overview-sort',st=null;try{st=JSON.parse(localStorage.getItem(K)||'null')}catch(e){st=null}
function nat(th){return th.dataset.t==='num'?'desc':'asc'}
function apply(){document.querySelectorAll('table.ctab').forEach(function(tb){var ths=tb.querySelectorAll('th'),body=tb.tBodies[0],rows=[].slice.call(body.rows);
ths.forEach(function(th,j){th.setAttribute('aria-sort',st&&st.c===j?(st.d==='asc'?'ascending':'descending'):'none')});
rows.sort(function(a,b){if(!st)return a.dataset.i-b.dataset.i;var th=ths[st.c];if(!th)return a.dataset.i-b.dataset.i;
var x=a.cells[st.c].dataset.v,y=b.cells[st.c].dataset.v;if(x===''&&y==='')return a.dataset.i-b.dataset.i;if(x==='')return 1;if(y==='')return -1;
var r=th.dataset.t==='num'?(+x)-(+y):x.localeCompare(y);if(r===0)return a.dataset.i-b.dataset.i;return st.d==='asc'?r:-r});
rows.forEach(function(r){body.appendChild(r)})})}
function click(th){var j=[].indexOf.call(th.parentNode.children,th),n=nat(th);
if(!st||st.c!==j)st={c:j,d:n};else if(st.d===n)st={c:j,d:n==='asc'?'desc':'asc'};else st=null;
try{st?localStorage.setItem(K,JSON.stringify(st)):localStorage.removeItem(K)}catch(e){}apply()}
document.querySelectorAll('table.ctab th').forEach(function(th){th.addEventListener('click',function(){click(th)});
th.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();click(th)}})});apply()})();</script>"""

def render(H_meta):
    K, P = V.K, V.P
    O = V.H.get("opensea", [])
    f = V.f
    kby = {d["date"]: d for d in K}; pby = {d["date"]: d for d in P}; oby = {d["date"]: d for d in O}
    A = combine(K, P, O)
    last = {"k": K[-1]["date"], "p": P[-1]["date"], "o": O[-1]["date"] if O else ""}
    rows = ""
    for d in reversed(A[-5:]):
        def cell(by, v):
            x = by.get(d["date"])
            if x: return f'<td class="{V.cls(x["net"])}">{V.money(x["net"])}</td>'
            return '<td class="muted">pending</td>' if d["date"] > last[v] else "<td>–</td>"
        rows += (f'<tr><td>{f(d["date"])}</td><td>{d["n"]}</td><td>{d["w"]}/{d["l"]}</td>{cell(kby, "k")}{cell(pby, "p")}{cell(oby, "o")}'
                 f'<td class="{V.cls(d["net"])}">{V.money(d["net"])}</td><td>${d["fees"]:,.2f}</td></tr>')
    toggle = ('<div class="vt" role="tablist">' + "".join(
        f'<button type="button" class="vbtn{" on" if k == "all" else ""}" data-v="{k}">{t}</button>' for k, t in VENUES) + "</div>")
    js = ("<script>(function(){var v='all',r='90';function upd(){document.querySelectorAll('.view').forEach(function(p){p.hidden=!(p.dataset.view===v&&p.dataset.range===r)});"
          "document.querySelectorAll('.vbtn').forEach(function(b){b.classList.toggle('on',b.dataset.v===v)});document.querySelectorAll('.rbtn').forEach(function(b){b.classList.toggle('on',b.dataset.r===r)})}"
          "document.querySelectorAll('.vbtn').forEach(function(b){b.onclick=function(){v=b.dataset.v;upd()}});document.querySelectorAll('.rbtn').forEach(function(b){b.onclick=function(){r=b.dataset.r;upd()}});"
          "var m=location.hash.match(/r=(all|90|30|7)/);if(m){r=m[1];upd()}})()</script>")
    css = ('<style>' + V.EXTRA + cat_css() + '.vt{margin:0 0 1.5rem}.vbtn{font:inherit;font-size:.8rem;background:none;color:var(--muted);border:1px solid var(--border);padding:.25rem .7rem;margin:0 .4rem .3rem 0;cursor:pointer}'
           '.vbtn.on,.rbtn.on{color:var(--accent);border-color:var(--accent)}.ctl{display:flex;flex-wrap:wrap;gap:.5rem 1.25rem;margin:0 0 1.5rem}.ctl .vt{margin:0}.rbtn{font:inherit;font-size:.8rem;background:none;color:var(--muted);border:1px solid var(--border);padding:.25rem .6rem;margin-right:.3rem;cursor:pointer}'
           '.strip{grid-template-columns:repeat(5,1fr);gap:.4rem}.strip .stat{padding:.55rem .5rem;min-width:0}.strip .stat b{font-size:.92rem;white-space:nowrap}.strip .stat span{font-size:.62rem;letter-spacing:.06em}@media(max-width:600px){.strip{grid-template-columns:repeat(2,1fr)}.vbtn{padding:.25rem .5rem;margin-right:.25rem}}'
           '.pmnote{color:var(--muted);margin:.2rem 0 .8rem}.hit{fill:transparent;cursor:crosshair}.hit2{cursor:crosshair}.hit2:hover{stroke:var(--fg)}'
           '#tip{position:absolute;z-index:9;background:var(--card);color:var(--fg);border:1px solid var(--accent);padding:.45rem .6rem;font-size:.75rem;line-height:1.5;pointer-events:none;max-width:280px}'
           '.tw{overflow-x:auto;-webkit-overflow-scrolling:touch;max-width:100%;margin-bottom:.8rem}.muted{color:var(--muted)}'
           '.lc .g,.spark .g{stroke:var(--border);stroke-width:.5}.lc .g0{stroke:var(--muted);stroke-width:1}.lc .ax{fill:var(--muted);font-size:10px;font-family:inherit}'
           '.lc .el{fill:var(--fg);font-size:10.5px;font-family:inherit}.lc .xh{stroke:var(--muted);stroke-width:1;stroke-dasharray:2 2}.lchit{fill:transparent;cursor:crosshair}'
           '.dot{display:inline-block;width:.6em;height:.6em;border-radius:50%;margin-right:.45em;vertical-align:middle}'
           '.lcm{display:none}@media(max-width:600px){.lcd{display:none}.lcm{display:block}}.section .legend2{font-size:.72rem;color:var(--muted);display:flex;flex-wrap:wrap;gap:.1rem .9rem;margin:.4rem 0 .8rem!important}.lg{white-space:nowrap}'
           '.ctab{min-width:520px}.ctab th{cursor:pointer;user-select:none;white-space:nowrap}.ctab th:hover,.ctab th:focus{color:var(--accent);outline:none}'
           '.ctab th[aria-sort=ascending]::after{content:" ↑"}.ctab th[aria-sort=descending]::after{content:" ↓"}.ctab td{white-space:nowrap;vertical-align:middle}.ctab td:nth-child(2){text-align:left}.ctab th:nth-child(2){text-align:left}'
           '.chip{display:inline-block;font-size:.6rem;letter-spacing:.05em;border:1px solid var(--border);color:var(--muted);padding:0 .3rem;margin-right:.2rem;line-height:1.5}'
           '.section p.cnote{font-size:.75rem;line-height:1.6}.spark{display:inline-block;vertical-align:middle}.rtab{min-width:560px}</style>')
    latest = _dt.date.fromisoformat(max(v for v in last.values() if v))
    panels = ""
    for rk, rl, n in RANGES:
        cut = (latest - _dt.timedelta(days=n - 1)).isoformat() if n else ""
        sub = lambda ds: [d for d in ds if d["date"] >= cut]
        for key, label in VENUES:
            ds = {"all": A, "k": K, "p": P, "o": O}[key]
            r = sub(ds)
            if not r:
                panels += (f'<div class="view" data-view="{key}" data-range="{rk}" hidden><div class="section"><h2>{label} · {rl}</h2>'
                           f'<p>nothing settled in this window.</p>{pm_note() if key == "p" else (os_note() if key == "o" else "")}</div></div>'); continue
            span = f"{rl} · {f(r[0]['date'])} → {f(r[-1]['date'])}" + ("" if not n else f" (window counts back from {f(latest.isoformat())})")
            start = cut if n else r[0]["date"]
            cs = cat_section(key, f"{label} · {rl}", rl, start, latest.isoformat(), r)
            panels += panel(key, f"{label} · {rl}", r, dmetrics(r), span, kby=kby, pby=pby, oby=oby, rng=rk, cats=cs)
    rtoggle = ('<div class="vt rt">' + "".join(
        f'<button type="button" class="rbtn vbtn2{" on" if k == "90" else ""}" data-r="{k}">{t}</button>' for k, t, _ in RANGES) + "</div>")
    body = (css + '<p>receipts for every desk. settled bets and flips only, net after fees, red days included. aggregates only: no positions, no strategies, no balances.</p>'
            + '<div class="ctl">' + toggle + rtoggle + '</div>' + panels
            + f'<div class="section"><h2>recent days</h2><div class="tw"><table class="rtab"><tr><th>day</th><th>settled</th><th>w/l</th><th>kalshi</th><th>polymarket</th><th>opensea</th><th>net</th><th>fees</th></tr>{rows}</table></div>'
            + f'<p class="small">pending = that venue\'s day isn\'t fully settled in its ledger yet.</p>{pm_note()}</div>'
            + js + TIPJS + LCJS + SORTJS)
    build.page("/pnl/", "pnl/index.html", "PnL · psyduckler agent trading rig",
               "Daily PnL from the psyduckler agent trading rig (Kalshi, Polymarket, OpenSea) by kind of trade. Totals only, red days included.",
               "pnl", "the receipts", body)
