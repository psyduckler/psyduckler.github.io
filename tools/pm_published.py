#!/usr/bin/env python3
"""RETIRED 2026-10-31: /pnl/ now comes from the trading console. Run: python3 tools/console.py update && python3 tools/build.py

Polymarket settled ledger as PUBLISHED by Bernard's dashboard (the numbers its /pm/ board and Overview show). Aggregates only.

Meowth's R2 release (pm-private private/polymarket/psyslo/releases/latest.json) stopped at 2026-10-13 03:25Z. Since
2026-10-22 every dashboard update (Bernard's Mac; slots 07:30, 10:30, 12:45, then hourly 14:00-22:00 CT) writes
pub/pm_ledger.json into the dashboard's Tokay repo (project prediction-markets, repo kalshi-dashboard). It is not served
over HTTP; read it from the repo's current snapshot with the Tokay MCP token.

Schema dash/pm-ledger@1:
  complete_through  last fully settled CT day (the day before the pull's CT day); days/rows stop there
  days         [{date, n, w, l, net, fees, gw, gl, best, worst}]   same shape as pnl_history.json["polymarket"]
  rows         [{d, c, n, w, l, net, gw, gl}]   day x category (copy, crypto, wx_high, wx_low, wx_rain, manual);
               a day's row cents sum to its day cents exactly
  ticket_hist  {nw, sw, nl, sl, hist, clipped, lo, hi}   same shape as pnl_history.json["psum"]
  totals {days, settled, net}    partial [{date, n, net}] = today so far (not in days/rows)

Token: the same Tokay MCP token as opensea_ledger.py, read at runtime; never printed or committed.

Usage: python3 tools/pm_published.py      print daily totals + freshness (no writes)
"""
import json, datetime as dt
import opensea_ledger as O

# Tokay Repo node of the dashboard (kalshi-dashboard, project prediction-markets). Stable across pushes.
REPO = "WyJSZXBvIiwiMDFhMTNjMzYtNjExZC03Y2E5LTg0YWEtODk2NDE0Zjc4ZDJkIiwiMDFhMTNiZTgtODEzZC03ZTQxLWE2ODAtNzM2MmEzZjViZWRmIl0="
PATH = "pub/pm_ledger.json"
MAX_AGE_H = 36   # the Mac pulls 07:30..22:00 CT; older than this means its updates stopped
Q = "query R($id: ID!) { node(id: $id) { ... on Repo { currentSourceSnapshot { id commitHash createdAt } } } }"
C = lambda x: int(round(x * 100))


def fetch(m=None):
    """-> (doc, commit). Refuses a file that is cut off, inconsistent, or from a pull more than MAX_AGE_H old."""
    m = m or O.MCP()
    snap = m.call("query_platform_graphql", {"source": Q, "operationName": "R", "variables": {"id": REPO}})
    s = snap["data"]["node"]["currentSourceSnapshot"]
    got = m.call("read_repo_files", {"repoSourceSnapshotId": s["id"], "files": [{"path": PATH}], "maxTotalBytes": 524288})
    f = (got.get("files") or [{}])[0]
    if "content" not in f:
        raise RuntimeError(f"{PATH} not readable at {s['commitHash'][:8]}: {str(f)[:200]}")
    if f.get("sizeBytes") is not None and f["sizeBytes"] != len(f["content"].encode()):
        raise RuntimeError(f"{PATH} cut off: {len(f['content'].encode())} of {f['sizeBytes']} bytes")
    doc = json.loads(f["content"])
    if doc.get("schema") != "dash/pm-ledger@1":
        raise RuntimeError(f"unexpected schema {doc.get('schema')}")
    per = {}
    for r in doc["rows"]:
        per[r["d"]] = per.get(r["d"], 0) + C(r["net"])
    for d in doc["days"]:
        if per.pop(d["date"], None) != C(d["net"]):
            raise RuntimeError(f"{d['date']}: category rows != day net")
    if per or sum(d["n"] for d in doc["days"]) != doc["totals"]["settled"]:
        raise RuntimeError("rows / totals do not match days")
    pulled = dt.datetime.fromisoformat(doc["pulled_to_utc"].replace("Z", "+00:00"))
    age_h = (dt.datetime.now(dt.timezone.utc) - pulled).total_seconds() / 3600
    if age_h > MAX_AGE_H:
        raise RuntimeError(f"published PM ledger is stale: pulled {doc['pulled_to_utc']} ({age_h:.1f} h old)")
    return doc, s["commitHash"]


if __name__ == "__main__":
    doc, commit = fetch()
    for d in doc["days"]:
        print(d["date"], d["n"], f"{d['net']:+.2f}")
    print("pulled", doc["pulled_to_utc"], "complete through", doc["complete_through"], "net", doc["totals"]["net"],
          "settled", doc["totals"]["settled"], "commit", commit[:8])
