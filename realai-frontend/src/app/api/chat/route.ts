import { NextRequest, NextResponse } from "next/server";
import { getEnv } from "@/lib/env";
import type { ChatRequest } from "@/lib/realai";

export async function POST(req: NextRequest) {
  try {
    const env = getEnv();
    const body: ChatRequest = await req.json();
    const { messages, settings } = body;

    // Build the message array, optionally prepending the system prompt.
    const allMessages =
      settings.systemPrompt?.trim()
        ? [
            { role: "system", content: settings.systemPrompt.trim() },
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
        model: settings.model,
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
