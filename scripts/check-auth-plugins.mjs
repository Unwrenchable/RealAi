#!/usr/bin/env node
/**
 * CI guard: fail if `magicLink` or `oAuthProxy` appears in any better-auth
 * server config (`server.ts` tracked by git that imports from "better-auth").
 * Both plugins are behind Dependabot criticals (OAuth-state account takeover),
 * so they must never be enabled. Files are discovered with `git ls-files`;
 * nothing is hardcoded. Exit 0 clean, 1 forbidden plugin found, 2 no files found.
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

export const FORBIDDEN = ["magicLink", "oAuthProxy"];
const IMPORTS_BETTER_AUTH = /from\s+["']better-auth(?:\/[^"']*)?["']|require\(\s*["']better-auth/;

export function isServerTs(path) {
  return /(^|\/)server\.ts$/.test(path);
}

/** Return findings for one file's source, or null if it is not a better-auth server file. */
export function scanSource(path, source) {
  if (!IMPORTS_BETTER_AUTH.test(source)) return null;
  const findings = [];
  source.split(/\r?\n/).forEach((line, i) => {
    for (const name of FORBIDDEN) {
      if (new RegExp(`\\b${name}\\b`).test(line)) findings.push({ path, line: i + 1, name });
    }
  });
  return findings;
}

export function scanRepo(root, files) {
  const scanned = [];
  const findings = [];
  for (const f of files.filter(isServerTs)) {
    const r = scanSource(f, readFileSync(join(root, f), "utf8"));
    if (r === null) continue;
    scanned.push(f);
    findings.push(...r);
  }
  return { scanned, findings };
}

function main() {
  const root = execFileSync("git", ["rev-parse", "--show-toplevel"], { encoding: "utf8" }).trim();
  const files = execFileSync("git", ["ls-files", "-z"], { cwd: root, encoding: "utf8" }).split("\0").filter(Boolean);
  const { scanned, findings } = scanRepo(root, files);
  if (scanned.length === 0) {
    console.error("[check-auth-plugins] no better-auth server.ts found; refusing to pass");
    process.exit(2);
  }
  for (const f of findings) console.error(`[check-auth-plugins] forbidden ${f.name} in ${f.path}:${f.line}`);
  if (findings.length) process.exit(1);
  console.log(`[check-auth-plugins] ok: ${scanned.length} better-auth server file(s) clean: ${scanned.join(", ")}`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) main();
