#!/usr/bin/env node
/**
 * check-bonded.ts — On-chain pump.fun bonding curve status checker (Solana Kit native).
 *
 * Used by the RealAI scalper to decide whether a "...pump" mint has graduated from the
 * bonding curve to a real Raydium pool before risking capital.
 *
 * Follows solana-dev skill guidelines:
 * - @solana/kit first for scripts (createClient + rpc plugin)
 * - Explicit cluster / RPC
 * - Treat on-chain data as untrusted: assert owner == pump program, sufficient data length
 * - Read-only (no signer / no fees required for status query)
 * - Structured output: BONDED_RESULT: {json}
 *
 * Usage (via the Python scalper or direct):
 *   node --import .../tsx/... check-bonded.ts --mint <mint> [--cluster mainnet-beta|devnet] [--rpc-url <url>]
 *
 * The checker derives the canonical bonding curve PDA and reads the `complete` flag
 * directly from the on-chain account owned by the pump program.
 */
import { createClient } from '@solana/kit';
import { solanaRpc, solanaMainnetRpc, solanaDevnetRpc } from '@solana/kit-plugin-rpc';
import { address, getProgramDerivedAddress, getAddressEncoder, fetchEncodedAccount } from '@solana/kit';
const PUMP_PROGRAM_ID = '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P';
function parseArgs() {
    const out = {};
    const argv = process.argv.slice(2);
    for (let i = 0; i < argv.length; i++) {
        const a = argv[i];
        if (!a.startsWith('--'))
            continue;
        const key = a.slice(2);
        let val = 'true';
        if (i + 1 < argv.length && !argv[i + 1].startsWith('--')) {
            val = argv[++i];
        }
        out[key] = val;
    }
    return out;
}
function getRpcEndpoint(cluster, explicit) {
    if (explicit)
        return explicit;
    if (cluster.includes('dev'))
        return 'https://api.devnet.solana.com';
    if (cluster.includes('local') || cluster.includes('127'))
        return 'http://127.0.0.1:8899';
    return 'https://api.mainnet-beta.solana.com';
}
async function main() {
    const args = parseArgs();
    const mintStr = args.mint;
    const cluster = (args.cluster || 'mainnet-beta').toLowerCase();
    const explicitRpc = args['rpc-url'] || args.rpcUrl;
    if (!mintStr) {
        const err = { status: 'error', reason: 'missing_mint' };
        console.log('BONDED_RESULT: ' + JSON.stringify(err));
        process.exit(1);
    }
    let mint;
    try {
        mint = address(mintStr);
    }
    catch (e) {
        const err = { status: 'error', reason: 'invalid_mint_address', detail: String(e) };
        console.log('BONDED_RESULT: ' + JSON.stringify(err));
        process.exit(1);
    }
    const rpcUrl = getRpcEndpoint(cluster, explicitRpc);
    console.error(`[check-bonded] cluster=${cluster} rpc=${rpcUrl} mint=${mintStr}`);
    // Read-only client (no signer plugin needed for account fetch)
    const rpcPlugin = cluster.includes('mainnet')
        ? solanaMainnetRpc({ rpcUrl })
        : cluster.includes('dev')
            ? solanaDevnetRpc({ rpcUrl })
            : solanaRpc({ rpcUrl });
    const client = createClient().use(rpcPlugin);
    try {
        // Derive the bonding curve PDA exactly as the pump program does.
        // Seeds: [ "bonding-curve", mint (32 bytes) ]
        const program = PUMP_PROGRAM_ID;
        const mintBytes = getAddressEncoder().encode(mint);
        const [bondingCurveAddr] = await getProgramDerivedAddress({
            programAddress: program,
            seeds: [Buffer.from('bonding-curve'), mintBytes],
        });
        // Fetch the raw account (untrusted on-chain data — validate everything)
        const account = await fetchEncodedAccount(client.rpc, bondingCurveAddr);
        // Explicit untrusted data validation (per solana-dev W011)
        if (!account.exists) {
            const res = {
                status: 'ok',
                mint: mintStr,
                bondingCurve: bondingCurveAddr,
                bonded: false,
                complete: false,
                reason: 'account_not_found_on_chain',
            };
            console.log('BONDED_RESULT: ' + JSON.stringify(res));
            return;
        }
        if (account.programAddress !== program) {
            const res = {
                status: 'ok',
                mint: mintStr,
                bondingCurve: bondingCurveAddr,
                bonded: false,
                complete: false,
                reason: 'wrong_owner',
                owner: account.programAddress,
            };
            console.log('BONDED_RESULT: ' + JSON.stringify(res));
            return;
        }
        const data = new Uint8Array(account.data);
        if (data.byteLength < 41) {
            const res = {
                status: 'ok',
                mint: mintStr,
                bondingCurve: bondingCurveAddr,
                bonded: false,
                complete: false,
                reason: 'data_too_short',
                dataLen: data.byteLength,
            };
            console.log('BONDED_RESULT: ' + JSON.stringify(res));
            return;
        }
        // Layout (little endian, standard pump.fun bonding curve account):
        // 0-7   virtual_token_reserves  u64
        // 8-15  virtual_sol_reserves    u64
        // 16-23 real_token_reserves     u64
        // 24-31 real_sol_reserves       u64
        // 32-39 token_total_supply      u64
        // 40    complete                u8/bool
        const dv = new DataView(data.buffer, data.byteOffset);
        const virtualTokenReserves = Number(dv.getBigUint64(0, true));
        const virtualSolReserves = Number(dv.getBigUint64(8, true));
        const realTokenReserves = Number(dv.getBigUint64(16, true));
        const realSolReserves = Number(dv.getBigUint64(24, true));
        const tokenTotalSupply = Number(dv.getBigUint64(32, true));
        const complete = data[40] !== 0;
        const res = {
            status: 'ok',
            mint: mintStr,
            bondingCurve: bondingCurveAddr,
            bonded: complete, // "bonded" means the curve is complete / graduated
            complete,
            dataLen: data.byteLength,
            owner: account.programAddress,
            // Reserves exposed so the Python side can compute accurate pre-bond PnL
            // using the curve's own pricing (virtuals) even before Raydium graduation.
            virtualTokenReserves,
            virtualSolReserves,
            realTokenReserves,
            realSolReserves,
            tokenTotalSupply,
        };
        console.log('BONDED_RESULT: ' + JSON.stringify(res));
    }
    catch (e) {
        const errRes = {
            status: 'error',
            reason: 'rpc_or_pda_failure',
            detail: e?.message || String(e),
        };
        console.log('BONDED_RESULT: ' + JSON.stringify(errRes));
        process.exit(1);
    }
}
main().catch((e) => {
    const errRes = { status: 'error', reason: 'unhandled', detail: String(e?.message || e) };
    console.log('BONDED_RESULT: ' + JSON.stringify(errRes));
    process.exit(1);
});
