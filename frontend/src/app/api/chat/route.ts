import { NextRequest, NextResponse } from "next/server";
import { getEnv } from "@/lib/env";
import { rateLimit } from "@/lib/ratelimit";
import type { ChatRequest } from "@/lib/realai";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function POST(req: NextRequest) {
  try {
    // Rate limiting
    const clientIp = req.headers.get("x-forwarded-for") || req.headers.get("x-real-ip") || "unknown";
    if (!rateLimit(clientIp)) {
      return NextResponse.json(
        { error: "Rate limit exceeded" },
        { status: 429, headers: { "Retry-After": "60" } }
      );
    }

    const env = getEnv();
    const body: ChatRequest = await req.json();
    const { messages, settings } = body;

    // Coerce cloud model ids onto local RealAI defaults (backend also enforces).
    const rawModel = String(settings?.model || "realai-default").toLowerCase();
    const cloudish = ["grok", "gpt-", "claude", "gemini", "chatgpt"].some(
      (p) => rawModel.startsWith(p) || rawModel.includes(p)
    );
    const model = cloudish ? "realai-default" : settings.model || "realai-default";

    // Omit empty/default "helpful assistant" system prompts — backend injects RealAI Bot.
    const sys = (settings.systemPrompt || "").trim();
    const sysLower = sys.toLowerCase();
    const dropSystem =
      !sys ||
      sysLower.includes("helpful ai assistant") ||
      sysLower.includes("helpful assistant");
    const allMessages =
      !dropSystem
        ? [
            { role: "system", content: sys },
            ...messages,
          ]
        : messages;

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    // Prefer the server-side env key; fall back to the user-supplied one.
    const apiKey = process.env.REALAI_API_KEY || settings.apiKey;
    if (apiKey) {
      headers["Authorization"] = `Bearer ${apiKey}`;
    }

    const backendRes = await fetch(`${env.NEXT_PUBLIC_API_URL}/v1/chat/completions`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        model,
        messages: allMessages,
        temperature: settings.temperature,
        max_tokens: settings.maxTokens,
        stream: Boolean((settings as any).stream),
      }),
    });

    const raw = await backendRes.text();
    let data: any = null;
    try {
      data = raw ? JSON.parse(raw) : null;
    } catch {
      data = null;
    }

    if (!backendRes.ok) {
      return NextResponse.json(
        {
          error:
            data?.error?.message ??
            (typeof data?.error === "string" ? data.error : null) ??
            `Backend error (${backendRes.status})`,
        },
        { status: backendRes.status }
      );
    }

    if (!data) {
      return NextResponse.json(
        { error: "Backend returned non-JSON response." },
        { status: 502 }
      );
    }

    return NextResponse.json(data);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
