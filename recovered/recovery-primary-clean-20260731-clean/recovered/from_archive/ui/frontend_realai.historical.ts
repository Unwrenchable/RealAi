import type { ChatMessage, Settings } from "@/lib/types";

export interface ChatRequest {
  messages: Array<{ role: string; content: string }>;
  settings: Settings;
}

/**
 * Send a list of messages to the RealAI backend via the Next.js proxy route
 * and return the assistant's reply text.
 */
export async function sendMessage(
  messages: ChatMessage[],
  settings: Settings
): Promise<string> {
  const payload: ChatRequest = {
    messages: messages.map((m) => ({ role: m.role, content: m.content })),
    settings,
  };

  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  let data: any;
  try {
    data = await res.json();
  } catch {
    throw new Error(`Backend returned a non-JSON response (HTTP ${res.status}).`);
  }

  if (!res.ok) {
    throw new Error(
      data?.error ?? `Request failed with status ${res.status}`
    );
  }

  // Support both OpenAI chat-completions format (choices[0].message.content)
  // and legacy completions format (choices[0].text).
  const content: string | undefined =
    data?.choices?.[0]?.message?.content ??
    data?.choices?.[0]?.text;

  if (typeof content !== "string") {
    throw new Error("Unexpected response format from backend.");
  }

  return content;
}
