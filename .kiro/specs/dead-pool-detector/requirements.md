# Requirements — Dead Pool Detector

## User stories

1. As a token buyer, I paste a BSC token contract address and get a verdict
   (ALIVE / RISKY / DEAD) in under 60 seconds, so I know whether the pool is real
   before I buy.
2. As a hunter, I see the simulated full-sell value of a balance (not spot price ×
   balance), so I am not fooled by displayed liquidity.
3. As a skeptic, I see one reason per signal (pair, reserves, tax, drainer, age),
   so I can verify each claim myself on-chain.

## Functional requirements

- FR1: Accept a BSC token contract address (0x…, 42 chars, valid checksum optional).
- FR2: Detect PancakeSwap V2 pair via factory `getPair(token, WBNB)`; if none, try V3
  factory across fee tiers (500 / 3000 / 10000).
- FR3: Read pair reserves on-chain; report them as the liquidity truth.
- FR4: Simulate a full-balance sell of a user-entered balance (default: 1% of
  totalSupply as a probe, plus the exact balance if the user enters one) via
  router `getAmountsOut` on the real exit route; subtract estimated gas.
- FR5: Read sell tax by simulating a small sell and comparing in/out (or reading
  the token's tax getter when standard).
- FR6: Check deployer + owner against the drainer blacklist (local list, no network).
- FR7: Read contract age (deployment block) and verification status (Sourcify/BscScan).
- FR8: Render verdict + per-signal reasons; never render a number that could not
  be read (show "unreadable" instead).
- FR9: Fall back to a second public RPC automatically when the first fails or
  rate-limits; surface which RPC answered.
- FR10: Work fully client-side; no backend, no keys, no wallet connection.

## Non-functional requirements

- NFR1: First verdict in < 60 s on a normal connection.
- NFR2: Zero secrets in the repo (no API keys; public RPCs only).
- NFR3: All copy in English (submission materials must be English).
- NFR4: `/.kiro/` present at repo root and NOT gitignored (Kiroween rule).
