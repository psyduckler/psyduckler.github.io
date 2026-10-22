#!/usr/bin/env python3
"""OpenSea (NFT flips) ledger as PUBLISHED by the Tokay opensea-ledger job. Aggregates only.

Since 2026-10-19 the opensea-ledger job (cron :23 and :53 UTC) builds THE OpenSea ledger and publishes it to its own
service files: /tokay/data/nft_ledger/published/{ledger.json, status.json, ledger_trades.csv, pull.json.gz}.
The old source (opensea-bots /tokay/data/research/nft_ledger/pull.json.gz) stopped updating 2026-10-19 19:11Z.
ledger.json has the same trades/overhead rows opensea_ledger.build() made, so opensea_ledger.days() works unchanged.

Token: the same Tokay MCP token as opensea_ledger.py, read at runtime; never printed or committed.

Usage: python3 tools/opensea_published.py      print daily aggregates + freshness (no writes)
"""
import hashlib, io, json, sys, tarfile, datetime as dt
import opensea_ledger as O

PUB = "/tokay/data/nft_ledger/published"
MAX_AGE_H = 3          # the job publishes every 30 min; older than this means it is broken


def _ctx(m):
    ctx0 = m.call("get_tokay_context", {})
    ctx = json.dumps(ctx0)
    if '"opensea-ledger"' not in ctx:  # newer tokens: inventory only comes back for an explicit workspaceId
        for w in (((ctx0.get("data") or {}).get("workspaces") or {}).get("nodes") or []):
            ctx += json.dumps(m.call("get_tokay_context", {"workspaceId": w["id"]}))
    return ctx


def _service_id(ctx, name):
    import base64, re
    for x in re.finditer(r'\{"id":\s*"([^"]+)",\s*"name":\s*"' + re.escape(name) + '"', ctx):
        try:
            if "Service" in base64.b64decode(x.group(1)).decode():
                return x.group(1)
        except Exception:
            pass
    raise RuntimeError(f"Service {name} not found on Tokay")


def fetch(m=None):
    """-> (ledger dict, status dict). Checks ledger.json's sha256 against status.json and the age of the pull."""
    m = m or O.MCP()
    svc = _service_id(_ctx(m), "opensea-ledger")
    tgz = O._get(O._url(m.call("create_service_file_download",
                               {"serviceId": svc, "scope": "SAVED", "paths": [PUB], "format": "TAR_GZ"})))
    files = {}
    with tarfile.open(fileobj=io.BytesIO(tgz)) as tf:
        for mem in tf.getmembers():
            if mem.isfile() and mem.name.rsplit("/", 1)[-1] in ("ledger.json", "status.json"):
                files[mem.name.rsplit("/", 1)[-1]] = tf.extractfile(mem).read()
    status = json.loads(files["status.json"])
    want = status["files"]["ledger.json"]["sha256"]
    if hashlib.sha256(files["ledger.json"]).hexdigest() != want:
        raise RuntimeError("ledger.json sha256 != status.json (caught mid-publish; retry in a minute)")
    led = json.loads(files["ledger.json"])
    pulled = dt.datetime.fromisoformat(led["pulled_at"].replace("Z", "+00:00"))
    age_h = (dt.datetime.now(dt.timezone.utc) - pulled).total_seconds() / 3600
    if age_h > MAX_AGE_H:
        raise RuntimeError(f"published OpenSea ledger is stale: pulled {led['pulled_at']} ({age_h:.1f} h old)")
    led["pulledAt"] = pulled.timestamp()   # what pnl_categories.opensea() uses for the CT-day cutoff
    return led, status


if __name__ == "__main__":
    led, st = fetch()
    for k, v in O.days(led).items():
        print(k, v["n"], f"{v['net_c'] / 100:+.2f}")
    print("pulled", led["pulled_at"], "net_usd", led["totals"]["net_usd"], "trades", led["totals"]["trades"])
