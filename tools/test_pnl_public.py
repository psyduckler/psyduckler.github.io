#!/usr/bin/env python3
"""Checks for the public /pnl/ refresh. Metrics are the published ones, not recomputed.

Run from the repo root: python3 tools/test_pnl_public.py
"""
import json, sys, datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build
import pnl_main as pm

PUB = json.loads((ROOT / "data/pnl_public.json").read_text())
HTML = (ROOT / "pnl/index.html").read_text()
PAY = {"all": "all", "k": "kalshi", "p": "pm", "h": "hl", "o": "os", "e": "eq"}
RANGE = {"all": "all", "90": "90d", "30": "30d", "7": "7d"}
FORBIDDEN = ("tokay.io", "tokay.app", "bearer", "console_url", "api_key", "secret", "wallet", "ticker", "0x")
TODAY = PUB["source_today"]
VENUE_ONLY = ["kalshi", "pm", "hl", "os", "eq"]


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
    # last view has no following panel; stop before the page-level source note
    if j < 0:
        k = HTML.find('<p class="small pmnote">', i)
        j = k if k > 0 else None
    return HTML[i:j if j else None]


def main():
    today_ct = dt.datetime.now(ZoneInfo("America/Chicago")).date().isoformat()
    if TODAY != today_ct:
        fail(f"source today {TODAY} != {today_ct}")
    expected = {f"{w}:{v}" for w in PUB["windows"] for v in PUB["venues"]}
    if set(PUB["responses"]) != expected:
        fail(f"expected {len(expected)} window x venue blocks, got {len(PUB['responses'])}")
    if "eq" not in PUB["venues"] or "robinhood" not in HTML.lower():
        fail("missing robinhood venue")
    if 'data-v="e"' not in HTML or "robinhood" not in HTML:
        fail("missing robinhood tab")
    if "today is left out" in HTML:
        fail("page still says today is left out")
    if "today, not final" not in HTML:
        fail("missing today, not final")
    if "NaN" in HTML:
        fail("page contains NaN")
    for bad in FORBIDDEN:
        blob = (ROOT / "data/pnl_public.json").read_text().lower()
        if bad in blob:
            fail(f"pnl_public.json contains {bad}")
        if bad in ("tokay.io", "tokay.app", "bearer", "console_url", "api_key", "secret"):
            if bad in HTML.lower():
                fail(f"pnl html contains {bad}")

    # venue combined nets sum to all-venue combined net (rounding)
    for window in PUB["windows"]:
        parts = [PUB["responses"][f"{window}:{v}"]["combined"]["net"] for v in VENUE_ONLY]
        alln = PUB["responses"][f"{window}:all"]["combined"]["net"]
        if abs(round(sum(parts), 2) - alln) > 0.05:
            fail(f"{window} venue sum {round(sum(parts), 2)} vs all {alln}")
        # every category on venue=all appears in the combined view
        block = view_block(window, "all")
        for cat in PUB["responses"][f"{window}:all"]["categories"]:
            if cat["label"].lower() not in block:
                fail(f"{window}:all dropped label {cat['label']}")
            for v in cat.get("venues") or []:
                chip = {"kalshi": "kalshi", "pm": "pm", "hl": "hl", "os": "opensea", "eq": "robinhood"}[v]
                # badge is on the row; search nearby after the label
                if chip not in block:
                    fail(f"{window}:all missing {chip} badge for {cat['label']}")

    for key, resp in PUB["responses"].items():
        window, venue = key.split(":")
        comb = resp["combined"]
        series = comb["series"] or []
        block = view_block(window, venue)
        cat_sum = round(sum(c["net"] for c in resp["categories"]), 2)
        # compare integer cents: 1307.37 vs 1307.4 is 3¢, but abs(float) can be just over 0.03
        if abs(int(round(cat_sum * 100)) - int(round(comb["net"] * 100))) > 3:
            fail(f"{key} category sum {cat_sum} vs net {comb['net']}")
        if not series:
            if comb.get("days") or comb.get("net"):
                fail(f"{key} totals without a series")
            if venue == "eq":
                if "no settled robinhood trades yet." not in block:
                    fail(f"{key} missing empty robinhood state")
            elif "nothing settled in this window." not in block:
                fail(f"{key} missing empty state")
            if "today, not final" in block:
                fail(f"{key} empty view claimed a today point")
            if "NaN" in block or "None" in block:
                fail(f"{key} empty view leaked a null")
            continue
        if series[-1][0] != TODAY or resp["to"] != TODAY or resp["today"] != TODAY:
            fail(f"{key} does not keep today")
        if series[-1][2] != comb["net"]:
            fail(f"{key} headline {comb['net']} != last running {series[-1][2]}")
        if len(series) != comb["days"]:
            fail(f"{key} series length != days")
        cls = "pos" if comb["net"] >= 0 else "neg"
        needle = f'<b class="{cls}">{build.money(comb["net"])}</b><span>total net</span>'
        if needle not in block:
            fail(f"{key} headline html missing {needle}")
        # published net, not a fresh sum of day nets, when those differ
        day_sum = round(sum(n for _d, n, _r in series), 2)
        if abs(day_sum - comb["net"]) > 0.005:
            other = build.money(day_sum)
            headline = build.money(comb["net"])
            if other != headline and other in block and needle.replace(headline, other) in block:
                fail(f"{key} published the recomputed day-net sum {other}")
        if comb["sharpe"] is None:
            if "—" not in block:
                fail(f"{key} null sharpe not shown")
        elif f'{comb["sharpe"]:.2f}' not in block:
            fail(f"{key} sharpe {comb['sharpe']} not on the page")
        if "today, not final" not in block or build.fmt_date(TODAY).lower() not in block.lower():
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

    # basketball now includes hyperliquid on the combined all-time view
    all_all = view_block("all", "all")
    if "basketball" not in all_all or "hl" not in all_all:
        fail("combined all missing basketball or hl badge")

    empty = pm.view_html("e", "robinhood", "7", "7d", {
        "window": "7d", "venue": "eq", "today": TODAY, "from": None, "to": None,
        "combined": {"net": 0, "days": 0, "day_wins": 0, "winrate": None, "avg_day": None,
                     "best_day": None, "worst_day": None, "sharpe": None, "series": []},
        "categories": [],
    }, {})
    if "no settled robinhood trades yet." not in empty:
        fail("empty robinhood view did not render")
    if "today, not final" in empty:
        fail("empty robinhood view claimed a today point")
    try:
        pm.view_html("o", "opensea", "7", "7d", {
            "window": "7d", "venue": "os", "today": TODAY, "from": "2026-11-06", "to": TODAY,
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
