import { NextRequest, NextResponse } from "next/server";
import type { ChatRequest } from "@/lib/realai";

const RAW_BACKEND =
  process.env.REALAI_API_BASE ??
  process.env.NEXT_PUBLIC_REALAI_API_BASE ??
  (process.env.NODE_ENV === "development" ? "http://localhost:8000" : "");

function normalizeBackendBaseUrl(url: string): string {
  const trimmed = url.trim().replace(/\/+$/, "");
  return trimmed.endsWith("/v1") ? trimmed.slice(0, -3) : trimmed;
}

const BACKEND = normalizeBackendBaseUrl(RAW_BACKEND);

export async function POST(req: NextRequest) {
  try {
    if (!BACKEND) {
      return NextResponse.json(
        {
          error:
            "Backend URL is not configured. Set REALAI_API_BASE (preferred) or NEXT_PUBLIC_REALAI_API_BASE.",
        },
        { status: 500 }
      );
    }

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

    const backendRes = await fetch(`${BACKEND}/v1/chat/completions`, {
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
