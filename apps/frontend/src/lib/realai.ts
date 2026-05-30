import type { ChatMessage, Settings } from "@/lib/types";

export interface ChatRequest {
  messages: Array<{ role: string; content: string }>;
  settings: Settings;
}

const RAW_API_BASE =
  process.env.NEXT_PUBLIC_REALAI_API_BASE ??
  (process.env.NODE_ENV === "development" ? "http://localhost:8000" : "");

function normalizeApiBase(url: string): string {
  const trimmed = url.trim().replace(/\/+$/, "");
  return trimmed.endsWith("/v1") ? trimmed.slice(0, -3) : trimmed;
}

const API_BASE = normalizeApiBase(RAW_API_BASE);

export async function sendMessage(
  messages: ChatMessage[],
  settings: Settings,
  signal?: AbortSignal
): Promise<string> {
  if (!API_BASE) {
    throw new Error(
      "Backend URL is not configured. Set NEXT_PUBLIC_REALAI_API_BASE."
    );
  }

  const payload: ChatRequest = {
    messages: messages.map((m) => ({ role: m.role, content: m.content })),
    settings,
  };

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const apiKey = settings.apiKey.trim();
  if (apiKey) {
    headers.Authorization = `Bearer ${apiKey}`;
  }

  const res = await fetch(`${API_BASE}/v1/chat/completions`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
    signal,
  });

  let data: any;
  try {
    data = await res.json();
  } catch {
    throw new Error(`Backend returned a non-JSON response (HTTP ${res.status}).`);
  }

  if (!res.ok) {
    throw new Error(data?.error ?? `Request failed with status ${res.status}`);
  }

  const content: string | undefined =
    data?.choices?.[0]?.message?.content ?? data?.choices?.[0]?.text;

  if (typeof content !== "string") {
    throw new Error("Unexpected response format from backend.");
  }

  return content;
}
