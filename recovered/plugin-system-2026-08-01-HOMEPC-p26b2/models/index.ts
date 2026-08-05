import fs from "node:fs";
import path from "node:path";

import type { ModelManifest } from "./types";

const modelsDir = path.join(process.cwd(), "models");

export function loadModels(): ModelManifest[] {
  if (!fs.existsSync(modelsDir)) {
    return [];
  }

  return fs
    .readdirSync(modelsDir)
    .map((dir) => {
      const manifestPath = path.join(modelsDir, dir, "manifest.json");
      if (!fs.existsSync(manifestPath)) {
        return null;
      }

      const data = fs.readFileSync(manifestPath, "utf-8");
      return JSON.parse(data) as ModelManifest;
    })
    .filter((manifest): manifest is ModelManifest => Boolean(manifest));
}

export function getModel(name: string): ModelManifest {
  const model = loadModels().find((candidate) => candidate.name === name);
  if (!model) {
    throw new Error(`Unknown model: ${name}`);
  }
  return model;
}