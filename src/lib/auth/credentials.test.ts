import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { isProductionEnv, resolveGrokCredentials } from "./credentials.ts";

const PROD = { NODE_ENV: "production", BETTER_AUTH_URL: "https://app.example.com" };

describe("resolveGrokCredentials", () => {
  it("throws in production when the client id is missing", () => {
    assert.throws(() => resolveGrokCredentials({ ...PROD, GROK_AUTH_CLIENT_SECRET: "x" }), /GROK_AUTH_CLIENT_ID/);
  });
  it("throws in production when the client secret is missing", () => {
    assert.throws(() => resolveGrokCredentials({ ...PROD, GROK_AUTH_CLIENT_ID: "x" }), /GROK_AUTH_CLIENT_SECRET/);
  });
  it("throws on VERCEL_ENV=production even with a preview secret set", () => {
    assert.throws(() => resolveGrokCredentials({ VERCEL_ENV: "production", GROK_PREVIEW_CLIENT_SECRET: "p" }));
  });
  it("treats whitespace-only values as unset in production", () => {
    assert.throws(() => resolveGrokCredentials({ ...PROD, GROK_AUTH_CLIENT_ID: " ", GROK_AUTH_CLIENT_SECRET: " " }));
  });
  it("uses injected credentials in production", () => {
    const r = resolveGrokCredentials({ ...PROD, GROK_AUTH_CLIENT_ID: "id", GROK_AUTH_CLIENT_SECRET: "s" });
    assert.equal(r.mode, "deployed");
  });
  it("does not throw when auth is explicitly off", () => {
    assert.equal(resolveGrokCredentials({ ...PROD, VITE_AUTH_ENABLED: "false" }).mode, "off");
  });
  it("disables preview auth when GROK_PREVIEW_CLIENT_SECRET is unset", () => {
    const r = resolveGrokCredentials({});
    assert.equal(r.mode, "preview-disabled");
    assert.equal(r.clientSecret, undefined);
  });
  it("enables preview auth from GROK_PREVIEW_CLIENT_SECRET", () => {
    const r = resolveGrokCredentials({ GROK_PREVIEW_CLIENT_SECRET: "p" });
    assert.equal(r.mode, "preview");
    assert.equal(r.clientId, "grok_preview");
    assert.equal(r.clientSecret, "p");
  });
  it("NODE_ENV=production without BETTER_AUTH_URL is the sandbox preview, not production", () => {
    assert.equal(isProductionEnv({ NODE_ENV: "production" }), false);
    assert.equal(isProductionEnv(PROD), true);
  });
});

describe("no hardcoded preview secret", () => {
  const dir = dirname(fileURLToPath(import.meta.url));
  const files = readdirSync(dir).filter((f) => /\.tsx?$/.test(f) && !f.endsWith(".test.ts"));
  it("auth sources contain no secret-like string literal", () => {
    // Any 40+ char base64url/hex literal (the old preview secret was 64 chars).
    const literal = /["'`][A-Za-z0-9_-]{40,}["'`]/;
    for (const f of files) {
      const src = readFileSync(join(dir, f), "utf8");
      assert.ok(!literal.test(src), `${f} contains a secret-like literal`);
      assert.ok(!/PREVIEW_CLIENT_SECRET\s*=/.test(src), `${f} assigns PREVIEW_CLIENT_SECRET`);
    }
  });
});