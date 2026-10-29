#!/usr/bin/env node
/**
 * CI guard: fail if `magicLink` or `oAuthProxy` appears in any better-auth
 * server config (`server.ts` tracked by git that imports from "better-auth").
 * Both plugins are behind Dependabot criticals (OAuth-state account takeover),
 * so they must never be enabled.
 *
 * Checks (all files from `git ls-files`):
 *   1. Every better-auth `server.ts` is free of `magicLink` / `oAuthProxy`.
 *   2. The set of better-auth `server.ts` files equals EXPECTED_SERVER_FILES
 *      exactly (a missing or unexpected one fails, so a new auth server can't
 *      slip past review).
 *   3. Repo-wide, no source file imports the magic-link / oauth-proxy module
 *      paths (`better-auth/plugins/magic-link`, `better-auth/plugins/oauth-proxy`,
 *      incl. client variants).
 * Exit 0 clean, 1 forbidden plugin/import, 2 no files found, 3 server-file set mismatch.
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

export const FORBIDDEN = ["magicLink", "oAuthProxy"];
export const EXPECTED_SERVER_FILES = ["realai/voice/src/lib/auth/server.ts", "src/lib/auth/server.ts"];
/** Module specifiers that must never be imported anywhere in the repo. */
export const BANNED_MODULE_RE =
  /(?:\bfrom\s*|\bimport\s*\(\s*|\bimport\s+|\brequire\s*\(\s*)["'](better-auth\/(?:client\/)?plugins\/(?:magic-link|oauth-proxy)(?:\/[^"']*)?)["']/g;
const CODE_FILE = /\.(?:[cm]?[jt]sx?)$/;
/** The guard and its test legitimately mention the banned paths. */
const SELF = new Set(["scripts/check-auth-plugins.mjs", "scripts/check-auth-plugins.test.mjs"]);

/** Return banned-module import findings for one file's source. */
export function scanImports(path, source) {
  const findings = [];
  source.split(/\r?\n/).forEach((line, i) => {
    for (const m of line.matchAll(BANNED_MODULE_RE)) findings.push({ path, line: i + 1, name: m[1] });
  });
  return findings;
}

/** Compare discovered better-auth server files to the expected list. */
export function checkExpected(scanned, expected = EXPECTED_SERVER_FILES) {
  const got = new Set(scanned);
  return {
    missing: expected.filter((f) => !got.has(f)),
    unexpected: scanned.filter((f) => !expected.includes(f)),
  };
}

export function scanImportsRepo(root, files) {
  const findings = [];
  for (const f of files) {
    if (!CODE_FILE.test(f) || SELF.has(f) || /(^|\/)node_modules\//.test(f)) continue;
    let src;
    try { src = readFileSync(join(root, f), "utf8"); } catch { continue; }
    findings.push(...scanImports(f, src));
  }
  return findings;
}
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
  const importFindings = scanImportsRepo(root, files);
  for (const f of [...findings, ...importFindings]) console.error(`[check-auth-plugins] forbidden ${f.name} in ${f.path}:${f.line}`);
  if (findings.length || importFindings.length) process.exit(1);
  const { missing, unexpected } = checkExpected(scanned);
  for (const f of missing) console.error(`[check-auth-plugins] expected better-auth server file missing: ${f}`);
  for (const f of unexpected) console.error(`[check-auth-plugins] unexpected better-auth server file (add to EXPECTED_SERVER_FILES after review): ${f}`);
  if (missing.length || unexpected.length) process.exit(3);
  console.log(`[check-auth-plugins] ok: ${scanned.length} better-auth server file(s) clean (matches expected list): ${scanned.join(", ")}; no banned module imports in ${files.length} tracked files`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) main();
