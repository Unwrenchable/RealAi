import { spawn } from "node:child_process";
import { mkdir, writeFile, readFile, readdir, stat, access } from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import os from "node:os";
import path from "node:path";
import { clip, uid } from "@/lib/utils";
import type { ExecTrace, HiveFile, HiveStatus, ScriptLanguage } from "./types";

const MAX_OUT = 48_000;
const CMD_TIMEOUT = 20_000;
const SCRIPT_TIMEOUT = 25_000;

export function hiveRoot() {
  // Prefer RealAI workspace sandbox — not a random tempdir, never cloud.
  const home =
    process.env.REALAI_HIVE_DIR ||
    process.env.REALAI_HOME ||
    process.env.REALAI_ROOT ||
    process.cwd();
  return path.resolve(home, ".hive");
}

function pythonBin(): string {
  return process.platform === "win32" ? "python" : "python3";
}

function sanitizedEnv(): NodeJS.ProcessEnv {
  const env = { ...process.env };
  // Strip cloud LLM keys — RealAI is the provider; never hop to xAI/OpenAI.
  delete env.XAI_API_KEY;
  delete env.DATABASE_URL;
  delete env.BETTER_AUTH_SECRET;
  delete env.GROK_API_KEY;
  delete env.OPENAI_API_KEY;
  delete env.ANTHROPIC_API_KEY;
  env.PYTHONDONTWRITEBYTECODE = "1";
  env.TERM = env.TERM || "xterm-256color";
  env.REALAI_BOT_LOCAL_ONLY = env.REALAI_BOT_LOCAL_ONLY || "1";
  return env;
}

export function resolveInHive(rel: string) {
  const root = hiveRoot();
  const cleaned = rel.replaceAll("\\", "/").replace(/^\/+/, "");
  const resolved = path.resolve(root, cleaned || ".");
  const relToRoot = path.relative(root, resolved);
  if (relToRoot.startsWith("..") || path.isAbsolute(relToRoot)) {
    throw new Error("path escapes hive");
  }
  return resolved;
}

const HELLO_PY = `print("RealAI hive is live.")
print("This line was printed by python — not invented by a model.")
`;

const SYSINFO_SH = `#!/usr/bin/env bash
set -euo pipefail
echo "host: $(uname -srm 2>/dev/null || echo windows)"
echo "python: $(python3 --version 2>&1 || python --version 2>&1)"
echo "node: $(node --version 2>&1)"
echo "pwd: $(pwd)"
echo "user: $(id -un 2>/dev/null || echo unknown)"
echo "date: $(date -Iseconds 2>/dev/null || date)"
`;

const SYSINFO_PS1 = `# RealAI hive sysinfo (Windows)
Write-Output "host: $([System.Environment]::OSVersion.VersionString)"
Write-Output ("python: " + (& python --version 2>&1 | Out-String).Trim())
Write-Output ("node: " + (& node --version 2>&1 | Out-String).Trim())
Write-Output ("pwd: " + (Get-Location).Path)
Write-Output ("user: " + $env:USERNAME)
Write-Output ("date: " + (Get-Date -Format o))
`;

const ADD_PY = `import sys
a = int(sys.argv[1]) if len(sys.argv) > 1 else 2
b = int(sys.argv[2]) if len(sys.argv) > 2 else 3
print(f"{a} + {b} = {a + b}")
`;

const README = `RealAI Hive workspace
=====================
Commands and scripts run HERE under the RealAI workspace (.hive).
Provider: RealAI (local orch). No xAI / cloud LLM hop.

scripts/hello.py      python demo
scripts/sysinfo.ps1   host / runtime probe (Windows)
scripts/sysinfo.sh    host / runtime probe (Unix)
scripts/add.py        2 + 3
scratch/              files the operator writes
`;

async function writeIfMissing(abs: string, body: string, mode?: number) {
  try {
    await access(abs, fsConstants.F_OK);
  } catch {
    await writeFile(abs, body, { encoding: "utf8", mode });
  }
}

export async function ensureHive() {
  const root = hiveRoot();
  await mkdir(path.join(root, "scripts"), { recursive: true });
  await mkdir(path.join(root, "scratch"), { recursive: true });
  await writeIfMissing(path.join(root, "README.txt"), README);
  await writeIfMissing(path.join(root, "scripts", "hello.py"), HELLO_PY);
  await writeIfMissing(path.join(root, "scripts", "sysinfo.sh"), SYSINFO_SH, 0o755);
  await writeIfMissing(path.join(root, "scripts", "sysinfo.ps1"), SYSINFO_PS1);
  await writeIfMissing(path.join(root, "scripts", "add.py"), ADD_PY);
  return root;
}

function decode(buf: Buffer) {
  if (buf.length === 0) return "";
  if (buf.includes(0)) return `<binary ${buf.length} bytes>`;
  return clip(buf.toString("utf8"), MAX_OUT);
}

type SpawnOut = {
  stdout: string;
  stderr: string;
  exitCode: number | null;
  durationMs: number;
  timedOut: boolean;
  error?: string;
};

function spawnCaptured(
  cmd: string,
  args: string[],
  cwd: string,
  timeoutMs: number,
): Promise<SpawnOut> {
  return new Promise((resolve) => {
    const started = Date.now();
    let timedOut = false;
    let settled = false;
    const finish = (out: SpawnOut) => {
      if (settled) return;
      settled = true;
      resolve(out);
    };
    let child;
    try {
      child = spawn(cmd, args, {
        cwd,
        env: sanitizedEnv(),
        stdio: ["ignore", "pipe", "pipe"],
      });
    } catch (err) {
      finish({
        stdout: "",
        stderr: err instanceof Error ? err.message : String(err),
        exitCode: -1,
        durationMs: Date.now() - started,
        timedOut: false,
        error: err instanceof Error ? err.message : String(err),
      });
      return;
    }
    const out: Buffer[] = [];
    const err: Buffer[] = [];
    const t = setTimeout(() => {
      timedOut = true;
      child.kill("SIGKILL");
    }, timeoutMs);
    child.stdout?.on("data", (d: Buffer) => out.push(d));
    child.stderr?.on("data", (d: Buffer) => err.push(d));
    child.on("error", (e) => {
      clearTimeout(t);
      finish({
        stdout: decode(Buffer.concat(out)),
        stderr: decode(Buffer.concat(err)) || e.message,
        exitCode: -1,
        durationMs: Date.now() - started,
        timedOut,
        error: e.message,
      });
    });
    child.on("close", (code) => {
      clearTimeout(t);
      finish({
        stdout: decode(Buffer.concat(out)),
        stderr: decode(Buffer.concat(err)),
        exitCode: code,
        durationMs: Date.now() - started,
        timedOut,
      });
    });
  });
}

function probeBin(cmd: string, args: string[]): Promise<string> {
  return spawnCaptured(cmd, args, hiveRoot(), 4000).then((r) => {
    const line = (r.stdout || r.stderr).trim().split("\n")[0] || "";
    return r.exitCode === 0 || line ? line || cmd : "missing";
  });
}

export async function hiveStatus(): Promise<HiveStatus> {
  try {
    const cwd = await ensureHive();
    const shellProbe =
      process.platform === "win32"
        ? probeBin("powershell", ["-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"])
        : probeBin("bash", ["--version"]);
    const [python, node, shell, listing] = await Promise.all([
      probeBin(pythonBin(), ["--version"]),
      probeBin("node", ["--version"]),
      shellProbe,
      listHive("."),
    ]);
    return {
      ok: true,
      cwd,
      python,
      node,
      bash: shell.split("\n")[0] || (process.platform === "win32" ? "powershell" : "bash"),
      files: listing.filter((f) => f.type === "file").length,
    };
  } catch (err) {
    return {
      ok: false,
      cwd: hiveRoot(),
      python: "?",
      node: "?",
      bash: "?",
      files: 0,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

export async function runCommand(command: string): Promise<ExecTrace> {
  const cwd = await ensureHive();
  const trimmed = command.trim();
  if (!trimmed) {
    return {
      id: uid("exec"),
      kind: "command",
      command: "",
      cwd,
      stdout: "",
      stderr: "empty command",
      exitCode: -1,
      durationMs: 0,
      timedOut: false,
      error: "empty command",
      live: true,
    };
  }
  const out =
    process.platform === "win32"
      ? await spawnCaptured("cmd.exe", ["/d", "/s", "/c", trimmed], cwd, CMD_TIMEOUT)
      : await spawnCaptured("bash", ["-lc", trimmed], cwd, CMD_TIMEOUT);
  return {
    id: uid("exec"),
    kind: "command",
    command: trimmed,
    cwd,
    stdout: out.stdout,
    stderr: out.stderr,
    exitCode: out.exitCode,
    durationMs: out.durationMs,
    timedOut: out.timedOut,
    error: out.error,
    live: true,
  };
}

const EXT: Record<ScriptLanguage, string> = {
  python: "py",
  node: "js",
  bash: "sh",
};

function runners(): Record<ScriptLanguage, [string, string[]]> {
  return {
    python: [pythonBin(), []],
    node: ["node", []],
    bash:
      process.platform === "win32"
        ? ["powershell", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]]
        : ["bash", []],
  };
}

export async function runScript(opts: {
  language: ScriptLanguage;
  code: string;
  filename?: string;
  argv?: string[];
}): Promise<ExecTrace> {
  const cwd = await ensureHive();
  const lang = opts.language;
  const rel =
    opts.filename?.trim() ||
    path.posix.join("scratch", `run-${Date.now()}.${EXT[lang]}`);
  let abs: string;
  try {
    abs = resolveInHive(rel);
  } catch (err) {
    return {
      id: uid("exec"),
      kind: "script",
      language: lang,
      path: rel,
      cwd,
      stdout: "",
      stderr: err instanceof Error ? err.message : String(err),
      exitCode: -1,
      durationMs: 0,
      timedOut: false,
      error: "path escapes hive",
      live: true,
    };
  }
  await mkdir(path.dirname(abs), { recursive: true });
  // On Windows, "bash" scripts are run via PowerShell; write .ps1 when needed.
  let runAbs = abs;
  let runRel = rel;
  if (lang === "bash" && process.platform === "win32" && !rel.endsWith(".ps1")) {
    runRel = rel.replace(/\.sh$/i, "") + ".ps1";
    runAbs = resolveInHive(runRel);
    await writeFile(runAbs, opts.code, { encoding: "utf8" });
  } else {
    await writeFile(abs, opts.code, { encoding: "utf8", mode: lang === "bash" ? 0o755 : 0o644 });
  }
  const [bin, prefix] = runners()[lang];
  const argv = opts.argv ?? [];
  const out = await spawnCaptured(bin, [...prefix, runAbs, ...argv], cwd, SCRIPT_TIMEOUT);
  return {
    id: uid("exec"),
    kind: "script",
    language: lang,
    command: `${bin} ${runRel}${argv.length ? " " + argv.join(" ") : ""}`,
    path: runRel,
    cwd,
    stdout: out.stdout,
    stderr: out.stderr,
    exitCode: out.exitCode,
    durationMs: out.durationMs,
    timedOut: out.timedOut,
    error: out.error,
    live: true,
  };
}

export async function readHiveFile(rel: string): Promise<ExecTrace> {
  const cwd = await ensureHive();
  const started = Date.now();
  try {
    const abs = resolveInHive(rel);
    const st = await stat(abs);
    if (st.isDirectory()) {
      return {
        id: uid("exec"),
        kind: "read",
        path: rel,
        cwd,
        stdout: "",
        stderr: "is a directory — use list_dir",
        exitCode: 1,
        durationMs: Date.now() - started,
        timedOut: false,
        live: true,
      };
    }
    if (st.size > 200_000) {
      return {
        id: uid("exec"),
        kind: "read",
        path: rel,
        cwd,
        stdout: "",
        stderr: `file too large (${st.size} bytes)`,
        exitCode: 1,
        durationMs: Date.now() - started,
        timedOut: false,
        live: true,
      };
    }
    const buf = await readFile(abs);
    return {
      id: uid("exec"),
      kind: "read",
      path: rel,
      cwd,
      stdout: decode(buf),
      stderr: "",
      exitCode: 0,
      durationMs: Date.now() - started,
      timedOut: false,
      live: true,
    };
  } catch (err) {
    return {
      id: uid("exec"),
      kind: "read",
      path: rel,
      cwd,
      stdout: "",
      stderr: err instanceof Error ? err.message : String(err),
      exitCode: 1,
      durationMs: Date.now() - started,
      timedOut: false,
      error: err instanceof Error ? err.message : String(err),
      live: true,
    };
  }
}

export async function writeHiveFile(rel: string, content: string): Promise<ExecTrace> {
  const cwd = await ensureHive();
  const started = Date.now();
  try {
    const abs = resolveInHive(rel);
    await mkdir(path.dirname(abs), { recursive: true });
    await writeFile(abs, content, "utf8");
    return {
      id: uid("exec"),
      kind: "write",
      path: rel,
      cwd,
      stdout: `wrote ${content.length} chars → ${rel}`,
      stderr: "",
      exitCode: 0,
      durationMs: Date.now() - started,
      timedOut: false,
      live: true,
    };
  } catch (err) {
    return {
      id: uid("exec"),
      kind: "write",
      path: rel,
      cwd,
      stdout: "",
      stderr: err instanceof Error ? err.message : String(err),
      exitCode: 1,
      durationMs: Date.now() - started,
      timedOut: false,
      error: err instanceof Error ? err.message : String(err),
      live: true,
    };
  }
}

export async function listHive(rel = "."): Promise<HiveFile[]> {
  const cwd = await ensureHive();
  const abs = resolveInHive(rel);
  const names = await readdir(abs, { withFileTypes: true });
  const rows: HiveFile[] = [];
  for (const d of names) {
    const child = path.join(abs, d.name);
    let size = 0;
    let updatedAt = new Date().toISOString();
    try {
      const st = await stat(child);
      size = st.size;
      updatedAt = st.mtime.toISOString();
    } catch {
      /* skip */
    }
    rows.push({
      name: d.name,
      path: path.posix.join(rel.replaceAll("\\", "/"), d.name).replace(/^\.\//, ""),
      type: d.isDirectory() ? "dir" : "file",
      size,
      updatedAt,
    });
  }
  rows.sort((a, b) => {
    if (a.type !== b.type) return a.type === "dir" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
  return rows;
}

export async function listHiveTrace(rel = "."): Promise<ExecTrace> {
  const cwd = await ensureHive();
  const started = Date.now();
  try {
    const rows = await listHive(rel);
    const lines = rows.map((r) =>
      r.type === "dir" ? `dir  ${r.path}/` : `file ${String(r.size).padStart(8)}  ${r.path}`,
    );
    return {
      id: uid("exec"),
      kind: "list",
      path: rel,
      cwd,
      stdout: lines.join("\n") || "(empty)",
      stderr: "",
      exitCode: 0,
      durationMs: Date.now() - started,
      timedOut: false,
      live: true,
    };
  } catch (err) {
    return {
      id: uid("exec"),
      kind: "list",
      path: rel,
      cwd,
      stdout: "",
      stderr: err instanceof Error ? err.message : String(err),
      exitCode: 1,
      durationMs: Date.now() - started,
      timedOut: false,
      error: err instanceof Error ? err.message : String(err),
      live: true,
    };
  }
}

export function traceToToolOutput(trace: ExecTrace) {
  return JSON.stringify({
    live: true,
    kind: trace.kind,
    command: trace.command,
    path: trace.path,
    cwd: trace.cwd,
    exitCode: trace.exitCode,
    durationMs: trace.durationMs,
    timedOut: trace.timedOut,
    stdout: trace.stdout,
    stderr: trace.stderr,
    error: trace.error ?? null,
    note: "This is real process output. Quote it. Do not invent a different result.",
  });
}
