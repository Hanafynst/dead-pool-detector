// Live acceptance check for the browser port in frontend/index.html.
//
// Extracts the exact <script id="live-engine"> block shipped in the page and
// runs it headlessly against live BSC mainnet (read-only eth_calls only):
//   1. CAKE must verdict ALIVE with an exit ratio close to the CLI's.
//   2. A pairless address must verdict NO_MARKET.
//   3. The same address twice must give an identical verdict (determinism).
//
// This is a NETWORK test — it is not part of the offline unittest suite.
// Run: node tests/live_port_check.mjs
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, "..", "frontend", "index.html"), "utf8");
const m = html.match(/<script id="live-engine">([\s\S]*?)<\/script>/);
if (!m) { console.error("FAIL: live-engine block not found in index.html"); process.exit(1); }
const DeadPool = new Function(m[1] + "; return DeadPool;")();

const CAKE = "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82";
const PAIRLESS = "0x000000000000000000000000000000000000dEaD";

let failures = 0;
function check(name, ok, detail) {
  console.log((ok ? "PASS" : "FAIL") + "  " + name + (detail ? " — " + detail : ""));
  if (!ok) failures++;
}

const rpc = DeadPool.makeRpc(DeadPool.RPCS, (u, o) => fetch(u, o));

const cake1 = await DeadPool.analyze(rpc, CAKE, {});
console.log("CAKE run 1:", cake1.verdict, "| exit ratio", cake1.exitRatio,
            "| answered by", rpc.answeredBy());
for (const c of cake1.checks) console.log("   [check]", c);
check("CAKE verdict is ALIVE", cake1.verdict === "ALIVE", cake1.verdict);
check("CAKE exit ratio within 0.85–0.95 (CLI recorded 0.907)",
      cake1.exitRatio !== null && cake1.exitRatio > 0.85 && cake1.exitRatio < 0.95,
      String(cake1.exitRatio));

const cake2 = await DeadPool.analyze(rpc, CAKE, {});
console.log("CAKE run 2:", cake2.verdict, "| exit ratio", cake2.exitRatio);
check("CAKE determinism (same verdict twice)", cake2.verdict === cake1.verdict,
      cake1.verdict + " vs " + cake2.verdict);

const none = await DeadPool.analyze(rpc, PAIRLESS, {});
console.log("Pairless:", none.verdict, "|", none.summary);
check("pairless address verdict is NO_MARKET", none.verdict === "NO_MARKET", none.verdict);

console.log(failures === 0 ? "\nALL LIVE CHECKS PASSED" : "\n" + failures + " CHECK(S) FAILED");
process.exit(failures === 0 ? 0 : 1);
