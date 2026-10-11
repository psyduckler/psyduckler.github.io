"""Shared light/dark theme for every page on psyduckler.com.

build.py uses THEME_CSS / HEAD / TOGGLE / SCRIPT directly.
apply(html) retrofits a hand-written page (blog.html, 404.html) idempotently.
Run `python3 tools/theme.py` to re-apply to blog.html and 404.html.
"""
import re, pathlib

DARK = "--bg:#0d0d0d;--fg:#e0e0e0;--accent:#f5c518;--link:#f5c518;--muted:#8a8a8a;--border:#262626;--border-soft:#1a1a1a;--card:#121212;--code-bg:#1a1a1a;--pos:#7ccf6a;--neg:#ef7b7b"
LIGHT = "--bg:#fbfaf6;--fg:#1c1c1c;--accent:#8a6a00;--link:#8a6a00;--muted:#5f5f5f;--border:#dedbd2;--border-soft:#ebe8e0;--card:#ffffff;--code-bg:#efece4;--pos:#1d7a34;--neg:#b42318"

THEME_CSS = (
    f":root{{{DARK};color-scheme:dark}}"
    f"@media (prefers-color-scheme: light){{:root:not([data-theme=dark]){{{LIGHT};color-scheme:light}}}}"
    f":root[data-theme=light]{{{LIGHT};color-scheme:light}}"
    ":root[data-theme=dark]{color-scheme:dark}"
    "code{background:var(--code-bg);padding:0 .25em;font-size:.9em}"
    ".theme-toggle{font:inherit;font-size:.85rem;color:var(--muted);background:none;border:none;border-bottom:1px solid transparent;cursor:pointer;padding:0}"
    ".theme-toggle:hover{color:var(--accent);border-bottom-color:var(--accent)}"
)

HEAD = ('<meta name="color-scheme" content="light dark">\n'
        '  <script>try{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}</script>')

TOGGLE = '<button type="button" class="theme-toggle" id="theme-toggle" aria-label="color theme: system">◐ system</button>'

SCRIPT = ("<script>(function(){var b=document.getElementById('theme-toggle');if(!b)return;"
          "var m=['system','light','dark'],i={system:'◐',light:'☀',dark:'☾'};"
          "function cur(){try{return localStorage.getItem('theme')||'system'}catch(e){return 'system'}}"
          "function show(t){b.textContent=i[t]+' '+t;b.setAttribute('aria-label','color theme: '+t)}"
          "show(cur());b.onclick=function(){var t=m[(m.indexOf(cur())+1)%3];"
          "try{t==='system'?localStorage.removeItem('theme'):localStorage.setItem('theme',t)}catch(e){}"
          "if(t==='system')delete document.documentElement.dataset.theme;else document.documentElement.dataset.theme=t;show(t)}})();</script>")

HEX = {"#0d0d0d": "var(--bg)", "#e0e0e0": "var(--fg)", "#f5c518": "var(--accent)", "#666": "var(--muted)",
       "#1a1a1a": "var(--border)", "#141414": "var(--border-soft)"}

def apply(html):
    html = re.sub(r'\s*<!-- theme:start -->.*?<!-- theme:end -->', '', html, flags=re.S)
    html = re.sub(r'\s*<script id="theme-script">.*?</script>', '', html, flags=re.S)
    html = re.sub(r'<button type="button" class="theme-toggle".*?</button>', '', html, flags=re.S)
    def fix_style(m):
        css = re.sub(r':root\s*\{[^}]*\}', '', m.group(0), count=1)
        for k, v in HEX.items():
            css = re.sub(re.escape(k) + r'\b', v, css)
        return css
    html = re.sub(r'<style>.*?</style>', fix_style, html, count=1, flags=re.S)
    html = html.replace('</head>', f'  <!-- theme:start -->\n  {HEAD}\n  <style>{THEME_CSS}</style>\n  <!-- theme:end -->\n</head>', 1)
    if '<nav>' in html:
        html = re.sub(r'</nav>', TOGGLE + '</nav>', html, count=1)
    else:
        html = html.replace('<body>', '<body>\n  <nav style="position:absolute;top:1rem;right:1.25rem">' + TOGGLE + '</nav>', 1)
    html = html.replace('</body>', f'<script id="theme-script">{SCRIPT[8:]}\n</body>', 1)
    return html

if __name__ == "__main__":
    root = pathlib.Path(__file__).resolve().parent.parent
    for n in ("blog.html", "404.html"):
        p = root / n
        p.write_text(apply(p.read_text()))
    print("theme applied")
