#!/usr/bin/env python3
"""Checks for the public /pnl/ refresh. Metrics are the published ones, not recomputed.

Run from the repo root: python3 tools/test_pnl_public.py
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build
import pnl_main as pm

PUB = json.loads((ROOT / "data/pnl_public.json").read_text())
HTML = (ROOT / "pnl/index.html").read_text()
PAY = {"all": "all", "k": "kalshi", "p": "pm", "h": "hl", "o": "os"}
RANGE = {"all": "all", "90": "90d", "30": "30d", "7": "7d"}
FORBIDDEN = ("tokay.io", "bearer", "console_url", "api_key", "secret", "wallet", "ticker", "0x")


def fail(msg):
    print("FAIL", msg)
    raise SystemExit(1)


def view_block(window, venue):
    key = next(k for k, v in PAY.items() if v == venue)
    rng = next(k for k, v in RANGE.items() if v == window)
    needle = f'data-view="{key}" data-range="{rng}"'
    i = HTML.find(needle)
    if i < 0:
        fail(f"missing view {window}:{venue}")
    j = HTML.find('<div class="view"', i + len(needle))
    return HTML[i:j if j > 0 else None]


def main():
    if PUB["source_today"] != "2026-11-11":
        fail("source today")
    if set(PUB["responses"]) != {f"{w}:{v}" for w in PUB["windows"] for v in PUB["venues"]}:
        fail("expected 20 window x venue blocks")
    if "today is left out" in HTML:
        fail("page still says today is left out")
    if "today, not final" not in HTML:
        fail("missing today, not final")
    for bad in FORBIDDEN:
        blob = (ROOT / "data/pnl_public.json").read_text().lower()
        if bad in blob:
            fail(f"pnl_public.json contains {bad}")

    for key, resp in PUB["responses"].items():
        window, venue = key.split(":")
        comb = resp["combined"]
        series = comb["series"]
        block = view_block(window, venue)
        if series[-1][0] != "2026-11-11" or resp["to"] != "2026-11-11" or resp["today"] != "2026-11-11":
            fail(f"{key} does not keep today")
        if series[-1][2] != comb["net"]:
            fail(f"{key} headline {comb['net']} != last running {series[-1][2]}")
        if len(series) != comb["days"]:
            fail(f"{key} series length != days")
        cat_sum = round(sum(c["net"] for c in resp["categories"]), 2)
        if abs(cat_sum - comb["net"]) > 0.03:
            fail(f"{key} category sum {cat_sum} vs net {comb['net']}")
        cls = "pos" if comb["net"] >= 0 else "neg"
        needle = f'<b class="{cls}">{build.money(comb["net"])}</b><span>total net</span>'
        if needle not in block:
            fail(f"{key} headline html missing {needle}")
        if comb["sharpe"] is None:
            if "—" not in block:
                fail(f"{key} null sharpe not shown")
        elif f'{comb["sharpe"]:.2f}' not in block:
            fail(f"{key} sharpe {comb['sharpe']} not on the page")
        if "today, not final" not in block or "nov 11, 2026" not in block:
            fail(f"{key} missing today disclosure or central date")
        if "(central)" not in block:
            fail(f"{key} date range is not labeled central")
        for cat in resp["categories"]:
            if cat["label"].lower() not in block:
                fail(f"{key} dropped label {cat['label']}")
            if cat["sharpe"] is None and cat["days"] < 2 and "—" not in block:
                fail(f"{key} {cat['label']} null sharpe")
            if cat["days"] and not cat["series"]:
                fail(f"{key} {cat['label']} totals without series")

    all_all = view_block("all", "all")
    for text in ("+$443.60", "+$226.94", "+$435.60", "+$5,280.41", "+$4,844.80", "-$1,456.98",
                 "nov 9, 2026", "nov 10, 2026", "deadlines", "macro · fed", "cpi"):
        if text not in all_all:
            fail(f"combined all missing {text}")
    if "+$5,280.43" in all_all:
        fail("combined all published the recomputed day-net sum")
    hl7 = view_block("7d", "hl")
    if ">1.32<" not in hl7 and "1.32" not in hl7:
        fail("7d hyperliquid sharpe was recomputed")
    if ">1.33<" in hl7:
        fail("7d hyperliquid shows recomputed sharpe 1.33")
    # a zero-settlement view must render without inventing a today point
    empty = pm.view_html("o", "opensea", "7", "7d", {
        "window": "7d", "venue": "os", "today": "2026-11-11", "from": "2026-11-11", "to": "2026-11-11",
        "combined": {"net": 0, "days": 0, "day_wins": 0, "winrate": None, "avg_day": 0,
                     "best_day": 0, "worst_day": 0, "sharpe": None, "series": []},
        "categories": [],
    }, {})
    if "nothing settled in this window." not in empty:
        fail("empty view did not render")
    if "today, not final" in empty:
        fail("empty view claimed a today point")
    try:
        pm.view_html("o", "opensea", "7", "7d", {
            "window": "7d", "venue": "os", "today": "2026-11-11", "from": "2026-11-05", "to": "2026-11-11",
            "combined": {"net": 1, "days": 1, "day_wins": 1, "winrate": 100, "avg_day": 1,
                         "best_day": 1, "worst_day": 1, "sharpe": None, "series": []},
            "categories": [],
        }, {})
    except SystemExit:
        pass
    else:
        fail("totals without a series were accepted")
    print("ok", len(PUB["responses"]), "views")


if __name__ == "__main__":
    main()
