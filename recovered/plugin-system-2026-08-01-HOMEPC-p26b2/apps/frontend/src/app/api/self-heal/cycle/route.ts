import { NextRequest, NextResponse } from "next/server";
import { getEnv } from "@/lib/env";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const env = getEnv();
  const base = env.NEXT_PUBLIC_API_URL.replace(/\/+$/, "");
  let body: { apply?: boolean } = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  try {
    const res = await fetch(`${base}/v1/self-heal/cycle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ apply: Boolean(body.apply) }),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e: any) {
    return NextResponse.json(
      {
        error: "orchestrator_unreachable",
        detail: String(e?.message || e),
      },
      { status: 502 }
    );
  }
}
