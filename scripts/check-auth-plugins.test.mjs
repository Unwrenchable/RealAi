import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { checkExpected, EXPECTED_SERVER_FILES, isServerTs, scanImports, scanImportsRepo, scanRepo, scanSource } from "./check-auth-plugins.mjs";

const clean = 'import { betterAuth } from "better-auth";\nimport { bearer } from "better-auth/plugins";\nexport const auth = betterAuth({ plugins: [bearer()] });\n';
const withMagic = 'import { betterAuth } from "better-auth";\nimport { magicLink } from "better-auth/plugins";\nexport const auth = betterAuth({ plugins: [magicLink({})] });\n';

test("only server.ts paths are candidates", () => {
  assert.ok(isServerTs("src/lib/auth/server.ts"));
  assert.ok(!isServerTs("src/lib/auth/popup.server.ts"));
});

test("fails when magicLink is present", () => {
  const r = scanSource("server.ts", withMagic);
  assert.ok(r.length > 0 && r.every((f) => f.name === "magicLink"));
});

test("flags oAuthProxy", () => {
  assert.equal(scanSource("server.ts", 'import "better-auth";\nimport { betterAuth } from "better-auth";\noAuthProxy()')[0].name, "oAuthProxy");
});

test("passes when clean, ignores files not importing better-auth", () => {
  assert.deepEqual(scanSource("server.ts", clean), []);
  assert.equal(scanSource("server.ts", "const magicLink = 1;"), null);
});

test("fixture repo: fail then pass", () => {
  const root = mkdtempSync(join(tmpdir(), "auth-guard-"));
  mkdirSync(join(root, "a"));
  writeFileSync(join(root, "a/server.ts"), withMagic);
  assert.equal(scanRepo(root, ["a/server.ts"]).findings.length > 0, true);
  writeFileSync(join(root, "a/server.ts"), clean);
  const ok = scanRepo(root, ["a/server.ts"]);
  assert.deepEqual(ok, { scanned: ["a/server.ts"], findings: [] });
});

test("bans magic-link / oauth-proxy module paths (static, dynamic, require, client)", () => {
  const ml = "better-auth/plugins/" + "magic-link";
  const op = "better-auth/plugins/" + "oauth-proxy";
  assert.equal(scanImports("a.ts", `import { magicLink } from "${ml}";`)[0].name, ml);
  assert.equal(scanImports("a.ts", `const m = await import("${op}");`)[0].name, op);
  assert.equal(scanImports("a.cjs", `const m = require('${op}/x');`)[0].name, op + "/x");
  assert.equal(scanImports("a.ts", `import "better-auth/client/plugins/${"magic-link"}";`).length, 1);
  assert.deepEqual(scanImports("a.ts", 'import { bearer } from "better-auth/plugins";'), []);
});

test("repo import scan skips non-code files and node_modules", () => {
  const root = mkdtempSync(join(tmpdir(), "auth-imports-"));
  const bad = 'import { x } from "better-auth/plugins/' + 'oauth-proxy";\n';
  mkdirSync(join(root, "node_modules"));
  writeFileSync(join(root, "a.ts"), bad);
  writeFileSync(join(root, "notes.md"), bad);
  writeFileSync(join(root, "node_modules/b.ts"), bad);
  const r = scanImportsRepo(root, ["a.ts", "notes.md", "node_modules/b.ts"]);
  assert.deepEqual(r.map((f) => f.path), ["a.ts"]);
});

test("expected server file list: exact match passes, missing/unexpected fail", () => {
  assert.deepEqual(checkExpected([...EXPECTED_SERVER_FILES]), { missing: [], unexpected: [] });
  assert.deepEqual(checkExpected(["src/lib/auth/server.ts"]).missing, ["realai/voice/src/lib/auth/server.ts"]);
  assert.deepEqual(checkExpected([...EXPECTED_SERVER_FILES, "x/server.ts"]).unexpected, ["x/server.ts"]);
});
