import { z } from "zod";

const envSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url().optional(),
  REALAI_API_BASE: z.string().url().optional(),
  REALAI_API_KEY: z.string().optional(),
});

let cached: { NEXT_PUBLIC_API_URL: string; REALAI_API_KEY?: string } | null = null;

function normalizeBase(url: string): string {
  return url.replace(/\/+$/, "").replace(/\/v1$/i, "");
}

export function getEnv() {
  if (cached) return cached;

  const parsed = envSchema.safeParse({
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    REALAI_API_BASE: process.env.REALAI_API_BASE,
    REALAI_API_KEY: process.env.REALAI_API_KEY,
  });

  const fromEnv = parsed.success ? parsed.data : {};
  const base =
    fromEnv.REALAI_API_BASE ||
    fromEnv.NEXT_PUBLIC_API_URL ||
    "http://127.0.0.1:8001";

  cached = {
    NEXT_PUBLIC_API_URL: normalizeBase(base),
    REALAI_API_KEY: fromEnv.REALAI_API_KEY,
  };
  return cached;
}