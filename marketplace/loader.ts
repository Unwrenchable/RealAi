/**
 * Marketplace Plugin Loader
 * Auto-discovers and registers providers, models, tools, and agents
 */

import fs from "fs";
import path from "path";

export interface PluginManifest {
  name: string;
  version: string;
  type: "provider" | "model" | "tool" | "agent";
  entry: string;
}

export function loadMarketplacePlugins(marketplaceDir: string): PluginManifest[] {
  const plugins: PluginManifest[] = [];

  const dirs = ["providers", "models", "tools", "agents"];

  for (const dir of dirs) {
    const dirPath = path.join(marketplaceDir, dir);
    if (!fs.existsSync(dirPath)) continue;

    const items = fs.readdirSync(dirPath);
    for (const item of items) {
      const manifestPath = path.join(dirPath, item, "manifest.json");
      if (fs.existsSync(manifestPath)) {
        const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
        plugins.push(manifest);
      }
    }
  }

  return plugins;
}

export function registerPlugins(plugins: PluginManifest[]): void {
  for (const plugin of plugins) {
    console.log(`Registered marketplace plugin: ${plugin.name} (${plugin.type})`);
  }
}
