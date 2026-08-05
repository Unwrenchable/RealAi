import { readConfig } from "../config";

const SERVER_FETCH_TIMEOUT_MS = 3000;

const PROVIDER_MODELS: Record<string, string[]> = {
  openai: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
  anthropic: [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-3-opus-20240229",
  ],
  gemini: ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"],
  grok: ["grok-beta", "grok-vision-beta"],
  openrouter: [
    "openai/gpt-4o",
    "anthropic/claude-3.5-sonnet",
    "meta-llama/llama-3.1-70b-instruct",
    "mistralai/mixtral-8x7b-instruct",
  ],
  mistral: ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest"],
  together: [
    "meta-llama/Llama-3-70b-chat-hf",
    "meta-llama/Llama-3-8b-chat-hf",
    "mistralai/Mixtral-8x7B-Instruct-v0.1",
  ],
  deepseek: ["deepseek-chat", "deepseek-coder"],
  perplexity: [
    "llama-3.1-sonar-large-128k-online",
    "llama-3.1-sonar-small-128k-online",
    "llama-3.1-sonar-huge-128k-online",
  ],
};

async function fetchModelsFromServer(baseUrl: string): Promise<string[] | null> {
  try {
    const res = await fetch(`${baseUrl}/v1/models`, { signal: AbortSignal.timeout(SERVER_FETCH_TIMEOUT_MS) });
    if (!res.ok) return null;
    const data = (await res.json()) as { data?: Array<{ id: string }> };
    return data.data?.map((m) => m.id) ?? null;
  } catch {
    return null;
  }
}

export async function modelsListCommand(): Promise<void> {
  const { default: chalk } = await import("chalk");
  const { default: ora } = await import("ora");

  const config = readConfig();
  const provider = config.provider ?? "openai";
  const baseUrl = config.baseUrl ?? "http://localhost:8000";

  const spinner = ora("Fetching models...").start();

  const serverModels = await fetchModelsFromServer(baseUrl);

  if (serverModels) {
    spinner.succeed("Models fetched from server");
    console.log(chalk.bold.cyan(`\n📋 Available Models (from server at ${baseUrl})\n`));
    for (const m of serverModels) {
      console.log(`  ${chalk.green("•")} ${chalk.white(m)}`);
    }
  } else {
    spinner.warn(`Server at ${baseUrl} not reachable — showing offline defaults`);
    const models = PROVIDER_MODELS[provider] ?? PROVIDER_MODELS["openai"];
    console.log(chalk.bold.cyan(`\n📋 Available Models (${provider})\n`));
    for (const m of models) {
      console.log(`  ${chalk.green("•")} ${chalk.white(m)}`);
    }
  }

  console.log();
}
