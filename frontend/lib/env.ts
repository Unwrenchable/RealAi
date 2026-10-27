/**
 * Server-side env for Next.js route handlers.
 * On Vercel, NEXT_PUBLIC_API_URL must point at the public API (Render).
 * Self-host: NEXT_PUBLIC_REALAI_API is an alias; NEXT_PUBLIC_PROVIDER defaults to realai.
 * Local default is Hive :8001.
 */

export type AppEnv = {
  NEXT_PUBLIC_API_URL: string;
  NEXT_PUBLIC_PROVIDER: string;
  REALAI_API_KEY: string;
};

/** First ``REALAI_API_KEY`` segment. Do not log the return value. */
export function serviceApiKey(): string {
  const raw = process.env.REALAI_API_KEY || "";
  let part = raw.split(",")[0]?.trim() || "";
  if (
    part.length >= 2 &&
    (part[0] === '"' || part[0] === "'") &&
    part[0] === part[part.length - 1]
  ) {
    part = part.slice(1, -1).trim();
  }
  return part;
}

/**
 * Headers for the Render API.
 * The service key goes out as Bearer when it is the only key.
 * A different user-supplied provider key stays on Authorization, and the
 * service key moves to X-API-Key so both can be sent together.
 */
export function backendAuthHeaders(userKey?: string): Record<string, string> {
  const serviceKey = serviceApiKey();
  const pasted = (userKey || "").trim();
  if (serviceKey && pasted && pasted !== serviceKey) {
    return {
      "X-API-Key": serviceKey,
      Authorization: `Bearer ${pasted}`,
    };
  }
  const key = serviceKey || pasted;
  if (!key) return {};
  return { Authorization: `Bearer ${key}` };
}

export function getEnv(): AppEnv {
  const base =
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.NEXT_PUBLIC_REALAI_API ||
    process.env.REALAI_API_BASE ||
    (process.env.VERCEL ? "https://realai-api.onrender.com" : "http://127.0.0.1:8001");

  const provider = (process.env.NEXT_PUBLIC_PROVIDER || "realai").trim() || "realai";

  return {
    NEXT_PUBLIC_API_URL: base.replace(/\/$/, ""),
    NEXT_PUBLIC_PROVIDER: provider,
    REALAI_API_KEY: process.env.REALAI_API_KEY || "",
  };
}
