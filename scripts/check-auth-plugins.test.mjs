import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { isServerTs, scanRepo, scanSource } from "./check-auth-plugins.mjs";

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
