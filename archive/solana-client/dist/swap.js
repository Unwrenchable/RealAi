/**
 * swap.ts — Jupiter v1 swap executor for the RealAI scalper (legacy tx, direct routes only).
 *
 * Supports:
 *   --side buy|sell
 *   --mint <token>
 *   --amount <sol-for-buy | token-atomic-or-large-for-sell>
 *   --keypair <path-to-json>
 *   --cluster mainnet-beta|devnet
 *   --dry-run true
 *   --rpc-url <override>
 *
 * Always requests asLegacyTransaction + onlyDirectRoutes for compatibility (no ALTs).
 * Prints:
 *   PREPARED_SWAP_TX
 *   SWAP_RESULT: {json}
 *
 * The scalper drives buys with small SOL floats and sells with captured atomic or huge number (treated as "use balance" best effort).
 */
import { Connection, Keypair, PublicKey, Transaction, VersionedTransaction, LAMPORTS_PER_SOL, } from "@solana/web3.js";
/**
 * NOTE (solana-dev skill alignment):
 * This file is intentionally a *legacy boundary* for Jupiter v1.
 * Jupiter /swap with asLegacyTransaction:true returns a pre-built legacy tx.
 * We deserialize/sign/send with web3.js here only.
 * New pure-Solana logic (bonding curve status, future PDAs, etc.) lives in
 * check-bonded.ts and uses @solana/kit + plugins exclusively.
 * Do not let PublicKey/Transaction/Connection leak into the Python side or
 * other new modules.
 */
import * as fs from "fs";
const JUP_QUOTE = "https://api.jup.ag/swap/v1/quote";
const JUP_SWAP = "https://api.jup.ag/swap/v1/swap";
const SOL_MINT = "So11111111111111111111111111111111111111112";
const LEGACY_TX_MAX_BYTES = 1232;
const SELL_USE_WALLET_BALANCE_THRESHOLD = 1e11;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function jupiterHeaders(extra) {
    const h = { ...(extra || {}) };
    const key = process.env.JUPITER_API_KEY || process.env.JUP_API_KEY;
    if (key) {
        h["x-api-key"] = key;
    }
    return h;
}
async function getWalletTokenBalanceAtomic(connection, owner, mint) {
    try {
        const resp = await connection.getParsedTokenAccountsByOwner(owner, {
            mint: new PublicKey(mint),
        });
        let total = 0;
        for (const { account } of resp.value) {
            const info = account.data?.parsed?.info?.tokenAmount;
            const amt = info?.amount;
            if (amt != null) {
                total += parseInt(String(amt), 10);
            }
        }
        return total;
    }
    catch {
        return 0;
    }
}
/** Jupiter free tier rate-limits aggressively; retry 429 before giving up. */
async function fetchJupiter(url, init, label = "request") {
    const waitsMs = [0, 1200, 2800, 5500];
    let last;
    for (let i = 0; i < waitsMs.length; i++) {
        if (waitsMs[i] > 0) {
            console.warn(`[swap] Jupiter 429/backoff on ${label}, waiting ${waitsMs[i]}ms…`);
            await sleep(waitsMs[i]);
        }
        const res = await fetch(url, init);
        if (res.status !== 429) {
            return res;
        }
        last = res;
    }
    return last;
}
function routeMetaFromQuote(quote) {
    let poolsUsed = [];
    let routeSummary = "";
    try {
        const plan = quote.routePlan || quote.marketInfos || [];
        poolsUsed = Array.from(new Set(plan
            .map((step) => step?.swapInfo?.label || step?.label || step?.ammKey)
            .filter(Boolean)));
        routeSummary = poolsUsed.length ? poolsUsed.join(" → ") : "unknown";
    }
    catch {
        /* ignore */
    }
    return { poolsUsed, routeSummary };
}
async function jupiterQuote(inputMint, outputMint, inputAmount, onlyDirectRoutes, slippageBps) {
    const qParams = new URLSearchParams({
        inputMint,
        outputMint,
        amount: String(inputAmount),
        slippageBps: String(slippageBps),
        onlyDirectRoutes: onlyDirectRoutes ? "true" : "false",
    });
    const qRes = await fetchJupiter(`${JUP_QUOTE}?${qParams.toString()}`, { method: "GET", headers: jupiterHeaders() }, "quote");
    if (!qRes.ok) {
        const txt = await qRes.text();
        throw new Error(`quote_http_${qRes.status}:${txt.slice(0, 200)}`);
    }
    const quote = await qRes.json();
    if (!quote?.outAmount) {
        throw new Error("bad_quote");
    }
    return quote;
}
async function jupiterSwapTx(quote, userPublicKey, onlyDirectRoutes, asLegacyTransaction) {
    const swapPayload = {
        quoteResponse: quote,
        userPublicKey,
        wrapAndUnwrapSol: true,
        asLegacyTransaction,
        onlyDirectRoutes,
        dynamicComputeUnitLimit: true,
        prioritizationFeeLamports: {
            priorityLevelWithMaxLamports: { maxLamports: 1000000, priorityLevel: "medium" },
        },
    };
    const sRes = await fetchJupiter(JUP_SWAP, {
        method: "POST",
        headers: jupiterHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(swapPayload),
    }, "swap");
    if (!sRes.ok) {
        const txt = await sRes.text();
        throw new Error(`swap_http_${sRes.status}:${txt.slice(0, 300)}`);
    }
    const swapData = await sRes.json();
    const swapTxB64 = swapData?.swapTransaction;
    if (!swapTxB64) {
        throw new Error("no_swap_tx_in_response");
    }
    return swapTxB64;
}
function serializeLegacyOrNull(tx) {
    try {
        return tx.serialize();
    }
    catch (e) {
        const msg = String(e?.message || e);
        if (msg.includes("too large") || msg.includes("1232")) {
            return null;
        }
        throw e;
    }
}
async function prepareSwap(keypair, inputMint, outputMint, inputAmount, preferOnlyDirect, slippageBps) {
    const attempts = [];
    // v0 first — fewer size limits on mainnet routes
    attempts.push({ onlyDirectRoutes: preferOnlyDirect, asLegacy: false, label: "versioned" });
    if (!preferOnlyDirect) {
        attempts.push({ onlyDirectRoutes: false, asLegacy: true, label: "multi-hop legacy" });
        attempts.push({ onlyDirectRoutes: true, asLegacy: true, label: "direct legacy" });
    }
    else {
        attempts.push({ onlyDirectRoutes: true, asLegacy: true, label: "direct legacy" });
    }
    let lastErr = null;
    const seen = new Set();
    for (const att of attempts) {
        const key = `${att.onlyDirectRoutes}:${att.asLegacy}`;
        if (seen.has(key))
            continue;
        seen.add(key);
        try {
            const quote = await jupiterQuote(inputMint, outputMint, inputAmount, att.onlyDirectRoutes, slippageBps);
            const meta = routeMetaFromQuote(quote);
            const b64 = await jupiterSwapTx(quote, keypair.publicKey.toBase58(), att.onlyDirectRoutes, att.asLegacy);
            if (att.asLegacy) {
                const tx = Transaction.from(Buffer.from(b64, "base64"));
                tx.sign(keypair);
                const rawTx = serializeLegacyOrNull(tx);
                if (!rawTx) {
                    console.warn(`[swap] Legacy tx too large for ${att.label} (${meta.routeSummary}); trying narrower route…`);
                    continue;
                }
                if (rawTx.length > LEGACY_TX_MAX_BYTES) {
                    console.warn(`[swap] Legacy tx ${rawTx.length}B > ${LEGACY_TX_MAX_BYTES}B; retrying…`);
                    continue;
                }
                console.log(`[swap] Prepared ${att.label} (${rawTx.length}B) route: ${meta.routeSummary}`);
                return { kind: "legacy", rawTx, quote, meta, onlyDirectRoutes: att.onlyDirectRoutes };
            }
            const vtx = VersionedTransaction.deserialize(Buffer.from(b64, "base64"));
            vtx.sign([keypair]);
            const rawTx = Buffer.from(vtx.serialize());
            console.log(`[swap] Prepared ${att.label} (${rawTx.length}B) route: ${meta.routeSummary}`);
            return { kind: "versioned", rawTx, quote, meta, onlyDirectRoutes: att.onlyDirectRoutes };
        }
        catch (e) {
            lastErr = e instanceof Error ? e : new Error(String(e));
            console.warn(`[swap] Attempt ${att.label} failed: ${lastErr.message}`);
            if (String(lastErr.message).includes("429")) {
                await sleep(1500);
            }
            else {
                await sleep(350);
            }
        }
    }
    throw lastErr || new Error("all_swap_attempts_failed");
}
function parseArgs() {
    const out = {};
    const argv = process.argv.slice(2);
    for (let i = 0; i < argv.length; i++) {
        let a = argv[i];
        if (!a.startsWith("--"))
            continue;
        const key = a.slice(2);
        let val = "true";
        if (i + 1 < argv.length && !argv[i + 1].startsWith("--")) {
            val = argv[++i];
        }
        out[key] = val;
    }
    return out;
}
async function main() {
    const args = parseArgs();
    const keypairPath = args.keypair || args["keypair"];
    const mint = args.mint;
    const rawAmount = parseFloat(args.amount || "0");
    const side = String(args.side || "buy").toLowerCase();
    const cluster = args.cluster || "mainnet-beta";
    const dryRun = ["true", "1", "yes"].includes(String(args["dry-run"] || args.dryRun || "").toLowerCase());
    const explicitRpc = args["rpc-url"] || args["rpcUrl"] || process.env.SOLANA_RPC_URL;
    // Control routing breadth: false = let Jupiter use any main pools (Raydium, Meteora, Orca, Pump, etc.)
    // true = onlyDirectRoutes (faster, fewer hops, but may miss some liquidity sources)
    const onlyDirectRoutes = ["true", "1", "yes"].includes(String(args["only-direct-routes"] || args["onlyDirectRoutes"] || args["direct-routes"] || "").toLowerCase());
    if (!keypairPath || !mint) {
        console.error("[swap] Missing --keypair or --mint");
        const errRes = { status: "error", reason: "missing_args" };
        console.log("SWAP_RESULT: " + JSON.stringify(errRes));
        process.exit(1);
    }
    let secret;
    try {
        secret = JSON.parse(fs.readFileSync(keypairPath, "utf8"));
    }
    catch (e) {
        console.error("[swap] Failed to load keypair:", e?.message || e);
        const errRes = { status: "error", reason: "bad_keypair", detail: String(e) };
        console.log("SWAP_RESULT: " + JSON.stringify(errRes));
        process.exit(1);
    }
    const keypair = Keypair.fromSecretKey(Uint8Array.from(secret));
    const rpcUrl = explicitRpc ||
        (cluster.includes("dev") ? "https://api.devnet.solana.com" : "https://api.mainnet-beta.solana.com");
    const connection = new Connection(rpcUrl, "confirmed");
    const wallet = keypair.publicKey.toBase58();
    const isSell = side === "sell" || side === "s";
    const inputMint = isSell ? mint : SOL_MINT;
    const outputMint = isSell ? SOL_MINT : mint;
    const slippageBps = parseInt(args["slippage-bps"] || args.slippageBps || (isSell ? "300" : "150"), 10);
    // Amount handling:
    // buy: amount is SOL (human), convert to lamports
    // sell: token atomic — clamped to on-chain ATA balance (source of truth)
    let inputAmount;
    if (!isSell) {
        inputAmount = Math.max(1, Math.floor(rawAmount * LAMPORTS_PER_SOL));
    }
    else {
        const requested = Math.max(1, Math.floor(rawAmount));
        const walletTokens = await getWalletTokenBalanceAtomic(connection, keypair.publicKey, mint);
        if (walletTokens <= 0) {
            const errRes = {
                status: "error",
                reason: "no_token_balance",
                detail: `wallet holds 0 of mint ${mint}`,
                wallet,
            };
            console.log("SWAP_RESULT: " + JSON.stringify(errRes));
            process.exit(1);
        }
        if (requested >= SELL_USE_WALLET_BALANCE_THRESHOLD) {
            inputAmount = walletTokens;
        }
        else {
            inputAmount = Math.min(requested, walletTokens);
        }
        if (inputAmount < walletTokens) {
            console.log(`[swap] Sell clamp: requested=${requested} wallet=${walletTokens} using=${inputAmount}`);
        }
        else {
            console.log(`[swap] Sell full wallet balance: ${walletTokens} atomic`);
        }
    }
    const balanceLamports = await connection.getBalance(keypair.publicKey);
    const balanceSol = balanceLamports / LAMPORTS_PER_SOL;
    console.log(`[swap] wallet=${wallet} balance=${balanceSol.toFixed(6)} SOL`);
    // Buy needs swap amount + ATA rent + tx fees (live only)
    const feeBufferLamports = 12000000;
    if (!dryRun && !isSell && balanceLamports < inputAmount + feeBufferLamports) {
        const errRes = {
            status: "error",
            reason: "insufficient_sol",
            detail: `balance_lamports=${balanceLamports} need>=${inputAmount + feeBufferLamports}`,
            wallet,
            balanceSol,
        };
        console.error(`[swap] Insufficient SOL: have ${balanceSol.toFixed(6)} need ~${((inputAmount + feeBufferLamports) / LAMPORTS_PER_SOL).toFixed(6)} SOL`);
        console.log("SWAP_RESULT: " + JSON.stringify(errRes));
        process.exit(1);
    }
    if (!dryRun && isSell && balanceLamports < 8000000) {
        const errRes = {
            status: "error",
            reason: "insufficient_sol",
            detail: `balance_lamports=${balanceLamports} need_fee_lamports>=8000000`,
            wallet,
            balanceSol,
        };
        console.log("SWAP_RESULT: " + JSON.stringify(errRes));
        process.exit(1);
    }
    console.log(`[swap] ${isSell ? "SELL" : "BUY"} mint=${mint} amountArg=${rawAmount} atomicIn=${inputAmount} cluster=${cluster} dry=${dryRun}`);
    let prepared;
    try {
        prepared = await prepareSwap(keypair, inputMint, outputMint, inputAmount, onlyDirectRoutes, slippageBps);
    }
    catch (e) {
        const detail = String(e?.message || e);
        const reason = detail.startsWith("quote_http") ? "quote_failed" : "swap_build_failed";
        console.error("[swap] Swap prepare failed:", detail);
        const errRes = { status: "error", reason, detail };
        console.log("SWAP_RESULT: " + JSON.stringify(errRes));
        process.exit(1);
    }
    const { quote, meta, rawTx } = prepared;
    const { poolsUsed, routeSummary } = meta;
    console.log(`[swap] quote outAmount=${quote.outAmount} priceImpact=${quote.priceImpactPct || "?"}%`);
    console.log(`[swap] route/pools: ${routeSummary || "direct/unknown"}`);
    console.log("PREPARED_SWAP_TX");
    if (dryRun) {
        const res = {
            status: "dry_run",
            side,
            mint,
            inAmount: inputAmount,
            quoteOutAmount: quote.outAmount,
            txSize: rawTx.length,
            txKind: prepared.kind,
            onlyDirectRoutes: prepared.onlyDirectRoutes,
            poolsUsed,
            route: routeSummary,
            note: "not_sent",
        };
        console.log("SWAP_RESULT: " + JSON.stringify(res));
        return;
    }
    // 4. Simulate (required before live send — solana-dev safety)
    let simErr = null;
    let simLogs = [];
    try {
        if (prepared.kind === "legacy") {
            const tx = Transaction.from(rawTx);
            const sim = await connection.simulateTransaction(tx);
            simErr = sim.value?.err;
            simLogs = sim.value?.logs || [];
        }
        else {
            const vtx = VersionedTransaction.deserialize(rawTx);
            const sim = await connection.simulateTransaction(vtx);
            simErr = sim.value?.err;
            simLogs = sim.value?.logs || [];
        }
    }
    catch (e) {
        simErr = e?.message || e;
    }
    if (simErr) {
        console.error("[swap] Simulation failed:", simErr);
        const errRes = {
            status: "error",
            reason: "simulation_failed",
            detail: String(simErr),
            logs: simLogs.slice(-8),
            wallet,
            balanceSol,
        };
        console.log("SWAP_RESULT: " + JSON.stringify(errRes));
        process.exit(1);
    }
    console.log("[swap] Simulation OK");
    // 5. Send
    let signature;
    try {
        signature = await connection.sendRawTransaction(rawTx, {
            skipPreflight: false,
            preflightCommitment: "confirmed",
        });
    }
    catch (e) {
        const detail = String(e?.message || e);
        console.error("[swap] sendRawTransaction failed:", detail);
        let reason = "send_failed";
        if (detail.includes("prior credit") ||
            detail.includes("InsufficientFunds") ||
            detail.includes("insufficient lamports")) {
            reason = "insufficient_sol";
        }
        const errRes = {
            status: "error",
            reason,
            detail,
            wallet,
            balanceSol,
        };
        console.log("SWAP_RESULT: " + JSON.stringify(errRes));
        process.exit(1);
    }
    // 6. Confirm
    let confirmed = false;
    try {
        const latest = await connection.getLatestBlockhash("confirmed");
        const conf = await connection.confirmTransaction({ signature, blockhash: latest.blockhash, lastValidBlockHeight: latest.lastValidBlockHeight }, "confirmed");
        confirmed = !conf.value?.err;
        if (conf.value?.err) {
            console.warn("[swap] Confirm reported error:", conf.value.err);
        }
    }
    catch (e) {
        console.warn("[swap] Confirm timeout (tx may still land):", e?.message || e);
    }
    const result = {
        status: "success",
        signature,
        confirmed,
        side,
        mint,
        inAmount: inputAmount,
        outAmount: quote.outAmount,
        priceImpactPct: quote.priceImpactPct,
        poolsUsed,
        route: routeSummary,
        txKind: prepared.kind,
        onlyDirectRoutes: prepared.onlyDirectRoutes,
    };
    console.log("SWAP_RESULT: " + JSON.stringify(result));
}
main().catch((e) => {
    console.error("[swap] Unhandled:", e?.message || e);
    const errRes = { status: "error", reason: "unhandled", detail: String(e?.message || e) };
    console.log("SWAP_RESULT: " + JSON.stringify(errRes));
    process.exit(1);
});
