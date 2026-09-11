#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const CHUNKS_PATH = "C:\\RealAI-clean\\results\\architect_output_chunks.txt";
const OUT_PATH = "C:\\RealAI-clean\\results\\architect_summary.txt";

console.log("[summarizer] Loading chunked architect output…");

const raw = fs.readFileSync(CHUNKS_PATH, "utf8");

// Simple heuristic summarizer
const sections = raw.split("===== CHUNK").map(s => s.trim()).filter(Boolean);

const summary = [
    "RealAI Architect Mode — Unified Summary",
    "========================================",
    "",
    "This file merges all chunk analyses into one unified correction plan.",
    "",
    "Key Findings:",
    "",
];

sections.forEach((sec, idx) => {
    summary.push(`--- Summary of Chunk ${idx + 1} ---`);
    summary.push(sec.substring(0, 2000)); // take first 2000 chars
    summary.push("");
});

fs.writeFileSync(OUT_PATH, summary.join("\n"), "utf8");

console.log(`[summarizer] Wrote unified summary to ${OUT_PATH}`);
