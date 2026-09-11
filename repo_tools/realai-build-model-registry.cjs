#!/usr/bin/env node

const fs = require("fs");

const OUT = "C:\\RealAI-clean\\realai\\registry\\model_registry.json";

const registry = {
    models: [
        {
            id: "qwen2.5-coder-7b",
            path: "models/qwen2.5-coder-7b-instruct-q5_k_m.gguf",
            backend: "llama.cpp",
            gpu: "amd-vulkan",
            format: "gguf",
            enabled: true
        }
    ]
};

fs.writeFileSync(OUT, JSON.stringify(registry, null, 2), "utf8");

console.log("[model-registry] Updated AMD/Vulkan model registry.");
