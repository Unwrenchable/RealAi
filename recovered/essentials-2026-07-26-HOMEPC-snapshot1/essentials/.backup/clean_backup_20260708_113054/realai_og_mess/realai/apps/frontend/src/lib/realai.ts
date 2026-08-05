import type { ChatMessage, Settings } from "@/lib/types";
import type { AgentOption } from "@/lib/types";

export interface ChatRequest {
  messages: Array<{ role: string; content: string }>;
  settings: Settings;
  userId?: string;
  sessionId?: string;
}

function buildAgentSystemPrefix(agent: AgentOption | null): string {
  if (!agent) return "";
  const lines = [
    `You are operating as the "${agent.name}" agent (${agent.id}).`,
  ];
  if (agent.description?.trim()) {
    lines.push(agent.description.trim());
  }
  if (agent.capabilities?.length) {
    lines.push("Core capabilities:");
    for (const cap of agent.capabilities.slice(0, 8)) {
      lines.push(`- ${cap}`);
    }
  }
  lines.push("Stay in character and follow the agent's scope.");
  return lines.join("\n");
}

/** Drop failed turns (user message with no assistant reply) before a new send. */
export function buildCompletionMessages(
  history: ChatMessage[],
  newUser: ChatMessage
): Array<{ role: string; content: string }> {
  const trimmed = [...history];
  while (trimmed.length > 0 && trimmed[trimmed.length - 1].role === "user") {
    trimmed.pop();
  }
  return [...trimmed, newUser].map((m) => ({
    role: m.role,
    content: m.content,
  }));
}

export function mergeSystemPrompt(
  settings: Settings,
  agent: AgentOption | null
): string {
  const parts: string[] = [];
  const agentPrefix = settings.agentId ? buildAgentSystemPrefix(agent) : "";
  if (agentPrefix) parts.push(agentPrefix);
  if (settings.systemPrompt.trim()) parts.push(settings.systemPrompt.trim());
  return parts.join("\n\n");
}

export async function sendMessage(
  messages: ChatMessage[],
  settings: Settings,
  signal?: AbortSignal,
  agent: AgentOption | null = null,
  options?: { userId?: string; sessionId?: string }
): Promise<string> {
  const last = messages[messages.length - 1];
  const history = last?.role === "user" ? messages.slice(0, -1) : messages;
  const completionMessages =
    last?.role === "user"
      ? buildCompletionMessages(history, last)
      : messages.map((m) => ({ role: m.role, content: m.content }));

  const payload: ChatRequest = {
    messages: completionMessages,
    settings: {
      ...settings,
      systemPrompt: mergeSystemPrompt(settings, agent),
    },
    userId: options?.userId,
    sessionId: options?.sessionId,
  };

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (options?.userId) headers["X-RealAI-User-Id"] = options.userId;
  if (options?.sessionId) headers["X-RealAI-Session-Id"] = options.sessionId;
  if (settings.agentId) headers["X-RealAI-Agent-Id"] = settings.agentId;
  if (settings.computeMode) headers["X-RealAI-Compute-Mode"] = settings.computeMode;
  headers["X-RealAI-Memory"] = "on";

  const timeoutMs = 180_000;
  const timeout =
    typeof AbortSignal !== "undefined" && "timeout" in AbortSignal
      ? (AbortSignal as typeof AbortSignal & { timeout(ms: number): AbortSignal })
          .timeout(timeoutMs)
      : null;
  const signals: AbortSignal[] = [];
  if (signal) signals.push(signal);
  if (timeout) signals.push(timeout);

  let combined: AbortSignal | undefined;
  if (signals.length === 1) {
    combined = signals[0];
  } else if (signals.length > 1 && typeof AbortSignal.any === "function") {
    combined = AbortSignal.any(signals);
  } else if (signal) {
    combined = signal;
  }

  const res = await fetch("/api/chat", {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
    signal: combined,
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(
      typeof data?.error === "string"
        ? data.error
        : data?.error?.message ?? `Request failed (${res.status})`
    );
  }

  const content = data?.choices?.[0]?.message?.content;
  if (typeof content === "string" && content.length > 0) {
    return content;
  }

  throw new Error("Empty response from RealAI provider.");
}