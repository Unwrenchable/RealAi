import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { isProductionEnv, resolveGrokCredentials } from "./credentials.ts";

const CREDS = { GROK_AUTH_CLIENT_ID: "id", GROK_AUTH_CLIENT_SECRET: "s", BETTER_AUTH_SECRET: "b" };

describe("production detection", () => {
  it("NODE_ENV=production alone is production", () => {
    assert.equal(isProductionEnv({ NODE_ENV: "production" }), true);
  });
  it("any BETTER_AUTH_URL alone is production", () => {
    assert.equal(isProductionEnv({ BETTER_AUTH_URL: "http://localhost:8080" }), true);
  });
  it("VERCEL_ENV=production is production", () => {
    assert.equal(isProductionEnv({ VERCEL_ENV: "production" }), true);
  });
  it("REALAI_AUTH_SANDBOX=1 overrides NODE_ENV / BETTER_AUTH_URL", () => {
    assert.equal(isProductionEnv({ NODE_ENV: "production", BETTER_AUTH_URL: "https://x", REALAI_AUTH_SANDBOX: "1" }), false);
    assert.equal(isProductionEnv({ NODE_ENV: "production", REALAI_AUTH_SANDBOX: "TRUE" }), false);
  });
  it("the sandbox flag never overrides VERCEL_ENV=production", () => {
    assert.equal(isProductionEnv({ VERCEL_ENV: "production", REALAI_AUTH_SANDBOX: "1" }), true);
  });
  it("comparisons are case-insensitive", () => {
    assert.equal(isProductionEnv({ NODE_ENV: " Production " }), true);
    assert.equal(isProductionEnv({ VERCEL_ENV: "PRODUCTION", REALAI_AUTH_SANDBOX: "Yes" }), true);
    assert.equal(resolveGrokCredentials({ NODE_ENV: "PRODUCTION", VITE_AUTH_ENABLED: "FALSE" }).mode, "off");
  });
  it("development without BETTER_AUTH_URL is not production", () => {
    assert.equal(isProductionEnv({}), false);
    assert.equal(isProductionEnv({ NODE_ENV: "development" }), false);
  });
});

describe("resolveGrokCredentials in production", () => {
  const PROD = { NODE_ENV: "production" };
  it("throws when the client id is missing", () => {
    const { GROK_AUTH_CLIENT_ID: _, ...rest } = CREDS;
    assert.throws(() => resolveGrokCredentials({ ...PROD, ...rest }), /GROK_AUTH_CLIENT_ID/);
  });
  it("throws when the client secret is missing", () => {
    const { GROK_AUTH_CLIENT_SECRET: _, ...rest } = CREDS;
    assert.throws(() => resolveGrokCredentials({ ...PROD, ...rest }), /GROK_AUTH_CLIENT_SECRET/);
  });
  it("requires BETTER_AUTH_SECRET", () => {
    const { BETTER_AUTH_SECRET: _, ...rest } = CREDS;
    assert.throws(() => resolveGrokCredentials({ ...PROD, ...rest }), /BETTER_AUTH_SECRET/);
  });
  it("refuses to boot when preview would be disabled (no creds, no preview secret)", () => {
    assert.throws(() => resolveGrokCredentials(PROD), /refusing to start/);
  });
  it("never falls back to the preview client, even with a preview secret", () => {
    assert.throws(() => resolveGrokCredentials({ ...PROD, GROK_PREVIEW_CLIENT_SECRET: "p" }));
  });
  it("whitespace-only values count as unset", () => {
    assert.throws(() => resolveGrokCredentials({ ...PROD, GROK_AUTH_CLIENT_ID: " ", GROK_AUTH_CLIENT_SECRET: "s", BETTER_AUTH_SECRET: "b" }));
  });
  it("boots with all three set", () => {
    assert.equal(resolveGrokCredentials({ ...PROD, ...CREDS }).mode, "deployed");
  });
  it("does not throw when VITE_AUTH_ENABLED=false", () => {
    assert.equal(resolveGrokCredentials({ ...PROD, VITE_AUTH_ENABLED: "false" }).mode, "off");
  });
});

describe("resolveGrokCredentials outside production", () => {
  it("preview is disabled without GROK_PREVIEW_CLIENT_SECRET", () => {
    const r = resolveGrokCredentials({});
    assert.equal(r.mode, "preview-disabled");
    assert.equal(r.clientSecret, undefined);
  });
  it("sandbox flag + preview secret uses the preview client even with NODE_ENV=production", () => {
    const r = resolveGrokCredentials({ NODE_ENV: "production", REALAI_AUTH_SANDBOX: "1", GROK_PREVIEW_CLIENT_SECRET: "p" });
    assert.equal(r.mode, "preview");
    assert.equal(r.clientId, "grok_preview");
  });
  it("injected creds are used in dev", () => {
    assert.equal(resolveGrokCredentials({ GROK_AUTH_CLIENT_ID: "id", GROK_AUTH_CLIENT_SECRET: "s" }).mode, "deployed");
  });
});

describe("no hardcoded preview secret", () => {
  const dir = dirname(fileURLToPath(import.meta.url));
  const files = readdirSync(dir).filter((f) => /\.tsx?$/.test(f) && !f.endsWith(".test.ts"));
  it("auth sources contain no secret-like string literal", () => {
    const literal = /["'`][A-Za-z0-9_-]{40,}["'`]/;
    for (const f of files) {
      const src = readFileSync(join(dir, f), "utf8");
      assert.ok(!literal.test(src), `${f} contains a secret-like literal`);
      assert.ok(!/PREVIEW_CLIENT_SECRET\s*=/.test(src), `${f} assigns PREVIEW_CLIENT_SECRET`);
    }
  });
});