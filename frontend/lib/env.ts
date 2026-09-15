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
