import { NextResponse } from "next/server";
import { getEnv } from "@/lib/env";

export const dynamic = "force-dynamic";

export async function GET() {
  const env = getEnv();
  const base = env.NEXT_PUBLIC_API_URL.replace(/\/+$/, "");
  try {
    const res = await fetch(`${base}/v1/agents`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e: any) {
    return NextResponse.json(
      { error: "orchestrator_unreachable", detail: String(e?.message || e) },
      { status: 502 }
    );
  }
}
