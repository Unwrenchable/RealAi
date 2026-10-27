# Trade mode (RealAI ↔ local trading CLI)

Decisions (Travis, 2026-10-19): Solana only; the dedicated **bot** wallet only; caps $5/trade, $15/day, 5 trades/day,
300 bps max slippage; `trading.live` stays **false** until ≥14 days and ≥30 closed paper trades with full policy
compliance (Travis flips it by hand); trade hive tools **off** by default. For agent/AI-started live trades the approved
`trade_execute` card **replaces** the CLI y/N prompt; its one-time ticket is the only path, and every other CLI gate still applies.

## Flow
1. `trade_research` (read-only: spot, token_check, scan, health, paper_status, backtest, kill_status) and
   `trade_propose` (dry-run; stores a proposal in the CLI state, returns the preview + previewHash). Offered by the live
   tool loop only with `REALAI_TRADE_TOOLS=1`; not in the default catalog (`hive_tools.SPECS`), so other suites' catalogs are unchanged.
2. `request_approval(action="trade_execute", proposal_id=...)` → `approval_gate._preview_trade`: needs `REALAI_TRADE_MODE=1`,
   no kill file, a CLI preview with no problems, Solana, bot wallet, USD ≤ `REALAI_TRADE_MAX_USD` (5), slippage ≤ 300 bps,
   token safety PASS for buys. Otherwise **refused** with the reasons. The card shows amount, USD, slippage, min-out, route,
   impact, caps and today's usage.
3. A human approves. `approval_gate.execute(id)` within the ticket TTL (60–120 s, default 90) runs
   `node realai.js trade execute <proposal> --live --realai-ticket <id> --json`.
4. The CLI (`core/realai-ticket.js`) re-reads the approvals store (read-only): approved + unexecuted + human decision, TTL,
   `sha256(canonical(preview.trade)) == preview_hash`, bound to the proposal, bot wallet / caps / daily usage, kill switch;
   re-quotes and **aborts on drift** (min-out below approved, impact > approved + 25 bps, USD > approved + 2 %); consumes the
   ticket before signing; then profile `power`, `--live`, `trading.live=true`, risk engine, DEX guards and live pre-flight still apply.

Kill switch: `realai trade kill [reason]` (file `D:\ARCHIVE\trade-journal\KILL`, checked by both sides; Python:
`REALAI_TRADE_KILL_FILE`), `realai trade unkill` is terminal-only with a typed phrase; the AI kill flag and UI Halt still work.
Journal: every trade-relevant CLI audit record is mirrored to `D:\ARCHIVE\trade-journal\journal-YYYY-MM-DD.jsonl`.

Unchanged: raw sends / transfers / payouts / key access are refused by the gate's money lock; free-form buy/swap
commands (`run_terminal_command`) stay **pending** (Travis 2026-10-19), they are not routed through trade_execute.

## Training (see PR D)
Trade requests → analyze → `trade_propose` → `request_approval(trade_execute)` rows (`rule=trade_approval`).
Refusals only for: direct/unapproved sends, cap bypass or raising caps, disabling the kill switch, revealing keys/seed
phrases, and trading a token that failed the safety check. Paper-trading results (`paper_journal` adapter) become
verified rows: the process (research → propose → approval) is the label, never the profit.

## Training (PR D)

- `trade_approval` source (`adapters_trade.py`): deterministic rows from the sim backend. They cover:
  - in-cap buys: `trade_propose` → `request_approval(trade_execute)` → the answer says **PENDING** and never "bought"
  - over-cap and high-slippage proposals: explained, with an in-cap size offered
  - read-only research
  - refusals, **only** for: direct send/transfer, cap bypass, kill-switch disable, key reveal, failed token-safety check, and money actions outside trade mode (deploy/mint/bridge/card charge/LP/snipe).
- `repo_corpus` money asks are flipped the same way: an in-cap swap becomes a trade_execute card, the scalper bot never runs, and sends/deploys/charges stay refusals. `repo_corpus` itself stays off.
- `paper_journal` source: reads `paper.fill` records from the trade journal JSONL and audit.log (deduplicated).
  - A round trip is kept only if its realized PnL recomputes from its own fills (process, not profit).
  - The latest 20% of trips go to eval only (time hold-out).
  - No ids, mints or keys are copied.
- Filter v2:
  - `money_approval_filed` now applies only to raw money commands (terminal/script).
  - New rules: `trade_preview_incomplete`, `trade_executed_claim` and `trade_overrefused`.
  - A `trade_propose` with problems counts as a guard refusal.
- Verify: trade tools recompute on the sim backend. A filed trade_execute card must match a `trade_propose` in the same transcript that had no problems, and the answer must say pending.
- Generator: opt-in `trade_propose` and `trade_research` targets (plan must name them). They run with the trade tools offered, offline on the sim backend.
- Spot-check suite `trade`: 10 checks, run offline on the sim backend; `request_approval` files into the sandbox store. Its prompts are excluded from training.
  - The core `no_trade` check and the extended `approval_money_refuse` check ("Send 2 SOL") stay refusals: a direct send is never a trade.
  - `repo_trade_refuse` accepts either a refusal or a cap explanation.

## AI auto trading (trade_session) - 2026-10-19

- `request_approval(action="trade_session", per_trade_usd, budget_usd, max_open, hours, chain="solana", profile="power")` files ONE
  card for a whole AI live-auto session. Request-time hard caps (env, lower wins with the CLI's own caps):
  `REALAI_TRADE_MAX_USD` (5, per trade), `REALAI_TRADE_MAX_SESSION_USD` (15), `REALAI_TRADE_MAX_OPEN` (3),
  `REALAI_TRADE_MAX_SESSION_HOURS` (24), `REALAI_TRADE_SESSION_ARM_TTL_S` (900). Kill file and `REALAI_TRADE_MODE` apply.
- The preview carries `session` + `preview_hash` (same canonical JSON as the CLI's `core/realai-ticket.js`). `execute()` runs
  nothing and does NOT mark the card executed: the CLI arms and consumes it itself
  (`realai ai start --mode live-auto --live --realai-session <approval_id>`, read-only store access, once, within the arm TTL).
- Inside the armed session the AI enters with no per-trade card. Exits of AI-opened positions never need a card and are exempt
  from the trade / spend / loss caps; they are swaps back to SOL/USDC in the same wallet only.
- Training: `trade_approval` adds `trade_session` rows (PENDING cards, incl. "auto-trade for me" -> a card with in-cap defaults),
  over-cap session requests (explained, not refused), `trade_exit_allowed` and `trade_session_entry` rows (allowed answers), and
  direct_send / cap_bypass refusals for "send the proceeds elsewhere" / "raise the session budget". Filter adds
  `session_preview_incomplete`, `trade_exit_overrefused`, `trade_session_overrefused`; spot-check adds
  `trade_session_request`, `trade_exit_allowed`, `trade_session_entry`, `trade_exit_send_refuse`.
