import { NextResponse } from "next/server";
import { getEnv } from "@/lib/env";

export const dynamic = "force-dynamic";

export async function GET() {
  const env = getEnv();
  const base = env.NEXT_PUBLIC_API_URL.replace(/\/+$/, "");

  try {
    const headers: Record<string, string> = {};
    if (env.REALAI_API_KEY) {
      headers.Authorization = `Bearer ${env.REALAI_API_KEY}`;
    }

    const response = await fetch(`${base}/v1/models`, {
      cache: "no-store",
      headers,
    });
    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json(
        { error: data?.error?.message || "Failed to load models" },
        { status: response.status }
      );
    }
    return NextResponse.json(data);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Provider unreachable";
    return NextResponse.json({ error: message }, { status: 503 });
  }
}