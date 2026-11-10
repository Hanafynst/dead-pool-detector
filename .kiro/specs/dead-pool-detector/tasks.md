# Tasks — Dead Pool Detector

- [ ] 1. Scaffold static site (index.html, app.js, style.css) with address + balance inputs
- [ ] 2. Implement chain.js: RPC client with 2-endpoint fallback (publicnode, dataseed)
- [ ] 3. Implement pair detection: V2 factory getPair, then V3 fee tiers
- [ ] 4. Implement reserves read + full-sell simulation via router getAmountsOut
- [ ] 5. Implement sell-tax probe (small simulated sell, in/out comparison)
- [ ] 6. Implement drainer blacklist check (local list) + deployer/owner reads
- [ ] 7. Implement verdict.js pure functions + verdict rendering
- [ ] 8. Unit tests for verdict logic (SAFU / HASH21 / BAGENT known cases)
- [ ] 9. Property-based tests (sim ≤ spot-implied; determinism)
- [ ] 10. Polish UI: one screen, one verdict, per-signal reasons, RPC badge
- [ ] 11. Deploy to free static hosting; verify public URL works cold
- [ ] 12. Record demo video (<3 min, YouTube public) + write submission text + Kiro write-up
