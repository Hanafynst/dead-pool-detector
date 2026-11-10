# Design — Dead Pool Detector

## Architecture (client-side only)

```
[Browser UI: index.html + app.js]
   ├── BSC RPC #1 (publicnode) ──┐
   ├── BSC RPC #2 (dataseed) ────┤ eth_call via ethers.js (CDN)
   └── DexScreener public API ───┘ (pair metadata, CORS-open)
```

No backend. No database. No auth. Static hosting (Vercel / GitHub Pages).

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
