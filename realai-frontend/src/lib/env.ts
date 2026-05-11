import { z } from "zod";

function normalizeApiBaseUrl(url: string): string {
  const trimmed = url.trim().replace(/\/+$/, "");
  return trimmed.endsWith("/v1") ? trimmed.slice(0, -3) : trimmed;
}

const envSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url().transform(normalizeApiBaseUrl),
});

export function getEnv() {
  return envSchema.parse({
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL ??
      process.env.REALAI_API_BASE ??
      process.env.NEXT_PUBLIC_REALAI_API_BASE,
  });
}