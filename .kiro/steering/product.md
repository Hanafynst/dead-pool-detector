# Product Steering — Dead Pool Detector

## Purpose
One screen. One contract address in. One verdict out: is this token's pool alive
or dead? Built for anyone about to buy a token based on a displayed price.

## Core truth (never violate)
- A displayed price / liquidity number is NOT proof. Only a full-balance sell
  simulation on the real exit route, minus gas, counts as value.
- A listing without bids is a queue, not liquidity. A pair with 0/0 reserves is dead.
- Read-only forever: no wallet connection, no approvals, no transactions, no keys.

## Audience
Crypto users checking a token before buying; free-mint hunters verifying a "free"
claim; anyone who has ever been rugged by a pretty number.

## Scope (v1 — Kiroween submission)
- BSC only (PancakeSwap V2 + V3).
- Inputs: one token contract address.
- Outputs: verdict (ALIVE / RISKY / DEAD) + simulated full-sell value + per-signal reasons.
- No accounts, no history, no backend.

## Out of scope (v1)
- Other chains, limit orders, portfolio tracking, alerts, paid features.

## Quality bar
- Every number shown must be reproducible on-chain (2 RPCs agree) or labeled as an estimate.
- If a check fails (RPC down, unverified contract), say so — never show a guessed number.
- Demo must complete in under 60 seconds: paste address → verdict.
