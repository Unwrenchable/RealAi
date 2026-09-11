import { createServerFn } from "@tanstack/react-start";
import type { ChatTurnResult, HiveFile, HiveStatus, RunResult, ScriptLanguage } from "./types";

export const probeHive = createServerFn({ method: "GET" }).handler(async (): Promise<HiveStatus> => {
  const { hiveStatus } = await import("./exec.server");
  return hiveStatus();
});

export const listHiveFiles = createServerFn({ method: "POST" })
  .validator((input: { path?: string }) => input)
  .handler(async ({ data }): Promise<{ ok: true; files: HiveFile[] } | { ok: false; error: string }> => {
    try {
      const { listHive } = await import("./exec.server");
      const files = await listHive(data.path || ".");
      return { ok: true, files };
    } catch (err) {
      return { ok: false, error: err instanceof Error ? err.message : String(err) };
    }
  });

export const readHivePath = createServerFn({ method: "POST" })
  .validator((input: { path: string }) => input)
  .handler(async ({ data }) => {
    const { readHiveFile } = await import("./exec.server");
    return readHiveFile(data.path);
  });

export const execCommand = createServerFn({ method: "POST" })
  .validator((input: { command: string }) => input)
  .handler(async ({ data }): Promise<RunResult> => {
    const { runCommand } = await import("./exec.server");
    const trace = await runCommand(data.command);
    return { ok: trace.exitCode === 0, trace };
  });

export const execScript = createServerFn({ method: "POST" })
  .validator((input: { language: ScriptLanguage; code: string; filename?: string; argv?: string[] }) => input)
  .handler(async ({ data }): Promise<RunResult> => {
    const { runScript } = await import("./exec.server");
    const trace = await runScript(data);
    return { ok: trace.exitCode === 0, trace };
  });

export const writeHivePath = createServerFn({ method: "POST" })
  .validator((input: { path: string; content: string }) => input)
  .handler(async ({ data }): Promise<RunResult> => {
    const { writeHiveFile } = await import("./exec.server");
    const trace = await writeHiveFile(data.path, data.content);
    return { ok: trace.exitCode === 0, trace };
  });

export const askRealai = createServerFn({ method: "POST" })
  .validator((input: { history: { role: "user" | "assistant"; content: string }[]; userText: string }) => input)
  .handler(async ({ data }): Promise<ChatTurnResult> => {
    const { runChatLoop } = await import("./chat.server");
    return runChatLoop(data);
  });
