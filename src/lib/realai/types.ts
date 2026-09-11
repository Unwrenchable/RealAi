export type ChatRole = "user" | "assistant";

export type ExecKind = "command" | "script" | "read" | "write" | "list";

export type ScriptLanguage = "python" | "node" | "bash";

export type ExecTrace = {
  id: string;
  kind: ExecKind;
  command?: string;
  language?: ScriptLanguage;
  path?: string;
  cwd: string;
  stdout: string;
  stderr: string;
  exitCode: number | null;
  durationMs: number;
  timedOut: boolean;
  error?: string;
  live: true;
};

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  traces?: ExecTrace[];
  createdAt: string;
  /** True when this turn executed nothing and the user asked to run something. */
  missedExec?: boolean;
};

export type Thread = {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
};

export type HiveFile = {
  name: string;
  path: string;
  type: "file" | "dir";
  size: number;
  updatedAt: string;
};

export type HiveStatus = {
  ok: boolean;
  cwd: string;
  python: string;
  node: string;
  bash: string;
  files: number;
  error?: string;
};

export type ChatTurnResult = {
  ok: boolean;
  reply: string;
  traces: ExecTrace[];
  missedExec: boolean;
  model: string;
  error?: string;
  /** Speech-ready text from orch realai_meta.voice when voice is enabled. */
  spokenText?: string;
};

export type RunResult = {
  ok: boolean;
  trace: ExecTrace;
};
