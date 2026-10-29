/**
 * Broker client credential resolution (server-only, dependency-free so it can be
 * unit-tested without Better Auth / pg).
 *
 * Fail-closed rules:
 *   - Auth explicitly off (`VITE_AUTH_ENABLED=false`): no credentials, no throw.
 *   - `GROK_AUTH_CLIENT_ID` + `GROK_AUTH_CLIENT_SECRET` set: use them (deployed).
 *   - Production and either is unset: THROW at startup. There is no fallback to
 *     the shared preview client in production.
 *   - Otherwise (sandbox live preview / local dev): use the shared preview client
 *     only when `GROK_PREVIEW_CLIENT_SECRET` is set; if it is unset, preview
 *     sign-in is disabled (authConfigured = false). The secret is never baked
 *     into source.
 *
 * "Production" = `VERCEL_ENV=production`, or `NODE_ENV=production` with an
 * explicit `BETTER_AUTH_URL` (the deployer always injects one; the sandbox
 * preview never has a fixed URL).
 */
export type EnvLike = Record<string, string | undefined>;

export const PREVIEW_CLIENT_ID = "grok_preview";
export const PREVIEW_CLIENT_SECRET_ENV = "GROK_PREVIEW_CLIENT_SECRET";

export type GrokCredentials =
  | { mode: "off"; clientId: undefined; clientSecret: undefined }
  | { mode: "deployed" | "preview"; clientId: string; clientSecret: string }
  | { mode: "preview-disabled"; clientId: undefined; clientSecret: undefined };

/** Read an env var, treating empty/whitespace as unset. */
export function readEnv(env: EnvLike, key: string): string | undefined {
  const value = env[key]?.trim();
  return value ? value : undefined;
}

export function isProductionEnv(env: EnvLike): boolean {
  if (readEnv(env, "VERCEL_ENV") === "production") return true;
  return readEnv(env, "NODE_ENV") === "production" && Boolean(readEnv(env, "BETTER_AUTH_URL"));
}

export function resolveGrokCredentials(env: EnvLike): GrokCredentials {
  if (readEnv(env, "VITE_AUTH_ENABLED") === "false") {
    return { mode: "off", clientId: undefined, clientSecret: undefined };
  }
  const clientId = readEnv(env, "GROK_AUTH_CLIENT_ID");
  const clientSecret = readEnv(env, "GROK_AUTH_CLIENT_SECRET");
  if (clientId && clientSecret) return { mode: "deployed", clientId, clientSecret };

  if (isProductionEnv(env)) {
    const missing = [
      clientId ? null : "GROK_AUTH_CLIENT_ID",
      clientSecret ? null : "GROK_AUTH_CLIENT_SECRET",
    ].filter(Boolean);
    throw new Error(
      `[auth] refusing to start: ${missing.join(" and ")} must be set in production ` +
        `(no fallback to the shared preview client). Set VITE_AUTH_ENABLED=false to run without auth.`,
    );
  }

  const previewSecret = readEnv(env, PREVIEW_CLIENT_SECRET_ENV);
  if (!previewSecret) {
    return { mode: "preview-disabled", clientId: undefined, clientSecret: undefined };
  }
  return { mode: "preview", clientId: PREVIEW_CLIENT_ID, clientSecret: previewSecret };
}