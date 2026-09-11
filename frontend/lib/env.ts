/**
 * Server-side env for Next.js route handlers.
 * Prefer orchestrator :8001 (not raw Vulkan :8080).
 */

export type AppEnv = {
  NEXT_PUBLIC_API_URL: string;
  REALAI_API_KEY: string;
};

export function getEnv(): AppEnv {
  const base =
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.REALAI_API_BASE ||
    "http://127.0.0.1:8001";

  return {
    NEXT_PUBLIC_API_URL: base.replace(/\/$/, ""),
    REALAI_API_KEY: process.env.REALAI_API_KEY || "local",
  };
}
