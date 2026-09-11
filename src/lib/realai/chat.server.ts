/**
 * RealAI console brain — local orchestrator only.
 * Never calls xAI / Grok / OpenAI cloud. Fail closed if orch is down.
 */
import { DEFAULT_REALAI_PROMPT, WANTS_EXEC_RE } from "./persona";
import {
  runCommand,
  runScript,
  readHiveFile,
  writeHiveFile,
  listHiveTrace,
  traceToToolOutput,
} from "./exec.server";
import type { ChatTurnResult, ExecTrace, ScriptLanguage } from "./types";

const MAX_ROUNDS = 6;
const MAX_TOKENS = 700;

function orchBase(): string {
  return (
    process.env.REALAI_API_BASE ||
    process.env.REALAI_ORCH_URL ||
    "http://127.0.0.1:8001"
  ).replace(/\/$/, "");
}

function modelId(): string {
  return (
    process.env.REALAI_DEFAULT_MODEL ||
    process.env.REALAI_MODEL ||
    "realai-default-coder"
  );
}

type OaiMessage =
  | { role: "system" | "user" | "assistant"; content: string | null; tool_calls?: OaiToolCall[] }
  | { role: "tool"; tool_call_id: string; content: string };

type OaiToolCall = {
  id: string;
  type: "function";
  function: { name: string; arguments: string };
};

type OaiChoice = {
  message: {
    role: string;
    content: string | null;
    tool_calls?: OaiToolCall[];
  };
  finish_reason?: string;
};

type OrchChatResponse = {
  choices?: OaiChoice[];
  model?: string;
  realai_meta?: {
    voice?: {
      spoken_text?: string;
      text?: string;
      enabled?: boolean;
    };
    provider?: string;
  };
};

const TOOLS = [
  {
    type: "function",
    function: {
      name: "run_command",
      description:
        "Execute a shell command in the RealAI hive sandbox. Returns REAL stdout, stderr, and exit code. Use this instead of inventing output.",
      parameters: {
        type: "object",
        properties: {
          command: {
            type: "string",
            description: "Shell command, run in the hive cwd (cmd on Windows, bash elsewhere).",
          },
        },
        required: ["command"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "run_script",
      description:
        "Write a script into the hive and execute it with python, node, or bash/cmd. Returns REAL process output.",
      parameters: {
        type: "object",
        properties: {
          language: { type: "string", enum: ["python", "node", "bash"] },
          code: { type: "string", description: "Full source of the script." },
          filename: {
            type: "string",
            description: "Optional path relative to hive (e.g. scratch/job.py). Auto-named if omitted.",
          },
          argv: {
            type: "array",
            items: { type: "string" },
            description: "Optional argv passed to the script.",
          },
        },
        required: ["language", "code"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "read_file",
      description: "Read a file from the hive. Returns real file bytes decoded as UTF-8.",
      parameters: {
        type: "object",
        properties: { path: { type: "string", description: "Path relative to hive root." } },
        required: ["path"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "write_file",
      description: "Write a text file inside the hive. Overwrites.",
      parameters: {
        type: "object",
        properties: {
          path: { type: "string" },
          content: { type: "string" },
        },
        required: ["path", "content"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "list_dir",
      description: "List files in a hive directory. Returns real listing.",
      parameters: {
        type: "object",
        properties: { path: { type: "string", description: "Directory relative to hive. Default ." } },
      },
    },
  },
];

function parseArgs(raw: string): Record<string, unknown> {
  try {
    const v = JSON.parse(raw || "{}");
    return v && typeof v === "object" ? (v as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

async function dispatchTool(name: string, args: Record<string, unknown>): Promise<ExecTrace> {
  switch (name) {
    case "run_command":
      return runCommand(String(args.command ?? ""));
    case "run_script": {
      const lang = (
        ["python", "node", "bash"].includes(String(args.language))
          ? String(args.language)
          : "python"
      ) as ScriptLanguage;
      const argv = Array.isArray(args.argv) ? args.argv.map((x) => String(x)) : [];
      return runScript({
        language: lang,
        code: String(args.code ?? ""),
        filename: args.filename ? String(args.filename) : undefined,
        argv,
      });
    }
    case "read_file":
      return readHiveFile(String(args.path ?? ""));
    case "write_file":
      return writeHiveFile(String(args.path ?? "scratch/untitled.txt"), String(args.content ?? ""));
    case "list_dir":
      return listHiveTrace(String(args.path ?? "."));
    default:
      return {
        id: `exec-unknown`,
        kind: "command",
        command: name,
        cwd: "",
        stdout: "",
        stderr: `unknown tool: ${name}`,
        exitCode: -1,
        durationMs: 0,
        timedOut: false,
        error: `unknown tool: ${name}`,
        live: true,
      };
  }
}

/** Local RealAI orch only — never xAI. */
async function realaiChat(
  messages: OaiMessage[],
  toolChoice: "auto" | "required" | "none",
): Promise<{ choice: OaiChoice | undefined; raw: OrchChatResponse }> {
  const base = orchBase();
  const model = modelId();
  const useTools = toolChoice !== "none";
  const body: Record<string, unknown> = {
    model,
    messages,
    temperature: 0.2,
    max_tokens: MAX_TOKENS,
  };
  if (useTools) {
    body.tools = TOOLS;
    body.tool_choice = toolChoice;
    body.parallel_tool_calls = true;
  }

  let res: Response;
  try {
    res = await fetch(`${base}/v1/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-RealAI-Voice": "on",
        "X-RealAI-Tools": "on",
        "X-RealAI-Provider": "realai",
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(120_000),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    throw new Error(`HIVE_BRAIN_OFFLINE:${msg}`);
  }

  if (!res.ok) {
    // Local models often reject tools — retry once without tools.
    if (useTools && (res.status === 400 || res.status === 422 || res.status === 500)) {
      const retryBody = {
        model,
        messages: messages.map((m) => {
          if (m.role === "tool") {
            return { role: "user" as const, content: `TOOL RESULT:\n${m.content}` };
          }
          const { tool_calls: _tc, ...rest } = m as {
            role: "system" | "user" | "assistant";
            content: string | null;
            tool_calls?: OaiToolCall[];
          };
          return rest;
        }),
        temperature: 0.2,
        max_tokens: MAX_TOKENS,
      };
      const retry = await fetch(`${base}/v1/chat/completions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-RealAI-Voice": "on",
          "X-RealAI-Provider": "realai",
        },
        body: JSON.stringify(retryBody),
        signal: AbortSignal.timeout(120_000),
      });
      if (!retry.ok) {
        const t = await retry.text().catch(() => "");
        throw new Error(`hive brain error ${retry.status}: ${t.slice(0, 240)}`);
      }
      const data = (await retry.json()) as OrchChatResponse;
      return { choice: data.choices?.[0], raw: data };
    }
    const bodyText = await res.text().catch(() => "");
    throw new Error(`hive brain error ${res.status}: ${bodyText.slice(0, 240)}`);
  }

  const data = (await res.json()) as OrchChatResponse;
  return { choice: data.choices?.[0], raw: data };
}

export type HistoryTurn = { role: "user" | "assistant"; content: string };

function dollarCommand(text: string): string | null {
  const m = text.trim().match(/^\$\s*(.+)$/s);
  return m ? m[1].trim() : null;
}

export async function runChatLoop(input: {
  history: HistoryTurn[];
  userText: string;
}): Promise<ChatTurnResult> {
  const traces: ExecTrace[] = [];
  const model = modelId();
  const wantsExec = WANTS_EXEC_RE.test(input.userText) || input.userText.trim().startsWith("$");

  // Direct `$ cmd` — run live, no model needed for the shell step.
  const dollar = dollarCommand(input.userText);
  if (dollar) {
    const trace = await runCommand(dollar);
    traces.push(trace);
  }

  const history: OaiMessage[] = input.history.slice(-16).map((m) => ({
    role: m.role,
    content: m.content.slice(0, 4000),
  }));

  const messages: OaiMessage[] = [
    { role: "system", content: DEFAULT_REALAI_PROMPT },
    ...history,
    { role: "user", content: input.userText },
  ];

  if (traces.length) {
    messages.push({
      role: "user",
      content:
        "SYSTEM: A live command already ran. Quote this real output; do not invent any.\n" +
        traceToToolOutput(traces[0]),
    });
  }

  try {
    let { choice, raw } = await realaiChat(messages, wantsExec && !dollar ? "auto" : "auto");
    if (!choice) {
      return {
        ok: false,
        reply: "RealAI orch returned an empty completion.",
        traces,
        missedExec: wantsExec && traces.length === 0,
        model,
        error: "empty completion",
      };
    }

    if (wantsExec && !dollar && !choice.message.tool_calls?.length) {
      messages.push({
        role: "user",
        content:
          "SYSTEM: You must use a tool for this. Do not invent output. Call run_command, run_script, read_file, write_file, or list_dir now.",
      });
      const forced = await realaiChat(messages, "required");
      if (forced.choice) {
        choice = forced.choice;
        raw = forced.raw;
      }
    }

    let rounds = 0;
    while (choice?.message.tool_calls?.length && rounds < MAX_ROUNDS) {
      rounds += 1;
      const calls = choice.message.tool_calls;
      messages.push({
        role: "assistant",
        content: choice.message.content ?? null,
        tool_calls: calls,
      });
      for (const call of calls) {
        const args = parseArgs(call.function.arguments);
        const trace = await dispatchTool(call.function.name, args);
        traces.push(trace);
        messages.push({
          role: "tool",
          tool_call_id: call.id,
          content: traceToToolOutput(trace),
        });
      }
      const next = await realaiChat(messages, "auto");
      if (!next.choice) break;
      choice = next.choice;
      raw = next.raw;
    }

    const reply = (choice?.message.content || "").trim();
    const spoken =
      raw.realai_meta?.voice?.spoken_text ||
      raw.realai_meta?.voice?.text ||
      undefined;
    const missedExec = wantsExec && traces.length === 0;
    return {
      ok: true,
      reply:
        reply ||
        (traces.length
          ? "Ran live. See the exec card for the real output."
          : "No reply from RealAI."),
      traces,
      missedExec,
      model: raw.model || model,
      spokenText: spoken,
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    if (msg.startsWith("HIVE_BRAIN_OFFLINE") || msg.includes("ECONNREFUSED")) {
      return {
        ok: false,
        reply:
          "RealAI orch is offline. Fail closed — no cloud hop, no xAI.\n" +
          "Start the stack: start_all.bat  (Vulkan :8080 + orch :8001)\n" +
          "Then use Run mode for shell, or retry chat.",
        traces,
        missedExec: wantsExec && traces.length === 0,
        model,
        error: msg,
      };
    }
    return {
      ok: false,
      reply: `RealAI hive failed: ${msg}`,
      traces,
      missedExec: wantsExec && traces.length === 0,
      model,
      error: msg,
    };
  }
}
