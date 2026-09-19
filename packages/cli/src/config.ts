import * as fs from "fs";
import * as path from "path";
import * as os from "os";

export interface RealAIConfig {
  apiKey?: string;
  provider?: string;
  model?: string;
  baseUrl?: string;
}

const CONFIG_DIR = path.join(os.homedir(), ".realai");
const CONFIG_FILE = path.join(CONFIG_DIR, "config.json");

export function readConfig(): RealAIConfig {
  try {
    if (!fs.existsSync(CONFIG_FILE)) {
      return {};
    }
    const raw = fs.readFileSync(CONFIG_FILE, "utf-8");
    return JSON.parse(raw) as RealAIConfig;
  } catch {
    return {};
  }
}

export function writeConfig(config: RealAIConfig): void {
  if (!fs.existsSync(CONFIG_DIR)) {
    fs.mkdirSync(CONFIG_DIR, { recursive: true });
  }
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2), "utf-8");
}

export function maskApiKey(key: string): string {
  if (key.length <= 8) return "****";
  return key.slice(0, 4) + "****" + key.slice(-4);
}
