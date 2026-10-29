/**
 * Broker client credential resolution (server-only, dependency-free so it can be
 * unit-tested without Better Auth / pg).
 *
 * "Production" (values compared case-insensitively, whitespace = unset):
 *   - `NODE_ENV=production`, OR
 *   - any `BETTER_AUTH_URL` is set, OR
 *   - `VERCEL_ENV=production` (cannot be overridden),
 *   unless the explicit sandbox flag `REALAI_AUTH_SANDBOX` is `1`/`true`/`yes`
 *   (sandbox live preview / local `vite preview`). The sandbox flag never
 *   overrides `VERCEL_ENV=production`.
 *
 * Fail-closed rules:
 *   - Auth explicitly off (`VITE_AUTH_ENABLED=false`): no credentials, no throw.
 *   - Production: THROW at startup unless `GROK_AUTH_CLIENT_ID`,
 *     `GROK_AUTH_CLIENT_SECRET` and `BETTER_AUTH_SECRET` are all set. Production
 *     never falls back to the shared preview client, so "preview disabled" in
 *     production is a boot failure, not a silent auth-off.
 *   - Non-production: injected creds if both set; else the shared preview client
 *     only when `GROK_PREVIEW_CLIENT_SECRET` is set; else preview sign-in is
 *     disabled (authConfigured = false). No secret is baked into source.
 */
export type EnvLike = Record<string, string | undefined>;

export const PREVIEW_CLIENT_ID = "grok_preview";
export const PREVIEW_CLIENT_SECRET_ENV = "GROK_PREVIEW_CLIENT_SECRET";
export const SANDBOX_FLAG_ENV = "REALAI_AUTH_SANDBOX";

export type GrokCredentials =
  | { mode: "off"; clientId: undefined; clientSecret: undefined }
  | { mode: "deployed" | "preview"; clientId: string; clientSecret: string }
  | { mode: "preview-disabled"; clientId: undefined; clientSecret: undefined };

/** Read an env var, treating empty/whitespace as unset. */
export function readEnv(env: EnvLike, key: string): string | undefined {
  const value = env[key]?.trim();
  return value ? value : undefined;
}

/** Lower-cased value for case-insensitive comparisons. */
function lower(env: EnvLike, key: string): string | undefined {
  return readEnv(env, key)?.toLowerCase();
}

export function isSandboxEnv(env: EnvLike): boolean {
  return ["1", "true", "yes"].includes(lower(env, SANDBOX_FLAG_ENV) ?? "");
}

export function isAuthDisabled(env: EnvLike): boolean {
  return lower(env, "VITE_AUTH_ENABLED") === "false";
}

export function isProductionEnv(env: EnvLike): boolean {
  if (lower(env, "VERCEL_ENV") === "production") return true;
  if (isSandboxEnv(env)) return false;
  return lower(env, "NODE_ENV") === "production" || Boolean(readEnv(env, "BETTER_AUTH_URL"));
}

export function resolveGrokCredentials(env: EnvLike): GrokCredentials {
  if (isAuthDisabled(env)) {
    return { mode: "off", clientId: undefined, clientSecret: undefined };
  }
  const clientId = readEnv(env, "GROK_AUTH_CLIENT_ID");
  const clientSecret = readEnv(env, "GROK_AUTH_CLIENT_SECRET");

  if (isProductionEnv(env)) {
    const missing = [
      clientId ? null : "GROK_AUTH_CLIENT_ID",
      clientSecret ? null : "GROK_AUTH_CLIENT_SECRET",
      readEnv(env, "BETTER_AUTH_SECRET") ? null : "BETTER_AUTH_SECRET",
    ].filter(Boolean);
    if (missing.length) {
      throw new Error(
        `[auth] refusing to start: ${missing.join(", ")} must be set in production ` +
          `(no preview fallback). Set VITE_AUTH_ENABLED=false to run without auth, ` +
          `or ${SANDBOX_FLAG_ENV}=1 for a sandbox preview.`,
      );
    }
    return { mode: "deployed", clientId: clientId as string, clientSecret: clientSecret as string };
  }

  if (clientId && clientSecret) return { mode: "deployed", clientId, clientSecret };
  const previewSecret = readEnv(env, PREVIEW_CLIENT_SECRET_ENV);
  if (!previewSecret) {
    return { mode: "preview-disabled", clientId: undefined, clientSecret: undefined };
  }
  return { mode: "preview", clientId: PREVIEW_CLIENT_ID, clientSecret: previewSecret };
}