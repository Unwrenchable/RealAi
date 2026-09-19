/** Shared chat UI types for RealAI frontend */

export type Role = "system" | "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: Role;
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
}

export interface ModelOption {
  id: string;
  label: string;
  description: string;
  badge?: string;
}

export interface Settings {
  model: string;
  systemPrompt: string;
  temperature: number;
  maxTokens: number;
  apiKey: string;
  stream?: boolean;
}

/** Public RealAI model ids — mapped by orchestrator model_catalog to Vulkan GGUF */
export const DEFAULT_MODELS: ModelOption[] = [
  {
    id: "realai-default-coder",
    label: "RealAI Coder",
    description: "Local Qwen2.5-Coder 7B on AMD Vulkan (default)",
    badge: "Local",
  },
  {
    id: "realai-default",
    label: "RealAI Default",
    description: "General local instruct model",
    badge: "Local",
  },
  {
    id: "qwen2.5-coder-7b-instruct-q5_k_m.gguf",
    label: "Qwen2.5 Coder (raw GGUF)",
    description: "Direct backend filename",
  },
];

export const DEFAULT_SETTINGS: Settings = {
  model: "realai-default-coder",
  systemPrompt: "",
  temperature: 0.7,
  maxTokens: 2048,
  apiKey: "",
  stream: false,
};
