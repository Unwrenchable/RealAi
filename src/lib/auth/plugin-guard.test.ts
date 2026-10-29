import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { assertNoForbiddenPlugins } from "./plugin-guard.ts";

describe("assertNoForbiddenPlugins", () => {
  it("throws on magic-link", () => {
    assert.throws(() => assertNoForbiddenPlugins([{ id: "bearer" }, { id: "magic-link" }]), /magic-link/);
  });
  it("throws on oauth-proxy", () => {
    assert.throws(() => assertNoForbiddenPlugins([{ id: "oauth-proxy" }]), /oauth-proxy/);
  });
  it("passes for allowed plugins and empty/undefined lists", () => {
    assertNoForbiddenPlugins([{ id: "bearer" }, { id: "generic-oauth" }, {}, null]);
    assertNoForbiddenPlugins([]);
    assertNoForbiddenPlugins(undefined);
  });
});

describe("server.ts wiring", () => {
  const src = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "server.ts"), "utf8");
  it("runs the startup plugin guard on auth.options.plugins", () => {
    assert.match(src, /assertNoForbiddenPlugins\(auth\.options\.plugins\)/);
  });
  it("requires a verified local email before account linking", () => {
    assert.match(src, /requireLocalEmailVerified:\s*true/);
    assert.doesNotMatch(src, /requireLocalEmailVerified:\s*false/);
  });
});