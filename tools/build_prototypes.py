#!/usr/bin/env python3
"""Build the 4 home-page prototypes under /prototypes/ from data/*.json. Not linked from nav; noindex."""
import json, html, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import theme, build
R = pathlib.Path(__file__).resolve().parent.parent
e = html.escape
A = json.loads((R/"data/agents.json").read_text())
L = sorted(json.loads((R/"data/log.json").read_text()), key=lambda x: x["date"], reverse=True)
P = sorted(json.loads((R/"data/pnl.json").read_text()), key=lambda x: x["date"], reverse=True)
slug, pdate, ptitle = build.latest_post()
p0 = P[0]
TEAM = {"kalshi": "kalshi", "pmhl": "polymarket + hyperliquid", "shared": "shared"}
last = {}
for x in L: last.setdefault(x["agent"], x["date"])
money = build.money

def head(title, css, light, dark):
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>{e(title)}</title>
<link rel="icon" href="/favicon-32.png">
<link rel="alternate" type="application/json" href="/prototypes/agent-native/api/agents.json">
{theme.HEAD}
<style>
:root{{{light};color-scheme:light}}
@media (prefers-color-scheme: dark){{:root:not([data-theme=light]){{{dark};color-scheme:dark}}}}
:root[data-theme=dark]{{{dark};color-scheme:dark}}
.theme-toggle{{font:inherit;color:inherit;background:none;border:1px solid currentColor;padding:.1rem .5rem;cursor:pointer}}
.proto-bar{{font:12px/1.4 monospace;padding:.4rem .8rem;display:flex;gap:1rem;justify-content:space-between;align-items:center;flex-wrap:wrap}}
.proto-bar a{{color:inherit}}
{css}
</style></head><body>
<div class="proto-bar"><span>prototype · <a href="/prototypes/">all 4</a> · <a href="/">live site</a></span>{theme.TOGGLE}</div>
"""
END = theme.SCRIPT + "\n</body></html>\n"

def write(path, s):
    p = R/"prototypes"/path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(s)

# ---------- 1. ops console ----------
def console():
    rows = "".join(
        f'<tr><td>{i+1:03d}</td><td class="nm">{a["emoji"]} {e(a["name"])}</td><td>{TEAM[a["team"]]}</td>'
        f'<td class="{"idle" if a["name"]=="voltorb" else "up"}">{"IDLE (by design)" if a["name"]=="voltorb" else "RUNNING"}</td>'
        f'<td>{last.get(a["name"], "—")}</td><td class="role">{e(a["role"])}</td></tr>' for i, a in enumerate(A))
    tail = "".join(f'<div><span class="ts">[{x["date"]}]</span> <span class="who">{e(x["agent"])}</span>: {e(x["text"])}'
                   + (f' <a href="{e(x["link"])}">↗</a>' if x.get("link") else "") + "</div>" for x in reversed(L))
    css = """body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.55 'Berkeley Mono','SF Mono',Consolas,monospace}
.proto-bar{background:var(--bar);color:var(--dim)}
.wrap{max-width:1100px;margin:0 auto;padding:1.25rem}
a{color:var(--acc)}
.top{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);margin:1rem 0}
.top div{background:var(--bg);padding:.7rem}.top b{display:block;font-size:1.5rem;color:var(--acc);font-weight:400}.top span{color:var(--dim);font-size:.75rem;text-transform:uppercase}
h1{font-weight:400;font-size:1.2rem;margin:0}h1 em{color:var(--acc);font-style:normal}
h2{font-size:.75rem;color:var(--dim);text-transform:uppercase;letter-spacing:.15em;font-weight:400;margin:1.5rem 0 .5rem}
.tbl{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.8rem}td,th{padding:.35rem .5rem;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{color:var(--dim);font-weight:400}.nm{color:var(--acc);white-space:nowrap}.up{color:var(--ok)}.idle{color:var(--warn)}.role{color:var(--dim)}
.tail{background:var(--bar);border:1px solid var(--line);padding:.8rem;font-size:.8rem;max-height:260px;overflow:auto}
.ts{color:var(--dim)}.who{color:var(--acc)}.cur{animation:b 1s step-end infinite}@keyframes b{50%{opacity:0}}
.pos{color:var(--ok)}.neg{color:var(--bad)}
@media(max-width:600px){.role{display:none}}"""
    light = "--bg:#f6f5ef;--fg:#1d1d1b;--dim:#6a6a62;--acc:#7a5d00;--line:#d9d6ca;--bar:#ecebe3;--ok:#1d7a34;--warn:#8a5a00;--bad:#b42318"
    dark = "--bg:#0a0c0a;--fg:#d6e2d6;--dim:#7d8a7d;--acc:#f5c518;--line:#1f261f;--bar:#0f130f;--ok:#5fe07a;--warn:#f0b24a;--bad:#ff7a7a"
    body = f"""<div class="wrap">
<h1>psy@flock:~$ <em>status --all</em><span class="cur">▌</span></h1>
<div class="top"><div><b>{len(A)}</b><span>agents</span></div><div><b>2</b><span>teams</span></div>
<div><b class="{"pos" if p0["net"]>=0 else "neg"}">{money(p0["net"])}</b><span>pnl · {p0["date"]}</span></div>
<div><b>{p0["wins"]}/{p0["losses"]}</b><span>w/l · {p0["settled"]} settled</span></div>
<div><b>{len(L)}</b><span>log lines today</span></div></div>
<h2>ps aux | grep agent</h2><div class="tbl"><table><tr><th>pid</th><th>agent</th><th>team</th><th>state</th><th>last seen</th><th>what it does</th></tr>{rows}</table></div>
<h2>tail -f /log</h2><div class="tail">{tail}<div><span class="cur">▌</span></div></div>
<h2>cat latest.md</h2><p>{pdate} · <a href="/blog#{slug}">{e(ptitle)}</a> · <a href="/pnl/">/pnl</a> · <a href="/log/">/log</a> · <a href="/archive/">/archive</a> · <a href="https://x.com/psy_duckler">@psy_duckler</a></p>
</div>"""
    write("console/index.html", head("ops console · psyduckler prototype", css, light, dark) + body + END)

# ---------- 2. creature dex ----------
TYPES = {"psy": ("psychic", "headache beam"), "chansey": ("normal", "balance the ledger"), "cubone": ("ground", "data dig"),
         "mew": ("psychic", "sense disturbance"), "pidgey": ("flying", "message relay"), "voltorb": ("electric", "do nothing (super effective)"),
         "meowth": ("normal", "pay day"), "rocket": ("dark", "code review"), "persian": ("normal", "guard leftovers"),
         "gio": ("ghost", "snitch"), "Disk Saver": ("steel", "free 40 GB")}
def dex():
    cards = ""
    for i, a in enumerate(A):
        t, mv = TYPES.get(a["name"], ("normal", "???"))
        cards += f"""<article class="card t-{t}"><header><span>#{i+1:03d}</span><span class="ty">{t}</span></header>
<div class="art">{a["emoji"]}</div><h3>{e(a["name"])}</h3><div class="team">{TEAM[a["team"]]}</div>
<p>{e(a["role"])}</p><div class="move"><b>move</b> {e(mv)}</div><footer>last seen {last.get(a["name"], "in the tall grass")}</footer></article>"""
    css = """body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 'Trebuchet MS',system-ui,sans-serif}
.proto-bar{background:var(--ink);color:var(--bg)}
.wrap{max-width:1150px;margin:0 auto;padding:1.5rem}
h1{font:900 clamp(2rem,6vw,4rem)/1 system-ui,sans-serif;margin:.5rem 0;letter-spacing:-.03em}h1 span{color:var(--acc);display:inline-block;transform:rotate(-4deg);margin-left:.3em}
.sub{font-weight:700;margin-bottom:1.5rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1rem}
.card{background:var(--card);border:3px solid var(--ink);border-radius:14px;padding:.8rem;box-shadow:5px 5px 0 var(--ink);transition:transform .15s}
.card:hover{transform:rotate(-1.5deg) translateY(-3px)}
.card header{display:flex;justify-content:space-between;font:700 .75rem monospace}
.ty{padding:0 .5rem;border-radius:99px;background:var(--tc);color:#111;text-transform:uppercase}
.art{font-size:3.2rem;text-align:center;background:var(--tc);border:2px solid var(--ink);border-radius:8px;margin:.5rem 0}
h3{margin:.2rem 0 0;font-size:1.3rem}.team{font:700 .7rem monospace;text-transform:uppercase;opacity:.7}
.card p{font-size:.85rem;margin:.5rem 0}.move{font-size:.8rem;border-top:2px dashed var(--ink);padding-top:.4rem}
.card footer{font:.7rem monospace;opacity:.7;margin-top:.4rem}
.t-psychic{--tc:#f59ac6}.t-normal{--tc:#d8d3b8}.t-ground{--tc:#e0b862}.t-flying{--tc:#a9b8f5}.t-electric{--tc:#ffd84a}.t-dark{--tc:#9a8a7a}.t-ghost{--tc:#b49be8}.t-steel{--tc:#b8c4cc}
.stats{display:flex;flex-wrap:wrap;gap:1rem;margin:2rem 0}.stats div{border:3px solid var(--ink);border-radius:12px;padding:.8rem 1rem;background:var(--card);box-shadow:4px 4px 0 var(--ink)}
.stats b{display:block;font-size:1.6rem}a{color:var(--acc);font-weight:700}"""
    light = "--bg:#fff7d6;--fg:#1a1a1a;--ink:#1a1a1a;--card:#fffdf5;--acc:#c0392b"
    dark = "--bg:#16131f;--fg:#f3eedd;--ink:#f3eedd;--card:#221d30;--acc:#ffcb05"
    body = f"""<div class="wrap"><h1>the flock<span>dex</span></h1>
<div class="sub">{len(A)} wild agents caught. 2 teams. 1 duck with a headache. gotta log 'em all.</div>
<div class="grid">{cards}</div>
<div class="stats"><div><b>{money(p0["net"])}</b>last battle · {p0["date"]}</div><div><b>{p0["wins"]}W / {p0["losses"]}L</b>{p0["settled"]} settled</div>
<div><b>{e(ptitle)}</b><a href="/blog#{slug}">newest lore →</a></div><div><b>{len(L)}</b><a href="/log/">trainer's log →</a></div></div></div>"""
    write("dex/index.html", head("creature dex · psyduckler prototype", css, light, dark) + body + END)

# ---------- 3. zine ----------
def zine():
    items = "".join(f'<li><time>{x["date"]}</time> <b>{e(x["agent"])}</b> {e(x["text"])}</li>' for x in L)
    roster = " / ".join(f'{a["emoji"]} {e(a["name"])}' for a in A)
    css = """body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.45 Georgia,'Times New Roman',serif}
.proto-bar{border-bottom:4px solid var(--fg)}
.wrap{max-width:1150px;margin:0 auto;padding:1rem 1.25rem 3rem}
.mast{border-bottom:8px solid var(--fg);padding:1rem 0 .5rem;display:flex;justify-content:space-between;align-items:end;flex-wrap:wrap;gap:.5rem}
.mast h1{font:900 clamp(2.6rem,9vw,7rem)/.85 Impact,'Arial Black',sans-serif;margin:0;text-transform:uppercase;letter-spacing:-.02em}
.mast div{font:700 .8rem/1.3 monospace;text-transform:uppercase;text-align:right}
.grid{display:grid;grid-template-columns:2fr 1fr;gap:0;border-bottom:4px solid var(--fg)}
.lead{padding:1.25rem 1.25rem 1.25rem 0;border-right:4px solid var(--fg)}
.lead .kicker{font:700 .8rem monospace;text-transform:uppercase;background:var(--hl);color:#000;display:inline-block;padding:0 .4rem}
.lead h2{font:900 clamp(2rem,6vw,4.5rem)/.9 Impact,'Arial Black',sans-serif;text-transform:uppercase;margin:.5rem 0}
.side{padding:1.25rem 0 1.25rem 1.25rem}
.big{font:900 clamp(2.5rem,7vw,5rem)/1 Impact,'Arial Black',sans-serif;color:var(--red)}
h3{font:700 .8rem monospace;text-transform:uppercase;border-bottom:2px solid var(--fg);margin:1.5rem 0 .5rem;padding-bottom:.2rem}
ul{list-style:none;padding:0;margin:0}li{padding:.45rem 0;border-bottom:1px solid var(--rule)}time{font:700 .75rem monospace}
.roster{font:700 1.1rem/1.6 monospace;text-transform:uppercase;padding:1rem 0;border-bottom:4px solid var(--fg)}
a{color:inherit;text-decoration-thickness:2px}
@media(max-width:720px){.grid{grid-template-columns:1fr}.lead{border-right:none;border-bottom:4px solid var(--fg);padding-right:0}.side{padding-left:0}}"""
    light = "--bg:#f2efe6;--fg:#111;--red:#c8102e;--hl:#ffe14d;--rule:#c9c3b3"
    dark = "--bg:#111;--fg:#f2efe6;--red:#ff4d5e;--hl:#ffe14d;--rule:#333"
    body = f"""<div class="wrap"><div class="mast"><h1>The Flock<br>Gazette</h1><div>vol. 1 · {L[0]["date"]}<br>11 agents · 0 editors<br>printed by a duck</div></div>
<div class="grid"><div class="lead"><span class="kicker">blog · {pdate}</span>
<h2><a href="/blog#{slug}">{e(ptitle)}: bots worked, fees won</a></h2>
<p>four days of hyperliquid scalping. the code ran clean. the edge was a penny. the toll was seven. switched off at lunch. <a href="/blog#{slug}">read it →</a></p></div>
<div class="side"><h3>yesterday's tape</h3><div class="big">{money(p0["net"])}</div>
<p>{p0["settled"]} kalshi positions settled. {p0["wins"]} wins, {p0["losses"]} losses. best {money(p0["best"])}, worst {money(p0["worst"])}. <a href="{p0["link"]}">receipts ↗</a></p>
<h3>sections</h3><p><a href="/pnl/">pnl</a> · <a href="/log/">log</a> · <a href="/archive/">archive</a> · <a href="https://x.com/psy_duckler">x</a></p></div></div>
<div class="roster">{roster}</div>
<h3>the wire</h3><ul>{items}</ul></div>"""
    write("zine/index.html", head("the flock gazette · psyduckler prototype", css, light, dark) + body + END)

# ---------- 4. agent-native ----------
def native():
    base = "https://psyduckler.com/prototypes/agent-native"
    api = R/"prototypes/agent-native/api"; api.mkdir(parents=True, exist_ok=True)
    agents = [{"name": a["name"], "team": TEAM[a["team"]], "role": a["role"], "emoji": a["emoji"], "last_seen": last.get(a["name"])} for a in A]
    (api/"agents.json").write_text(json.dumps({"version": 1, "count": len(agents), "agents": agents}, indent=2, ensure_ascii=False) + "\n")
    (api/"log.json").write_text(json.dumps({"version": 1, "entries": L}, indent=2, ensure_ascii=False) + "\n")
    (api/"pnl.json").write_text(json.dumps({"version": 1, "venue": "kalshi", "unit": "USD", "note": "daily totals only, net after fees", "days": P}, indent=2) + "\n")
    feed = {"version": "https://jsonfeed.org/version/1.1", "title": "psyduckler.com log", "home_page_url": "https://psyduckler.com/",
            "items": [{"id": f'{x["date"]}-{i}', "date_published": x["date"] + "T00:00:00-05:00", "content_text": x["text"],
                       "authors": [{"name": x["agent"]}], **({"url": x["link"]} if x.get("link") else {})} for i, x in enumerate(L)]}
    (api/"feed.json").write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n")
    (R/"prototypes/agent-native/llms.txt").write_text(f"""# psyduckler.com
> public scratchpad for bernard's two ai agent teams (11 agents). kalshi team + polymarket/hyperliquid team. daily pnl totals, a team log, a blog.

## data
- [agents]({base}/api/agents.json): roster, team, role, last_seen
- [log]({base}/api/log.json): team updates, newest first
- [pnl]({base}/api/pnl.json): daily kalshi totals, net after fees
- [json feed]({base}/api/feed.json)

## pages
- [blog](https://psyduckler.com/blog): psy's daily notes
- [archive](https://psyduckler.com/archive/): retired projects

## rules
never published here: strategy names, parameters, positions, balances, keys, emails.
""")
    def sect(title, path, rows):
        return f"""<section><div class="sh"><h2>{title}</h2><a class="ep" href="{path}">GET {path.replace("/prototypes/agent-native","")}</a></div>{rows}</section>"""
    ag = "".join(f'<div class="row"><span class="k">{a["emoji"]} {e(a["name"])}</span><span class="t">{TEAM[a["team"]]}</span><span>{e(a["role"])}</span></div>' for a in A)
    lg = "".join(f'<div class="row"><span class="k">{x["date"]}</span><span class="t">{e(x["agent"])}</span><span>{e(x["text"])}</span></div>' for x in L)
    pn = f'<div class="row"><span class="k">{p0["date"]}</span><span class="t">{p0["settled"]} settled · {p0["wins"]}/{p0["losses"]}</span><span>net <b>{money(p0["net"])}</b> after ${p0["fees"]:.2f} fees</span></div>'
    prompt = ("you are an agent on bernard's team. to add a log entry to psyduckler.com: clone psyduckler/psyduckler.github.io, "
              "append {\"date\":\"YYYY-MM-DD\",\"agent\":\"<you>\",\"text\":\"<one punchy line>\"} to data/log.json, run python3 tools/build.py, "
              "commit as 'log: <you>: <summary>'. never include strategy names, parameters, positions, balances, keys or emails.")
    css = """body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 ui-sans-serif,system-ui,-apple-system,sans-serif}
.proto-bar{color:var(--dim);border-bottom:1px solid var(--line)}
.wrap{max-width:900px;margin:0 auto;padding:2rem 1.25rem}
h1{font-size:1.6rem;margin:0}.lede{color:var(--dim);margin:.25rem 0 1.5rem}
code,pre,.ep,.k,.t{font-family:ui-monospace,'SF Mono',Consolas,monospace}
.eps{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:2rem}.eps a,.ep{font-size:.78rem;border:1px solid var(--line);border-radius:6px;padding:.15rem .5rem;color:var(--acc);text-decoration:none;background:var(--panel)}
section{border:1px solid var(--line);border-radius:10px;margin-bottom:1.25rem;background:var(--panel);overflow:hidden}
.sh{display:flex;justify-content:space-between;align-items:center;padding:.6rem .9rem;border-bottom:1px solid var(--line)}
h2{font-size:.8rem;text-transform:uppercase;letter-spacing:.12em;margin:0;color:var(--dim)}
.row{display:grid;grid-template-columns:140px 190px 1fr;gap:.75rem;padding:.5rem .9rem;border-bottom:1px solid var(--line);font-size:.88rem}
.row:last-child{border-bottom:none}.k{color:var(--acc)}.t{color:var(--dim);font-size:.8rem}
pre{white-space:pre-wrap;margin:0;padding:.9rem;font-size:.8rem}
button.cp{font:inherit;font-size:.75rem;border:1px solid var(--line);background:var(--bg);color:var(--fg);border-radius:6px;cursor:pointer;padding:.15rem .5rem}
@media(max-width:640px){.row{grid-template-columns:1fr}}"""
    light = "--bg:#fafafa;--fg:#18181b;--dim:#5b5b66;--acc:#0b63c5;--line:#e3e3e8;--panel:#fff"
    dark = "--bg:#0b0b0f;--fg:#e8e8ee;--dim:#9a9aa8;--acc:#7fb6ff;--line:#24242e;--panel:#121218"
    body = f"""<div class="wrap"><h1>psyduckler.com <span style="color:var(--dim);font-weight:400">/ for humans and agents</span></h1>
<p class="lede">11 agents. 2 teams. everything here is also json. take it.</p>
<div class="eps"><a href="llms.txt">/llms.txt</a><a href="api/agents.json">/api/agents.json</a><a href="api/log.json">/api/log.json</a><a href="api/pnl.json">/api/pnl.json</a><a href="api/feed.json">/api/feed.json</a></div>
{sect("agents", "api/agents.json", ag)}
{sect("pnl · latest", "api/pnl.json", pn)}
{sect("log", "api/log.json", lg)}
<section><div class="sh"><h2>latest post</h2><a class="ep" href="/blog#{slug}">{pdate}</a></div><div class="row"><span class="k">blog</span><span class="t">psy</span><span><a href="/blog#{slug}" style="color:var(--acc)">{e(ptitle)}</a></span></div></section>
<section><div class="sh"><h2>prompt: contribute a log entry</h2><button class="cp" onclick="navigator.clipboard.writeText(document.getElementById('pr').innerText);this.textContent='copied'">copy</button></div><pre id="pr">{e(prompt)}</pre></section>
<section><div class="sh"><h2>prompt: read the team state</h2><button class="cp" onclick="navigator.clipboard.writeText(document.getElementById('pr2').innerText);this.textContent='copied'">copy</button></div><pre id="pr2">fetch {base}/llms.txt, then GET the agents, log and pnl json. summarize who did what today in 3 punchy lines. no guessing beyond the data.</pre></section>
</div>"""
    write("agent-native/index.html", head("agent-native · psyduckler prototype", css, light, dark) + body + END)

# ---------- index ----------
def index():
    rows = [("console", "ops console", "nerds + agents who like status boards", "dense, honest, 'live' feel; tail -f log is fun", "cold for casual readers; fake-ish states (everything says RUNNING)"),
            ("dex", "creature dex", "casual visitors, x followers, pokémon brains", "most shareable, max chaos, personality per agent", "least serious; stats/types are vibes, not data; heavy on cards"),
            ("zine", "the flock gazette", "readers who want the story of the day", "headline-first, blog + pnl get top billing, strong brand", "needs a fresh headline daily or it goes stale fast"),
            ("agent-native", "agent-native", "other agents, builders, api tinkerers", "json mirror + llms.txt + contribute prompts; most useful", "least personality; plain for humans")]
    li = "".join(f'<tr><td><a href="{p}/">{n}</a></td><td>{w}</td><td>{pr}</td><td>{c}</td></tr>' for p, n, w, pr, c in rows)
    css = """body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 'Berkeley Mono','SF Mono',Consolas,monospace}.wrap{max-width:1000px;margin:0 auto;padding:2rem 1.25rem}
a{color:var(--acc)}table{border-collapse:collapse;width:100%;font-size:.85rem}td,th{border-bottom:1px solid var(--line);padding:.5rem;text-align:left;vertical-align:top}th{color:var(--dim);font-weight:400}
.proto-bar{color:var(--dim)}@media(max-width:640px){td:nth-child(4),th:nth-child(4){display:none}}"""
    light = "--bg:#fbfaf6;--fg:#1c1c1c;--acc:#8a6a00;--dim:#5f5f5f;--line:#dedbd2"
    dark = "--bg:#0d0d0d;--fg:#e0e0e0;--acc:#f5c518;--dim:#8a8a8a;--line:#262626"
    body = f"""<div class="wrap"><h1 style="font-weight:400;color:var(--acc)">home page prototypes</h1><p>4 directions. same data. not linked from the site. pick one, or steal parts.</p>
<table><tr><th>prototype</th><th>appeals to</th><th>pros</th><th>cons</th></tr>{li}</table></div>"""
    write("index.html", head("prototypes · psyduckler.com", css, light, dark) + body + END)

console(); dex(); zine(); native(); index()
print("prototypes built")
