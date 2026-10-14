"""The live /pnl/ page: equity curve + stat strip, daily bars + calendar heatmap,
recent rows and a Polymarket section, with a combined / kalshi / polymarket toggle.
Data: data/pnl_history.json (aggregates only). Called from tools/build.py."""
import build_pnl_versions as V
import build

def strip(M):
    s = V.stat
    return (f'<div class="strip">{s("total net", V.money(M["net"]), V.cls(M["net"]))}{s("win rate", f"{M["wr"]:.1f}%")}'
            f'{s("profit factor", f"{M["pf"]:.2f}")}{s("best day", V.money(M["best"]), "pos")}{s("worst day", V.money(M["worst"]), "neg")}'
            f'{s("max drawdown", V.money(M["dd"]), "neg")}{s("sharpe-ish", f"{M["sharpe"]:.2f}")}{s("settled", f"{M["trades"]:,}")}'
            f'{s("fees", f"${M["fees"]:,.2f}")}{s("green days", f"{M["green"]}/{M["days"]}")}</div>')

def panel(key, label, days, M, span):
    return (f'<div class="view" data-view="{key}"{"" if key == "all" else " hidden"}>'
            f'<div class="section"><h2>{label} · equity</h2>{strip(M)}{V.line([M["curve"]])}'
            f'<p class="small">{span}. net after fees. max drawdown is peak-to-trough on the running total.</p></div>'
            f'<div class="section"><h2>{label} · daily net</h2>{V.bars([d["net"] for d in days])}'
            f'<p>{M["green"]} green days, {M["days"] - M["green"]} red. best {V.money(M["best"])}, worst {V.money(M["worst"])}.</p></div>'
            f'<div class="section"><h2>{label} · calendar</h2>{V.heatmap(days)}<p class="small">brighter = bigger. grey = nothing settled. mon at top.</p></div></div>')

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
    return ('<h2 style="margin-top:1.5rem">daily totals · polymarket</h2><table><tr><th>day</th><th>settled</th><th>w/l</th>'
            f'<th>net</th><th>fees</th><th>best</th><th>worst</th></tr>{rows}</table>')

def render(H_meta):
    K, P, A = V.K, V.P, V.ALLD
    f = V.f
    kby = {d["date"]: d for d in K}; pby = {d["date"]: d for d in P}
    rows = ""
    for d in reversed(A[-10:]):
        k, p = kby.get(d["date"]), pby.get(d["date"])
        cell = lambda x: f'<td class="{V.cls(x["net"])}">{V.money(x["net"])}</td>' if x else "<td>–</td>"
        rows += (f'<tr><td>{f(d["date"])}</td><td>{d["n"]}</td><td>{d["w"]}/{d["l"]}</td>{cell(k)}{cell(p)}'
                 f'<td class="{V.cls(d["net"])}">{V.money(d["net"])}</td><td>${d["fees"]:,.2f}</td></tr>')
    toggle = ('<div class="vt" role="tablist">' + "".join(
        f'<button type="button" class="vbtn{" on" if k == "all" else ""}" data-v="{k}">{t}</button>'
        for k, t in (("all", "combined"), ("k", "kalshi"), ("p", "polymarket"))) + "</div>")
    js = ("<script>document.querySelectorAll('.vbtn').forEach(function(b){b.onclick=function(){"
          "document.querySelectorAll('.vbtn').forEach(function(x){x.classList.toggle('on',x===b)});"
          "document.querySelectorAll('.view').forEach(function(v){v.hidden=v.dataset.view!==b.dataset.v})}})</script>")
    css = ('<style>' + V.EXTRA + '.vt{margin:0 0 1.5rem}.vbtn{font:inherit;font-size:.8rem;background:none;color:var(--muted);border:1px solid var(--border);padding:.25rem .7rem;margin-right:.4rem;cursor:pointer}'
           '.vbtn.on{color:var(--accent);border-color:var(--accent)}</style>')
    MP = V.MP
    body = (css + '<p>receipts for both teams. settled bets only, net after fees, red days included. aggregates only: no positions, no strategies, no balances.</p>'
            + toggle
            + panel("all", "combined", A, V.MA, f"kalshi {f(K[0]['date'])} → {f(K[-1]['date'])}, polymarket {f(P[0]['date'])} → {f(P[-1]['date'])}")
            + panel("k", "kalshi", K, V.MK, f"{f(K[0]['date'])} → {f(K[-1]['date'])}")
            + panel("p", "polymarket", P, MP, f"{f(P[0]['date'])} → {f(P[-1]['date'])}")
            + f'<div class="section"><h2>recent days</h2><table><tr><th>day</th><th>settled</th><th>w/l</th><th>kalshi</th><th>polymarket</th><th>net</th><th>fees</th></tr>{rows}</table></div>'
            + f'<div class="section"><h2>polymarket · the new desk</h2><p>polymarket started {f(P[0]["date"])}. {MP["trades"]:,} bets settled through {f(P[-1]["date"])}, '
              f'net <span class="{V.cls(MP["net"])}">{V.money(MP["net"])}</span> after ${MP["fees"]:,.2f} fees, {MP["wr"]:.1f}% win rate. small wins, slightly bigger losses. tuition.</p>'
              + pm_table(P) + f'<p class="small">{H_meta}</p></div>' + js)
    build.page("/pnl/", "pnl/index.html", "PnL · Bernard's Grok Bot team",
               "Daily prediction-market PnL from Bernard's Grok Bot teams (Kalshi + Polymarket). Totals only, red days included.",
               "pnl", "the receipts", body)
