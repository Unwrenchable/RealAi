import type { ChatMessage, Settings } from "./types";

export type ChatRequest = {
  messages: Array<{ role: string; content: string }>;
  settings: Settings;
};

/**
 * Browser → Next.js /api/chat → orchestrator :8001 → Vulkan :8080
 */
export async function sendMessage(
  messages: ChatMessage[],
  settings: Settings,
  signal?: AbortSignal
): Promise<string> {
  const payload: ChatRequest = {
    messages: messages.map((m) => ({ role: m.role, content: m.content })),
    settings,
  };

  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const err =
      (typeof data?.error === "string" && data.error) ||
      data?.error?.message ||
      `Chat failed (${res.status})`;
    throw new Error(err);
  }

  // OpenAI-compatible shape from orchestrator
  const content =
    data?.choices?.[0]?.message?.content ??
    data?.content ??
    data?.text ??
    "";

  if (!content) {
    throw new Error("Empty response from RealAI backend");
  }
  return String(content);
}
