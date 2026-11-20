# Dead Pool Detector — Kiroween 2026 (Frankenstein)

> "The price is a rumor. The sell simulation is the truth."

Paste any BSC token contract address → get a verdict: is the pool alive or dead?

## What it checks (all read-only, no wallet connection, no backend)

1. **Pair exists?** PancakeSwap V2/V3 `getPair` on-chain.
2. **Real reserves?** Actual pair reserves — not the displayed price.
3. **Full-sell simulation** — what you'd really get selling your whole balance on the real exit route (minOut 0), minus gas. A displayed price means nothing until the sell is simulated.
4. **Sell tax** — on-chain tax read from the token contract.
5. **Drainer blacklist** — deployer/owner checked against known drainer wallets.
6. **Contract age & shape** — verified source, owner powers, hidden mint/drain functions.

**Verdict: ALIVE / RISKY / DEAD** — with the simulated sell number and one reason per signal.

## Why

Free-mint and token hunting taught us one lesson: a displayed price is not proof.
A token can show $13,540 liquidity while the pool holds 0 and a full sell returns
~$0.003. This tool turns that vetting pipeline into a one-screen product.

## Tech

- Static frontend (HTML/JS, no framework) — hosted free, no backend, no API keys.
- Data: public BSC RPC (2 endpoints, fallback) + DexScreener public API.
- Built with [Kiro](https://kiro.dev) — spec-driven development. See `/.kiro/` for
  specs, steering docs, hooks, and agents used.

## Core engine (prep build)

`detector.py` is the analysis core the UI will wrap. Pure Python stdlib —
no dependencies, read-only `eth_call`s only, no wallet, no keys.

```bash
python3 detector.py --chain bsc --token <token-address> [--pair <pair-address>]
                    [--sell-amount N] [--displayed-usd X] [--quote-usd Y] [--json]
```

What it does:

1. Resolves the pair (`factory.getPair(token, WBNB)`, or `--pair`).
2. Reads **real reserves** (`pair.getReserves()`) and token `totalSupply`.
3. **Simulates a sell** of a reference amount (default 1% of supply,
   capped at 10% of the pool's token reserve) through the router's
   `getAmountsOut`, and compares it with the spot value implied by the
   reserves (the *exit ratio*).
4. Optionally cross-checks a displayed liquidity figure: with
   `--displayed-usd` (what a site claims) and `--quote-usd` (BNB price),
   real V2 liquidity is estimated as `2 × quote reserve × quote price`.

Verdicts:

| Verdict | Meaning |
|---|---|
| `ALIVE` | Reserves are real; the simulated sell exits near spot. |
| `RISKY` | Pool lives, but the exit leaks value (tax / price impact), or the sell route can't be simulated. |
| `DEAD` | Reserves are zero/dust while supply exists, or a simulated sell returns ~nothing. |
| `LYING_DISPLAY` | Real reserves are under 1% of the displayed liquidity figure. |
| `NO_MARKET` | No pair against WBNB on the main factory — nothing to sell into. |

Tests (mocked RPC, no network):

```bash
python3 -m unittest discover -s tests -v
```

Live smoke (2026-11-12, BSC mainnet, read-only): CAKE → `ALIVE`
(exit ratio 0.91); a pairless address → `NO_MARKET`.

## Status

Core engine + unit tests done in prep (branch `prep-core`); frontend,
Kiro spec/hook integration evidence, and demo assets are the build-phase
work (Nov 13 – Dec 4, 2026). See `intake.md` for rules, concept, and
build plan.

## License

MIT — see [LICENSE](LICENSE).
