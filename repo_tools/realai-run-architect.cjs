#!/usr/bin/env node

const fs = require("fs");
const zlib = require("zlib");

// Try to load llama-cpp-node
let Llama;
try {
    Llama = require("llama-cpp-node").Llama;
} catch {
    console.error("\n[ERROR] Install llama-cpp-node:\n");
    console.error("    npm install llama-cpp-node\n");
    process.exit(1);
}

const MODEL_PATH = "C:\\RealAI-clean\\models\\Llama-3.2-1B-Instruct-Q4_K_M.gguf";
const PROMPT_PATH = "C:\\RealAI-clean\\prompts\\architect_mode.txt";
const SNAPSHOT_PATH = "C:\\RealAI-clean\\results\\repo_snapshot.json";
const OUT_PATH = "C:\\RealAI-clean\\results\\architect_output_chunks.txt";

const CHUNK_BYTES = 256 * 1024;
const MAX_TOKENS = 1024;

const model = new Llama({
    modelPath: MODEL_PATH,
    nCtx: 4096,
    nGpuLayers: -1,
});

const prompt = fs.readFileSync(PROMPT_PATH, "utf8");
const snapshotRaw = fs.readFileSync(SNAPSHOT_PATH);
const snapshotGzip = zlib.gzipSync(snapshotRaw);

const chunks = [];
for (let i = 0; i < snapshotGzip.length; i += CHUNK_BYTES) {
    chunks.push(snapshotGzip.slice(i, i + CHUNK_BYTES));
}

console.log(`[architect] Snapshot compressed: ${snapshotGzip.length} bytes`);
console.log(`[architect] Total chunks: ${chunks.length}`);

const allOutputs = [];

(async () => {
    for (let i = 0; i < chunks.length; i++) {
        console.log(`[architect] Processing chunk ${i + 1}/${chunks.length}`);

        const chunkB64 = chunks[i].toString("base64");

        const fullPrompt =
            prompt +
            `\n\n---\n\nRepo Snapshot Chunk ${i + 1}/${chunks.length} (gzip+base64):\n` +
            chunkB64 +
            "\n\nTask: Analyze ONLY this chunk. Identify misplaced modules, abilities, plugins, providers, GPU backend issues, registry/catalog/world-model problems, and structural corrections.";

        const result = await model.createCompletion({
            prompt: fullPrompt,
            maxTokens: MAX_TOKENS,
            temperature: 0.2,
        });

        const text = result.choices[0].text;

        allOutputs.push(
            `\n\n===== CHUNK ${i + 1}/${chunks.length} =====\n${text.trim()}\n`
        );
    }

    fs.writeFileSync(OUT_PATH, allOutputs.join(""), "utf8");
    console.log(`[architect] Wrote chunked output to ${OUT_PATH}`);
})();
