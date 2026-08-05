export type MessageRole = "user" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: Date;
  model: string;
  agentId?: string;
}

export interface ModelOption {
  id: string;
  label: string;
  description: string;
  badge?: string;
}

export interface AgentOption {
  id: string;
  name: string;
  description?: string;
  type?: string;
  capabilities?: string[];
  preferredProfile?: string;
  riskLevel?: string;
}

export type ComputeMode = "auto" | "gpu" | "cpu" | "hybrid";

export interface Settings {
  model: string;
  systemPrompt: string;
  temperature: number;
  maxTokens: number;
  apiKey: string;
  agentId: string;
  stream: boolean;
  autoRoute: boolean;
  computeMode: ComputeMode;
}

export const DEFAULT_SETTINGS: Settings = {
  model: "qwen2.5-coder-7b-instruct-q5_k_m.gguf",
  systemPrompt: "",
  temperature: 0.7,
  maxTokens: 2048,
  apiKey: "",
  agentId: "",
  stream: false,
  autoRoute: true,
  computeMode: "auto",
};

const MODEL_META: Record<string, Omit<ModelOption, "id">> = {
  realai: {
    label: "RealAI",
    description: "Default orchestration â€” routes to available backends",
    badge: "default",
  },
  "realai-hive": {
    label: "RealAI Hive",
    description: "Multi-agent coordinator for complex tasks",
    badge: "multi-agent",
  },
  "realai-overseer": {
    label: "RealAI Overseer",
    description: "Engineering-focused guidance and planning",
    badge: "overseer",
  },
  "realai-1.0": {
    label: "RealAI 1.0",
    description: "Branded local model slot (when weights are available)",
  },
  "realai-embed": {
    label: "RealAI Embed",
    description: "Embeddings endpoint",
  },
};

export const DEFAULT_MODELS: ModelOption[] = [
  { id: "realai", ...MODEL_META.realai },
  { id: "realai-hive", ...MODEL_META["realai-hive"] },
  { id: "realai-overseer", ...MODEL_META["realai-overseer"] },
  { id: "realai-1.0", ...MODEL_META["realai-1.0"] },
];

export function modelOptionsFromIds(ids: string[]): ModelOption[] {
  const seen = new Set<string>();
  const options: ModelOption[] = [];
  for (const id of ids) {
    const key = id.trim();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    const meta = MODEL_META[key];
    options.push(
      meta
        ? { id: key, ...meta }
        : {
            id: key,
            label: key,
            description: "Available on your RealAI provider",
          }
    );
  }
  return options.length > 0 ? options : DEFAULT_MODELS;
}
