/**
 * Startup guard (server-only, dependency-free): refuse to boot if a forbidden
 * Better Auth plugin is registered. `magic-link` and `oauth-proxy` sit behind
 * Dependabot criticals (OAuth-state account takeover) and must never be
 * enabled. Complements the CI guard `scripts/check-auth-plugins.mjs`, which
 * also bans their module paths repo-wide.
 */
export const FORBIDDEN_PLUGIN_IDS = ["magic-link", "oauth-proxy"] as const;

export function assertNoForbiddenPlugins(
  plugins: ReadonlyArray<{ id?: string } | null | undefined> | undefined,
): void {
  const found = (plugins ?? [])
    .map((p) => p?.id)
    .filter((id): id is string =>
      typeof id === "string" && (FORBIDDEN_PLUGIN_IDS as readonly string[]).includes(id),
    );
  if (found.length) {
    throw new Error(`[auth] refusing to start: forbidden Better Auth plugin(s) registered: ${found.join(", ")}`);
  }
}