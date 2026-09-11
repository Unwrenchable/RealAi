#!/usr/bin/env node

/**
 * RealAI CLI
 * Command-line interface for RealAI platform
 */

const args = process.argv.slice(2);
const command = args[0] || "help";
const baseUrl = (process.env.REALAI_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

function getArg(flag: string): string | undefined {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
}

async function main(): Promise<void> {
  if (command === "health") {
    console.log(JSON.stringify(await request("/health"), null, 2));
    return;
  }
  if (command === "models") {
    console.log(JSON.stringify(await request("/v1/models"), null, 2));
    return;
  }
  if (command === "providers") {
    console.log(JSON.stringify(await request("/v1/providers"), null, 2));
    return;
  }
  if (command === "tasks") {
    console.log(JSON.stringify(await request("/v1/tasks"), null, 2));
    return;
  }
  if (command === "chat") {
    const model = getArg("--model") || "realai-1.0";
    const prompt = args
      .slice(1)
      .filter((value, index, all) => value !== "--model" && all[index - 1] !== "--model")
      .join(" ")
      .trim();
    if (!prompt) {
      throw new Error("Usage: realai chat [--model realai-1.0] <prompt>");
    }
    const response = await request("/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        messages: [{ role: "user", content: prompt }],
      }),
    });
    console.log(response?.choices?.[0]?.message?.content ?? "");
    return;
  }
  console.log("Available commands: health, models, providers, tasks, chat");
}

async function request(path: string, init?: RequestInit): Promise<any> {
  const response = await fetch(`${baseUrl}${path}`, init);
  if (!response.ok) {
    throw new Error(`RealAI API error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error(message);
  process.exitCode = 1;
});
