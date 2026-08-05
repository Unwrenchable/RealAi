export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
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
}

export const DEFAULT_MODELS: ModelOption[] = [
  {
    id: "realai-2.0",
    label: "RealAI 2.0",
    description: "The default RealAI model — fast and capable.",
    badge: "Default",
  },
  {
    id: "gpt-4o",
    label: "GPT-4o",
    description: "OpenAI's most capable multimodal model.",
  },
  {
    id: "gpt-4o-mini",
    label: "GPT-4o mini",
    description: "Fast and affordable OpenAI model.",
  },
  {
    id: "claude-3-5-sonnet-20241022",
    label: "Claude 3.5 Sonnet",
    description: "Anthropic's best balance of speed and intelligence.",
  },
  {
    id: "gemini-1.5-pro",
    label: "Gemini 1.5 Pro",
    description: "Google's long-context multimodal model.",
  },
];

export const DEFAULT_SETTINGS: Settings = {
  model: DEFAULT_MODELS[0].id,
  systemPrompt: "",
  temperature: 0.7,
  maxTokens: 2048,
  apiKey: "",
};
