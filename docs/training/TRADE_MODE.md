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
