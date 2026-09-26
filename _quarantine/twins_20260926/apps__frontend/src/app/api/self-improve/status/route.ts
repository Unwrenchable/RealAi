import { NextResponse } from "next/server";
import { getEnv } from "@/lib/env";

export const dynamic = "force-dynamic";

export async function GET() {
  const env = getEnv();
  const base = env.NEXT_PUBLIC_API_URL.replace(/\/+$/, "");
  try {
    const res = await fetch(`${base}/v1/self-improve/status`, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e: any) {
    return NextResponse.json(
      {
        error: "orchestrator_unreachable",
        hint: "Start: python -m realai.v3_orchestrator --port 8001 with REALAI_SELF_IMPROVE=true",
        detail: String(e?.message || e),
      },
      { status: 502 }
    );
  }
}
