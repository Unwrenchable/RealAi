import * as readline from "readline";
import { readConfig } from "../config";

interface ChatOptions {
  model?: string;
  provider?: string;
  system?: string;
}

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

async function sendChat(
  messages: Message[],
  baseUrl: string,
  model: string,
  apiKey: string | undefined
): Promise<string> {
  try {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;

    const res = await fetch(`${baseUrl}/v1/chat/completions`, {
      method: "POST",
      headers,
      body: JSON.stringify({ model, messages, stream: false }),
      signal: AbortSignal.timeout(30000),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Server error ${res.status}: ${text}`);
    }

    const data = (await res.json()) as {
      choices?: Array<{ message?: { content?: string } }>;
    };
    return data.choices?.[0]?.message?.content ?? "(empty response)";
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    if (message.includes("fetch failed") || message.includes("ECONNREFUSED") || message.includes("timeout")) {
      return `[Offline mode] Echo: ${messages[messages.length - 1]?.content ?? ""}`;
    }
    throw err;
  }
}

export async function chatCommand(options: ChatOptions): Promise<void> {
  const { default: chalk } = await import("chalk");
  const { default: ora } = await import("ora");

  const config = readConfig();
  const model = options.model ?? config.model ?? "gpt-4o-mini";
  const baseUrl = config.baseUrl ?? "http://localhost:8000";

  console.log(chalk.bold.cyan("\n🤖 RealAI Chat\n"));
  console.log(chalk.dim(`  Model: ${model}`));
  console.log(chalk.dim(`  Server: ${baseUrl}`));
  console.log(chalk.dim('  Type "exit" or press Ctrl+C to quit.\n'));

  const messages: Message[] = [];

  if (options.system) {
    messages.push({ role: "system", content: options.system });
  }

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const askQuestion = (): void => {
    if (!process.stdin.isTTY) {
      rl.close();
      return;
    }

    process.stdout.write(chalk.bold.green("You: "));

    rl.once("line", async (line: string) => {
      const input = line.trim();

      if (!input) {
        askQuestion();
        return;
      }

      if (input.toLowerCase() === "exit" || input.toLowerCase() === "quit") {
        console.log(chalk.dim("\nGoodbye!\n"));
        rl.close();
        return;
      }

      messages.push({ role: "user", content: input });

      const spinner = ora({ text: "Thinking...", color: "cyan" }).start();

      try {
        const reply = await sendChat(messages, baseUrl, model, config.apiKey);
        spinner.stop();
        messages.push({ role: "assistant", content: reply });
        console.log(chalk.bold.blue("RealAI: ") + chalk.white(reply) + "\n");
      } catch (err) {
        spinner.fail("Error");
        console.error(chalk.red((err instanceof Error ? err.message : String(err)) + "\n"));
      }

      askQuestion();
    });
  };

  askQuestion();

  await new Promise<void>((resolve) => {
    rl.on("close", resolve);
  });
}
