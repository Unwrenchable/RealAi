#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const SUMMARY_PATH = "C:\\RealAI-clean\\results\\architect_summary.txt";

console.log("[autofix] Loading architect summary…");

const summary = fs.readFileSync(SUMMARY_PATH, "utf8");

// Simple pattern-based fixer
const moves = [];
const lines = summary.split("\n");

lines.forEach(line => {
    if (line.includes("MOVE →")) {
        const parts = line.split("MOVE →")[1].trim().split("→");
        const src = parts[0].trim();
        const dest = parts[1].trim();
        moves.push({ src, dest });
    }
});

console.log(`[autofix] Found ${moves.length} move operations.`);

moves.forEach(({ src, dest }) => {
    try {
        const absSrc = path.join("C:\\RealAI-clean", src);
        const absDest = path.join("C:\\RealAI-clean", dest);

        fs.mkdirSync(path.dirname(absDest), { recursive: true });
        fs.renameSync(absSrc, absDest);

        console.log(`[autofix] Moved ${src} → ${dest}`);
    } catch (err) {
        console.log(`[autofix] Failed to move ${src}: ${err}`);
    }
});

console.log("[autofix] Done.");
