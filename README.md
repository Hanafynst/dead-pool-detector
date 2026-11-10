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

## Status

Scaffold only — built during the Kiroween 2026 Submission Period (Oct 30 – Dec 4, 2026).
See [intake.md](intake.md) for rules, concept, and build plan.

## License

MIT — see [LICENSE](LICENSE).
