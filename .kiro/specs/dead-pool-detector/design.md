# Design — Dead Pool Detector

## Architecture (client-side only)

```
[Browser UI: index.html + app.js]
   ├── BSC RPC #1 (publicnode) ──┐
   ├── BSC RPC #2 (dataseed) ────┤ eth_call via ethers.js (CDN)
   └── DexScreener public API ───┘ (pair metadata, CORS-open)
```

No backend. No database. No auth. Static hosting (Vercel / GitHub Pages).

## As built (2026-11-20) — deviations from the draft above

- **No ethers.js, no CDN.** The browser engine is hand-rolled (4-byte
  selectors + 32-byte words, BigInt uint256) inside the single
  `frontend/index.html` — zero external dependencies, no build step. The
  repo's zero-dependency rule (already true of detector.py) won over the
  draft's CDN plan.
- **One file, not modules.** `chain.js` / `verdict.js` / `labels.js` live as
  delimited blocks in index.html: a DOM-free engine block (transport
  injected, exercised headlessly by tests/live_port_check.mjs) plus a thin
  UI glue block. `blacklist.js` is not built yet (task 6 open).
- **The Python core is the reference implementation.** The browser engine is
  a 1:1 port of detector.py — same call order, same thresholds (dust
  0.001 WBNB, exit < 0.01 DEAD, exit < 0.80 RISKY, real < 1% of displayed
  LYING_DISPLAY). Where the draft above and detector.py disagreed (e.g.
  RISKY at sim < 50%), detector.py's shipped thresholds govern.
- **DexScreener not used.** The displayed-liquidity cross-check takes the
  figure (and BNB price) as optional user inputs, exactly like the CLI
  flags — no third-party API in the page.
- **RPC order:** dataseed → publicnode in the browser (PORT-SPEC); the
  Python core keeps dataseed → defibit → ninicoin.

## Modules

- `ui/` — single-page UI: address input, balance input, verdict card, signal list.
- `chain.js` — RPC client with fallback; minimal ABIs (factory getPair, pair
  getReserves, router getAmountsOut, ERC20 decimals/totalSupply/balanceOf).
- `verdict.js` — pure functions: pair → reserves → sim sell → tax → blacklist →
  age → verdict. Pure = property-testable.
- `blacklist.js` — local drainer list (starts with 0xD5B0e0b038A51FBF82e66fCCbC972ee83CEF9F1b).
- `labels.js` — English copy for every signal and verdict.

## Verdict logic (draft)

- DEAD if: no pair on V2 or V3, OR reserves are 0/0, OR full-sell sim returns ~0.
- RISKY if: pair exists but sim sell < 50% of spot-implied value, OR sell tax > 10%,
  OR deployer/owner on blacklist, OR contract unverified with owner mint powers.
- ALIVE otherwise (pair + reserves + sim sell consistent with spot within tolerance).

## Testing (§21/§22 self-healing loop)

- Unit tests for `verdict.js` pure functions (known cases: SAFU — dead pool with
  displayed liquidity; HASH21 — live V4 pair; BAGENT — paid-gated).
- Property-based tests: sim sell value is always ≤ spot-implied value; verdict is
  deterministic for the same inputs.
- RPC tests run against public endpoints (read-only calls only).
