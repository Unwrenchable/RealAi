import * as readline from "readline";
import { readConfig, writeConfig } from "../config";

interface LoginOptions {
  provider?: string;
}

function prompt(question: string, hidden = false): Promise<string> {
  return new Promise((resolve) => {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });

    if (hidden && process.stdout.isTTY) {
      process.stdout.write(question);
      let answer = "";
      process.stdin.setRawMode(true);
      process.stdin.resume();
      process.stdin.setEncoding("utf8");
      process.stdin.on("data", function handler(char: string) {
        if (char === "\n" || char === "\r" || char === "\u0003") {
          process.stdin.setRawMode(false);
          process.stdin.pause();
          process.stdin.removeListener("data", handler);
          process.stdout.write("\n");
          rl.close();
          resolve(answer);
        } else if (char === "\u007F") {
          answer = answer.slice(0, -1);
        } else {
          answer += char;
        }
      });
    } else {
      rl.question(question, (answer) => {
        rl.close();
        resolve(answer.trim());
      });
    }
  });
}

const KNOWN_PROVIDERS = [
  "openai",
  "anthropic",
  "gemini",
  "grok",
  "openrouter",
  "mistral",
  "together",
  "deepseek",
  "perplexity",
];

export async function loginCommand(options: LoginOptions): Promise<void> {
  const { default: chalk } = await import("chalk");

  console.log(chalk.bold.cyan("\n🤖 RealAI Login\n"));

  let provider = options.provider;
  if (!provider) {
    console.log(chalk.dim("Available providers: " + KNOWN_PROVIDERS.join(", ")));
    provider = await prompt(chalk.white("Provider (default: openai): "));
    if (!provider) provider = "openai";
  }

  if (!KNOWN_PROVIDERS.includes(provider.toLowerCase())) {
    console.log(chalk.yellow(`⚠ Unknown provider "${provider}". Proceeding anyway.`));
  }

  const apiKey = await prompt(chalk.white("API Key: "), true);
  if (!apiKey) {
    console.log(chalk.red("✗ API key cannot be empty."));
    process.exit(1);
  }

  const model = await prompt(chalk.white("Default model (press enter to skip): "));

  const existing = readConfig();
  writeConfig({
    ...existing,
    apiKey,
    provider: provider.toLowerCase(),
    ...(model ? { model } : {}),
    baseUrl: "http://localhost:8000",
  });

  console.log(chalk.green("\n✓ Login successful!"));
  console.log(chalk.dim(`  Config saved to ~/.realai/config.json`));
  console.log(chalk.dim(`  Provider: ${provider.toLowerCase()}`));
  if (model) console.log(chalk.dim(`  Model: ${model}`));
}
