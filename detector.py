#!/usr/bin/env python3
"""Dead Pool Detector — core engine.

Read-only on-chain checks that answer one question: is this token's pool
actually alive, or is the displayed liquidity a lie?

The core lesson (documented SAFU case): a site displayed $13,540 of
liquidity and a ~$0.98 spot price while the pair's real reserves were 0
and a simulated full sell returned ~$0.003. A displayed number is a rumor;
reserves plus a simulated sell are the truth.

Checks (all eth_call, no transactions, no keys):
  1. Pair resolution   — factory.getPair(token, WBNB) or --pair
  2. Real reserves     — pair.getReserves(), split by token0/token1
  3. Token supply      — totalSupply() / decimals() / symbol()
  4. Sell simulation   — router.getAmountsOut(sell_amount, [token, WBNB])
                         compared against the spot value implied by reserves
  5. Display cross-check (optional) — if the caller passes a displayed
                         liquidity figure (--displayed-usd) and a quote
                         price (--quote-usd), real V2 liquidity is
                         estimated as 2 * quote_reserve * quote_usd and
                         compared with the claim.

Verdicts: NO_MARKET, DEAD, LYING_DISPLAY, RISKY, ALIVE.

Stdlib only. The RPC layer is a single callable so tests can inject a
fake transport.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request

# ---------------------------------------------------------------- constants

CHAINS = {
    "bsc": {
        "rpcs": [
            "https://bsc-dataseed.binance.org",
            "https://bsc-dataseed1.defibit.io",
            "https://bsc-dataseed1.ninicoin.io",
        ],
        "factory": "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73",  # PancakeSwap V2
        "router": "0x10ED43C718714eb63d5aA57B78B54704E256024E",   # PancakeSwap V2
        "wquote": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",   # WBNB
    },
}

ZERO_ADDRESS = "0x" + "00" * 20

# function selectors
SEL = {
    "totalSupply": "18160ddd",
    "decimals": "313ce567",
    "symbol": "95d89b41",
    "balanceOf": "70a08231",
    "getPair": "e6a43905",
    "getReserves": "0902f1ac",
    "token0": "0dfe1681",
    "token1": "d21220a7",
    "getAmountsOut": "d06ca61f",
}

# ---------------------------------------------------------------- ABI codec
# Minimal hand-rolled codec: address, uint256, address[] — all we need.


def enc_address(addr: str) -> str:
    return addr.lower().replace("0x", "").rjust(64, "0")


def enc_uint(value: int) -> str:
    return format(value, "064x")


def enc_call(selector: str, *args_hex: str) -> str:
    return "0x" + selector + "".join(args_hex)


def enc_get_amounts_out(amount_in: int, path: list[str]) -> str:
    """getAmountsOut(uint256,address[]) — dynamic array arg."""
    head = enc_uint(amount_in) + enc_uint(64)  # offset to array data
    body = enc_uint(len(path)) + "".join(enc_address(a) for a in path)
    return "0x" + SEL["getAmountsOut"] + head + body


def dec_uint(hexdata: str, word: int = 0) -> int:
    h = hexdata.replace("0x", "")
    return int(h[word * 64:(word + 1) * 64] or "0", 16)


def dec_address(hexdata: str, word: int = 0) -> str:
    h = hexdata.replace("0x", "")
    return "0x" + h[word * 64 + 24:(word + 1) * 64]


def dec_uint_array(hexdata: str) -> list[int]:
    # offset is in BYTES; h indexes hex chars (2 per byte).
    h = hexdata.replace("0x", "")
    base = int(h[0:64], 16) * 2  # hex-char index of the array data
    n = int(h[base:base + 64], 16)
    return [int(h[base + 64 + i * 64: base + 128 + i * 64], 16)
            for i in range(n)]


def dec_string(hexdata: str) -> str:
    h = hexdata.replace("0x", "")
    if len(h) < 128:
        # bytes32-style symbol (some tokens return a fixed bytes32)
        raw = bytes.fromhex(h[:64]).rstrip(b"\x00")
        return raw.decode("utf-8", "replace")
    base = int(h[0:64], 16) * 2  # offset is in bytes; h indexes hex chars
    n = int(h[base:base + 64], 16)
    return bytes.fromhex(h[base + 64: base + 64 + n * 2]).decode("utf-8", "replace")


# ---------------------------------------------------------------- RPC layer


class RpcError(Exception):
    pass


class JsonRpc:
    """Minimal JSON-RPC client with endpoint fallback. Read-only."""

    def __init__(self, urls: list[str], timeout: int = 20):
        self.urls = urls
        self.timeout = timeout
        self._id = 0

    def call(self, method: str, params: list):
        last_err = None
        for url in self.urls:
            self._id += 1
            payload = json.dumps({
                "jsonrpc": "2.0", "id": self._id,
                "method": method, "params": params,
            }).encode()
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json",
                         "User-Agent": "dead-pool-detector/0.1"})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    body = json.loads(r.read())
                if "error" in body:
                    raise RpcError(str(body["error"]))
                return body["result"]
            except Exception as e:  # try next endpoint
                last_err = e
        raise RpcError(f"all RPC endpoints failed: {last_err}")

    def eth_call(self, to: str, data: str) -> str:
        return self.call("eth_call", [{"to": to, "data": data}, "latest"])


# ---------------------------------------------------------------- detector


class Detector:
    def __init__(self, rpc, chain_cfg: dict):
        self.rpc = rpc
        self.cfg = chain_cfg

    def _call(self, to: str, data: str) -> str:
        return self.rpc.eth_call(to, data)

    def analyze(self, token: str, pair: str | None = None,
                sell_amount_raw: int | None = None,
                displayed_usd: float | None = None,
                quote_usd: float | None = None,
                dust_quote: float = 0.001) -> dict:
        token = token.lower()
        wquote = self.cfg["wquote"]
        out: dict = {"token": token, "checks": [], "flags": []}

        # -- token basics -------------------------------------------------
        try:
            supply = dec_uint(self._call(token, enc_call(SEL["totalSupply"])))
            decimals = dec_uint(self._call(token, enc_call(SEL["decimals"])))
        except Exception as e:
            out["verdict"] = "NO_MARKET"
            out["flags"].append(f"token contract unreadable: {e}")
            out["summary"] = "Token contract does not answer basic ERC20 calls."
            return out
        try:
            symbol = dec_string(self._call(token, enc_call(SEL["symbol"])))
        except Exception:
            symbol = "?"
        out["symbol"] = symbol
        out["decimals"] = decimals
        out["total_supply"] = supply / 10 ** decimals
        out["checks"].append(f"totalSupply = {out['total_supply']:,.4f} {symbol}")

        # -- pair resolution ----------------------------------------------
        if pair is None:
            res = self._call(self.cfg["factory"], enc_call(
                SEL["getPair"], enc_address(token), enc_address(wquote)))
            pair = dec_address(res)
        pair = pair.lower()
        if pair == ZERO_ADDRESS:
            out["verdict"] = "NO_MARKET"
            out["flags"].append("no pair against the quote asset on the main DEX factory")
            out["summary"] = f"No {symbol}/WBNB pair exists — there is no market to sell into."
            return out
        out["pair"] = pair
        out["checks"].append(f"pair = {pair}")

        # -- reserves -------------------------------------------------------
        res = self._call(pair, enc_call(SEL["getReserves"]))
        r0, r1 = dec_uint(res, 0), dec_uint(res, 1)
        token0 = dec_address(self._call(pair, enc_call(SEL["token0"]))).lower()
        if token0 == token:
            reserve_token_raw, reserve_quote_raw = r0, r1
        else:
            reserve_token_raw, reserve_quote_raw = r1, r0
        reserve_token = reserve_token_raw / 10 ** decimals
        reserve_quote = reserve_quote_raw / 10 ** 18  # WBNB has 18 decimals
        out["reserve_token"] = reserve_token
        out["reserve_quote"] = reserve_quote
        out["checks"].append(
            f"reserves = {reserve_token:,.4f} {symbol} / {reserve_quote:,.6f} WBNB")

        # -- DEAD rule: reserves zero/dust while supply exists --------------
        dead = reserve_quote_raw == 0 or reserve_token_raw == 0 \
            or reserve_quote < dust_quote
        if dead:
            out["verdict"] = "DEAD"
            out["flags"].append(
                f"quote reserve is {reserve_quote:.6f} WBNB (dust threshold "
                f"{dust_quote}) while total supply is {out['total_supply']:,.2f}")
            out["summary"] = (f"Pool is dead: reserves are zero/dust, so there "
                              f"is effectively nothing to sell into.")
            return out

        # -- sell simulation --------------------------------------------------
        if sell_amount_raw is None:
            sell_amount_raw = supply // 100  # default: 1% of total supply
        # Cap the reference sell at 10% of the pool's token reserve: beyond
        # that, constant-product price impact dominates and every pool —
        # even a healthy one — grades as a bad exit.
        sell_amount_raw = min(sell_amount_raw, max(reserve_token_raw // 10, 1))
        sell_amount = sell_amount_raw / 10 ** decimals
        spot_out = sell_amount_raw * reserve_quote_raw / reserve_token_raw / 10 ** 18
        sim_out = None
        exit_ratio = None
        try:
            res = self._call(self.cfg["router"], enc_get_amounts_out(
                sell_amount_raw, [token, wquote]))
            amounts = dec_uint_array(res)
            sim_out = amounts[-1] / 10 ** 18
            exit_ratio = (sim_out / spot_out) if spot_out > 0 else 0.0
            out["checks"].append(
                f"sell simulation: {sell_amount:,.4f} {symbol} -> {sim_out:,.6f} WBNB "
                f"(spot-implied {spot_out:,.6f}; exit ratio {exit_ratio:.3f})")
        except Exception as e:
            out["flags"].append(f"sell simulation reverted/failed: {e}")
        out["sell_amount"] = sell_amount
        out["simulated_out_wbnb"] = sim_out
        out["exit_ratio"] = exit_ratio

        # -- display cross-check --------------------------------------------
        lying = False
        if displayed_usd is not None and quote_usd:
            real_liq_usd = 2 * reserve_quote * quote_usd
            out["real_liquidity_usd_est"] = real_liq_usd
            out["checks"].append(
                f"real liquidity est. ${real_liq_usd:,.2f} vs displayed ${displayed_usd:,.2f}")
            if real_liq_usd < 0.01 * displayed_usd:
                lying = True
                out["flags"].append(
                    f"displayed liquidity ${displayed_usd:,.2f} but real "
                    f"reserves imply ~${real_liq_usd:,.2f} (<1% of the claim)")

        # -- verdict ----------------------------------------------------------
        if lying:
            out["verdict"] = "LYING_DISPLAY"
            out["summary"] = ("The displayed liquidity is a lie: real reserves "
                               "are under 1% of the displayed figure.")
        elif exit_ratio is not None and exit_ratio < 0.01:
            out["verdict"] = "DEAD"
            out["flags"].append(
                f"sell simulation returns {exit_ratio:.4f} of spot value — exit is worthless")
            out["summary"] = "A full sell simulation returns ~nothing: exit is dead."
        elif exit_ratio is not None and exit_ratio < 0.8:
            out["verdict"] = "RISKY"
            out["flags"].append(
                f"sell simulation keeps only {exit_ratio:.2f} of spot value "
                f"(tax and/or price impact)")
            out["summary"] = "Pool is alive but the exit leaks value (tax/impact)."
        elif sim_out is None:
            out["verdict"] = "RISKY"
            out["summary"] = "Reserves exist but the sell route could not be simulated."
        else:
            out["verdict"] = "ALIVE"
            out["summary"] = "Reserves are real and the simulated sell exits near spot."
        return out


# ---------------------------------------------------------------- CLI


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Dead Pool Detector (core, BSC/V2)")
    p.add_argument("--chain", default="bsc", choices=list(CHAINS))
    p.add_argument("--token", required=True)
    p.add_argument("--pair", default=None)
    p.add_argument("--sell-amount", type=float, default=None,
                   help="reference sell amount in token units (default: 1%% of supply)")
    p.add_argument("--displayed-usd", type=float, default=None,
                   help="liquidity figure a site displays, for cross-check")
    p.add_argument("--quote-usd", type=float, default=None,
                   help="USD price of the quote asset (e.g. BNB price)")
    p.add_argument("--rpc", default=None, help="override RPC URL")
    p.add_argument("--json", action="store_true", help="JSON only")
    args = p.parse_args(argv)

    cfg = CHAINS[args.chain]
    rpc = JsonRpc([args.rpc] if args.rpc else cfg["rpcs"])
    det = Detector(rpc, cfg)

    sell_raw = None
    result = det.analyze(args.token, pair=args.pair,
                         sell_amount_raw=sell_raw,
                         displayed_usd=args.displayed_usd,
                         quote_usd=args.quote_usd)

    # second pass if an explicit sell amount was requested (needs decimals)
    if args.sell_amount is not None:
        sell_raw = int(args.sell_amount * 10 ** result["decimals"])
        result = det.analyze(args.token, pair=args.pair,
                             sell_amount_raw=sell_raw,
                             displayed_usd=args.displayed_usd,
                             quote_usd=args.quote_usd)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Token:   {result.get('symbol', '?')} {result['token']}")
        for c in result["checks"]:
            print(f"  [check] {c}")
        for f in result["flags"]:
            print(f"  [flag]  {f}")
        print(f"VERDICT: {result['verdict']} — {result['summary']}")
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
