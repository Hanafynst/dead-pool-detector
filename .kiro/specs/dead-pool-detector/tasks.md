# Tasks — Dead Pool Detector

Status key: [x] done · [ ] open. Annotations record what actually shipped;
the original task text is kept so the spec trail stays readable.

- [x] 1. Scaffold static site with address + balance inputs
  — Shipped as ONE self-contained `frontend/index.html` (inline CSS/JS, zero
    external refs, no build step) instead of separate index/app/style files.
    Address input shipped in the Live check section (2026-11-20). A balance
    input was deliberately NOT shipped: the checker uses the CLI's reference
    sell (1% of supply, capped at 10% of the pool's token reserve) so verdicts
    stay comparable across tokens.
- [x] 2. Implement the RPC client with 2-endpoint fallback
  — In-page engine (`DeadPool.makeRpc` in frontend/index.html). Order per
    PORT-SPEC: bsc-dataseed.binance.org → bsc.publicnode.com, fall-through on
    any failure; the answering endpoint is shown in the UI. (design.md listed
    publicnode first; PORT-SPEC order won. The Python core keeps its own
    3-endpoint list.)
- [ ] 3. Implement pair detection: V2 factory getPair, then V3 fee tiers
  — V2 DONE (CLI + browser port). V3 fee-tier probing still open (roadmap).
- [x] 4. Implement reserves read + sell simulation via router getAmountsOut
  — Done in detector.py and ported 1:1 to the browser engine.
- [ ] 5. Implement sell-tax probe (small simulated sell, in/out comparison)
  — Open. The exit ratio already surfaces tax as value leakage (RISKY flag
    reads "tax and/or price impact"), but there is no separate tax figure yet.
- [ ] 6. Implement drainer blacklist check (local list) + deployer/owner reads
  — Open (build-phase hardening).
- [x] 7. Implement verdict logic as pure functions + verdict rendering
  — detector.py `Detector.analyze` (transport injected) and the DOM-free
    browser engine share the same thresholds; both render checks, flags and
    the verdict (CLI text/JSON, page report block).
- [x] 8. Unit tests for verdict logic (known cases)
  — Python suite: 11/11 mocked-RPC tests (dead pool zero reserves, dust-quote
    dead, no pair, healthy ALIVE exit 0.99, lying display, honest display not
    flagged, heavy-tax RISKY, ABI codec roundtrips). The SAFU-style case is
    covered as the lying-display/dead samples. Live acceptance for the port:
    tests/live_port_check.mjs (CAKE → ALIVE 0.907024, pairless → NO_MARKET,
    determinism). HASH21 / BAGENT live cases not yet run.
- [ ] 9. Property-based tests (sim ≤ spot-implied; determinism)
  — Open as a framework task. Spot evidence only: determinism verified live
    (same address twice → identical verdict and ratio, 2026-11-20).
- [x] 10. Polish UI: one screen, one verdict, per-signal reasons, RPC badge
  — Verdict chip + per-check rows + flag lines; the status line names the RPC
    endpoint that answered.
- [ ] 11. Deploy to free static hosting; verify public URL works cold
  — Open (hosting handled outside this branch's local work).
- [ ] 12. Record demo video (<3 min, YouTube public) + write submission text + Kiro write-up
  — Drafts exist (video script + Devpost draft, outside the repo); recording,
    the Kiro write-up (from credit-phase evidence) and final submit are open.

## Added 2026-11-20 (credit-independent build)

- [x] 13. Browser live-RPC port of detector.py per PORT-SPEC.md
  — Live check section in frontend/index.html; acceptance recorded in
    tests/live_port_check.mjs run output (see STATUS.md, 2026-11-20 entry).
- [x] 14. Agent hook: run the unit suite on save
  — .kiro/hooks/run-tests-on-save.kiro.hook (fileSaved on detector.py,
    tests/**, frontend/index.html → python3 -m unittest discover -s tests).
