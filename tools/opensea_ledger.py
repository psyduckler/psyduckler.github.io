#!/usr/bin/env python3
"""OpenSea (NFT flips) settled ledger, read from Tokay at runtime. Aggregates only.

Sources (all read-only, through the Tokay MCP at https://mcp.tokay.io/mcp):
  - opensea-bots service file /tokay/data/research/nft_ledger/pull.json.gz (the wallet's OpenSea sales; Tokay task output)
  - opensea-advisor service files /tokay/data/advisor/ledger/ (cached gas txs, ETH/USD hours, tx attribution)
  - opensea-advisor repo: ledger.py (the Tokay copy of nft_ledger/ledger.py), ledger_seed.json, config.json
The ledger code runs locally in a temp dir (pure: no network, no files) and is never committed.
Per flip: day = CT date of the sale, net = net_usd (after OpenSea fees and gas). Overhead gas (cancels, approvals,
bridge) is charged to the CT day it was spent, so the sum of all days equals the ledger's totals.lifetime.net_usd.

Token: env TOKAY_MCP_TOKEN_RO (read-scoped), read at runtime; never printed or committed.

Usage: python3 tools/opensea_ledger.py        print daily aggregates + totals (no writes)
Called by pnl_categories.py (update), which writes data/pnl_history.json["opensea"] + data/pnl_cats.json.
"""
import os
import gzip, io, json, re, sys, tarfile, tempfile, urllib.request, datetime as dt, importlib.util
from pathlib import Path
from zoneinfo import ZoneInfo

URL = "https://mcp.tokay.io/mcp"
CT = ZoneInfo("America/Chicago")
PULL = "/tokay/data/research/nft_ledger/pull.json.gz"
CACHE = "/tokay/data/advisor/ledger"


class MCP:
    def __init__(self):
        self.tok, self.sid, self.n = os.environ["TOKAY_MCP_TOKEN_RO"].strip(), None, 0
        self.rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "psyduckler-pnl", "version": "1"}})
        self.rpc("notifications/initialized", notify=True)

    def rpc(self, method, params=None, notify=False):
        body = {"jsonrpc": "2.0", "method": method}
        if not notify:
            self.n += 1; body["id"] = self.n
        if params is not None:
            body["params"] = params
        h = {"Authorization": "Bearer " + self.tok, "Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.sid:
            h["Mcp-Session-Id"] = self.sid
        with urllib.request.urlopen(urllib.request.Request(URL, json.dumps(body).encode(), h), timeout=120) as r:
            self.sid = r.headers.get("Mcp-Session-Id") or self.sid
            txt = r.read().decode()
        if notify:
            return None
        if txt.lstrip().startswith("{"):
            return json.loads(txt)
        for line in txt.splitlines():
            if line.startswith("data:"):
                d = json.loads(line[5:])
                if d.get("id") == body["id"]:
                    return d
        raise RuntimeError(f"no MCP answer for {method}")

    def call(self, name, args):
        r = self.rpc("tools/call", {"name": name, "arguments": args})
        res = r.get("result") or {}
        d = res.get("structuredContent")
        if d is None:
            t = (res.get("content") or [{}])[0].get("text", "")
            d = json.loads(t) if t.startswith("{") else {"text": t}
        if res.get("isError") or "errors" in d or d.get("code"):
            raise RuntimeError(f"{name}: {str(d.get('reason') or d.get('code') or d)[:200]}")
        return d


def _url(d):
    m = re.search(r'"downloadUrl":\s*"([^"]+)"', json.dumps(d))
    if not m:
        raise RuntimeError("no downloadUrl")
    return m.group(1)


def _get(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def fetch(m=None):
    """-> (pull dict, ledger module, config dict, cache dict). Reads everything over the MCP; nothing is written to the repo."""
    m = m or MCP()
    ctx0 = m.call("get_tokay_context", {})
    ctx = json.dumps(ctx0)
    if '"opensea-bots"' not in ctx:  # newer tokens: inventory only comes back for an explicit workspaceId
        for w in (((ctx0.get("data") or {}).get("workspaces") or {}).get("nodes") or []):
            ctx += json.dumps(m.call("get_tokay_context", {"workspaceId": w["id"]}))
    def node_id(kind, name):
        for x in re.finditer(r'\{"id":\s*"([^"]+)",\s*"name":\s*"' + re.escape(name) + '"', ctx):
            import base64
            try:
                if kind in base64.b64decode(x.group(1)).decode():
                    return x.group(1)
            except Exception:
                pass
        raise RuntimeError(f"{kind} {name} not found on Tokay")
    bots_svc, adv_svc, adv_repo = node_id("Service", "opensea-bots"), node_id("Service", "opensea-advisor"), node_id("Repo", "opensea-advisor")
    pull = json.loads(gzip.decompress(_get(_url(m.call("create_service_file_download",
                                                         {"serviceId": bots_svc, "scope": "SAVED", "paths": [PULL], "format": "RAW"})))))
    tgz = _get(_url(m.call("create_service_file_download", {"serviceId": adv_svc, "scope": "SAVED", "paths": [CACHE], "format": "TAR_GZ"})))
    cache = {}
    with tarfile.open(fileobj=io.BytesIO(tgz)) as tf:
        for mem in tf.getmembers():
            if mem.isfile() and mem.name.endswith(".json"):
                cache[mem.name.rsplit("/", 1)[-1]] = json.load(tf.extractfile(mem))
    repo = m.call("get_repo", {"repoId": adv_repo})
    snap = re.search(r'"currentSourceSnapshot":\s*\{"id":\s*"([^"]+)"', json.dumps(repo)).group(1)
    src = {}
    for f in ("ledger.py", "ledger_seed.json", "config.json"):
        src[f] = _get(_url(m.call("create_repo_download", {"repoSourceSnapshotId": snap, "path": f, "format": "RAW"})))
    tmp = Path(tempfile.mkdtemp(prefix="osledger_"))
    (tmp / "ledger.py").write_bytes(src["ledger.py"])
    spec = importlib.util.spec_from_file_location("os_ledger_vendored", tmp / "ledger.py")
    lg = importlib.util.module_from_spec(spec); spec.loader.exec_module(lg)
    cfg = json.loads(src["config.json"]); seed = json.loads(src["ledger_seed.json"])
    cache["_seed_attrib"] = seed.get("attrib") or {}
    return pull, lg, cfg, cache


def _iso(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() if s else None


def build(pull, lg, cfg, cache):
    """Same call the advisor makes (advisor.build_ledger), on pull.json.gz's sales. -> ledger dict."""
    lc = cfg.get("ledger") or {}
    attrib = dict((cache.get("attrib.json") or {}).get("txs") or {}, **cache["_seed_attrib"])
    bots = {b: (v["slug"], v["chain"], int(round(v["fee"] * 10000)), v["name"]) for b, v in cfg["bots"].items()}
    prices = {int(k): v for k, v in ((cache.get("ethusd.json") or {}).get("hours") or {}).items()}
    floors = {k: v["floor"] for k, v in (pull.get("floors") or {}).items() if v.get("floor")}
    return lg.build(pull["sales"], [], (cache.get("eth_txs.json") or {}).get("txs") or {},
                    (cache.get("rh_receipts.json") or {}).get("txs") or {}, prices, floors, pull["pulledAt"],
                    bots=bots, wallet=cfg["wallet"], tx_bot=attrib, tokay_start=_iso(lc.get("tokay_start")) or None,
                    gas_start=_iso(lc.get("gas_start")) or lg.START, manual=lc.get("manual_tokens"))


def cents(x):
    return int(round(x * 100))


def days(led):
    """-> {CT date: {n, w, l, net_c, fees_c, gw_c, gl_c, best_c, worst_c}} with cumulative rounding, so the sum of the
    days' cents equals round(lifetime net_usd, 2) exactly. Overhead gas: counted in net and gl, not in n/w/l."""
    d = lambda ts: dt.datetime.fromtimestamp(ts, CT).date().isoformat()
    raw = {}
    blank = lambda: dict(n=0, w=0, l=0, net=0.0, fees=0.0, gw=0.0, gl=0.0, flips=[])
    for t in led["trades"]:
        x = raw.setdefault(d(t["sell_ts"]), blank()); v = t["net_usd"] or 0.0; u = t.get("eth_usd") or 0
        x["n"] += 1; x["w"] += v > 0; x["l"] += v < 0; x["net"] += v; x["flips"].append(v)
        x["gw" if v > 0 else "gl"] += v
        x["fees"] += ((t.get("fee_wei") or 0) + (t.get("gas_direct_wei") or 0) + (t.get("gas_wrap_wei") or 0)) / 1e18 * u
    for o in led["overhead"]:
        x = raw.setdefault(d(o["ts"]), blank()); g = o.get("gas_usd") or 0.0
        x["net"] -= g; x["gl"] -= g; x["fees"] += g
    out, run, prev = {}, 0.0, 0
    for k in sorted(raw):
        x = raw[k]; run += x["net"]; c = cents(run)
        out[k] = dict(n=x["n"], w=x["w"], l=x["l"], net_c=c - prev, fees_c=cents(x["fees"]), gw_c=cents(x["gw"]),
                      best_c=cents(max(x["flips"])) if x["flips"] else None, worst_c=cents(min(x["flips"])) if x["flips"] else None)
        out[k]["gl_c"] = out[k]["net_c"] - out[k]["gw_c"]    # keeps gw + gl == net to the cent
        prev = c
    return out


if __name__ == "__main__":
    pull, lg, cfg, cache = fetch()
    led = build(pull, lg, cfg, cache)
    for k, v in days(led).items():
        print(k, v["n"], f"{v['net_c'] / 100:+.2f}")
    print("pulled", dt.datetime.fromtimestamp(pull["pulledAt"], CT).strftime("%Y-%m-%d %H:%M CT"),
          "lifetime net_usd", led["totals"]["lifetime"]["net_usd"], "trades", led["totals"]["lifetime"]["trades"])
