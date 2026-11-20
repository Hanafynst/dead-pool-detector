#!/usr/bin/env python3
"""Unit tests for detector.py — mocked JSON-RPC transport, no network.

Covers: dead pool (reserves 0), healthy pool, no-pair, lying display.
Run: python3 -m unittest discover -s tests -v   (or pytest tests/)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import detector as d

TOKEN = "0x1111111111111111111111111111111111111111"
PAIR = "0x2222222222222222222222222222222222222222"
WBNB = d.CHAINS["bsc"]["wquote"]
FACTORY = d.CHAINS["bsc"]["factory"]
ROUTER = d.CHAINS["bsc"]["router"]


def word(n: int) -> str:
    return "0x" + format(n, "064x")


def addr_word(a: str) -> str:
    return "0x" + d.enc_address(a)


class FakeRpc:
    """Scenario-driven fake for eth_call."""

    def __init__(self, *, supply=1_000_000 * 10**18, decimals=18,
                 pair=PAIR, reserve_token=100_000 * 10**18,
                 reserve_quote=50 * 10**18, amounts_out=None):
        self.supply = supply
        self.decimals = decimals
        self.pair = pair
        self.reserve_token = reserve_token
        self.reserve_quote = reserve_quote
        self.amounts_out = amounts_out  # raw quote-asset out (wei)

    def eth_call(self, to, data):
        to = to.lower()
        sel = data[2:10]
        if to == TOKEN:
            if sel == d.SEL["totalSupply"]:
                return word(self.supply)
            if sel == d.SEL["decimals"]:
                return word(self.decimals)
            if sel == d.SEL["symbol"]:
                # dynamic string "TEST"
                return word(32) + word(4) + "54455354".ljust(64, "0")
        if to == FACTORY.lower() and sel == d.SEL["getPair"]:
            return addr_word(self.pair or d.ZERO_ADDRESS)
        if self.pair and to == self.pair.lower():
            if sel == d.SEL["token0"]:
                return addr_word(TOKEN)
            if sel == d.SEL["getReserves"]:
                return "0x" + format(self.reserve_token, "064x") \
                    + format(self.reserve_quote, "064x") + format(0, "064x")
        if to == ROUTER.lower() and sel == d.SEL["getAmountsOut"]:
            amt_in = d.dec_uint(data, 0)
            return word(32) + word(2) + format(amt_in, "064x") \
                + format(self.amounts_out or 0, "064x")
        raise AssertionError(f"unexpected call to={to} sel={sel}")


def analyze(rpc, **kw):
    return d.Detector(rpc, d.CHAINS["bsc"]).analyze(TOKEN, **kw)


class TestVerdicts(unittest.TestCase):
    def test_dead_pool_zero_reserves(self):
        rpc = FakeRpc(reserve_token=0, reserve_quote=0)
        r = analyze(rpc)
        self.assertEqual(r["verdict"], "DEAD")
        self.assertIn("pair", r)

    def test_dead_pool_dust_quote(self):
        # 0.0005 WBNB quote reserve vs 1,000,000 token supply -> dust -> DEAD
        rpc = FakeRpc(reserve_quote=5 * 10**14)
        r = analyze(rpc)
        self.assertEqual(r["verdict"], "DEAD")

    def test_no_pair(self):
        rpc = FakeRpc(pair=None)
        r = analyze(rpc)
        self.assertEqual(r["verdict"], "NO_MARKET")
        self.assertNotIn("pair", r)

    def test_healthy_pool_alive(self):
        # spot out for selling 1% of supply (10,000 TEST):
        # 10,000 * 50 / 100,000 = 5 WBNB; sim returns 4.95 (0.5% fee-ish)
        rpc = FakeRpc(amounts_out=int(4.95 * 10**18))
        r = analyze(rpc)
        self.assertEqual(r["verdict"], "ALIVE")
        self.assertAlmostEqual(r["exit_ratio"], 0.99, places=2)

    def test_lying_display(self):
        # Reserves imply ~$6,000 real liquidity (2 * 5 WBNB * $600);
        # site displays $13,540,000 -> real is <1% of claim -> LYING_DISPLAY
        rpc = FakeRpc(reserve_token=10_000 * 10**18,
                      reserve_quote=5 * 10**18,
                      amounts_out=int(0.49 * 10**18))
        r = analyze(rpc, displayed_usd=13_540_000, quote_usd=600)
        self.assertEqual(r["verdict"], "LYING_DISPLAY")
        self.assertLess(r["real_liquidity_usd_est"], 0.01 * 13_540_000)

    def test_honest_display_not_flagged(self):
        rpc = FakeRpc(amounts_out=int(4.95 * 10**18))
        r = analyze(rpc, displayed_usd=60_000, quote_usd=600)
        # real liq = 2*50*600 = $60,000 == displayed -> no lying flag
        self.assertEqual(r["verdict"], "ALIVE")

    def test_heavy_tax_is_risky(self):
        # sim returns only 40% of spot -> RISKY
        rpc = FakeRpc(amounts_out=int(2.0 * 10**18))
        r = analyze(rpc)
        self.assertEqual(r["verdict"], "RISKY")


class TestCodec(unittest.TestCase):
    def test_amounts_out_encoding_roundtrip(self):
        data = d.enc_get_amounts_out(10**18, [TOKEN, WBNB])
        # strip the 4-byte selector before decoding return-style words
        self.assertEqual(d.dec_uint("0x" + data[10:], 0), 10**18)

    def test_uint_array_roundtrip(self):
        enc = word(32) + word(3) + word(7) + word(8) + word(9)
        self.assertEqual(d.dec_uint_array(enc), [7, 8, 9])

    def test_string_dynamic(self):
        s = "0x" + word(32)[2:] + word(4)[2:] + "54455354".ljust(64, "0")
        self.assertEqual(d.dec_string(s), "TEST")

    def test_string_bytes32_fallback(self):
        s = d.dec_string("0x" + "54455354".ljust(64, "0"))
        self.assertEqual(s, "TEST")


if __name__ == "__main__":
    unittest.main()
