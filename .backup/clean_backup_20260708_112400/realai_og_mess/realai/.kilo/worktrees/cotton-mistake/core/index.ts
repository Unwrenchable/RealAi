import { exec as execCallback } from "node:child_process";
import { watch as fsWatch } from "node:fs";
import { writeFile } from "node:fs/promises";
import { promisify } from "node:util";

const exec = promisify(execCallback);

export type Task = {
  input: string;
};

export class Agent {
  name = "agent";
  description = "Base agent";

  say(message: string) {
    // Keep this simple for CLI visibility.
    console.log(`[${this.name}] ${message}`);
  }
}

export async function shell(command: string): Promise<string> {
  const { stdout, stderr } = await exec(command, { env: process.env });
  return [stdout, stderr].filter(Boolean).join("").trim();
}

type WatchCallback = (event: string, file: string | Buffer | null) => void;

export const fs = {
  watch(path: string, callback: WatchCallback) {
    try {
      return fsWatch(path, { recursive: true }, callback);
    } catch {
      return fsWatch(path, callback);
    }
  },
  async write(path: string, content: string) {
    await writeFile(path, content, "utf8");
  },
};

export const http = {
  async post(url: string, body: unknown) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`HTTP ${response.status}: ${text}`);
    }
    return response;
  },
};
