export interface ProviderConfig {
  baseUrl: string;
  defaultModel: string;
  apiFormat: "openai" | "anthropic";
}

export const PROVIDER_CONFIGS: Record<string, ProviderConfig> = {
  openai: {
    baseUrl: "https://api.openai.com/v1",
    defaultModel: "gpt-4o-mini",
    apiFormat: "openai",
  },
  anthropic: {
    baseUrl: "https://api.anthropic.com",
    defaultModel: "claude-3-5-haiku-20241022",
    apiFormat: "anthropic",
  },
  grok: {
    baseUrl: "https://api.x.ai/v1",
    defaultModel: "grok-beta",
    apiFormat: "openai",
  },
  gemini: {
    baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai",
    defaultModel: "gemini-1.5-flash",
    apiFormat: "openai",
  },
  openrouter: {
    baseUrl: "https://openrouter.ai/api/v1",
    defaultModel: "openai/gpt-4o-mini",
    apiFormat: "openai",
  },
  mistral: {
    baseUrl: "https://api.mistral.ai/v1",
    defaultModel: "mistral-small-latest",
    apiFormat: "openai",
  },
  together: {
    baseUrl: "https://api.together.xyz/v1",
    defaultModel: "meta-llama/Llama-3-8b-chat-hf",
    apiFormat: "openai",
  },
  deepseek: {
    baseUrl: "https://api.deepseek.com/v1",
    defaultModel: "deepseek-chat",
    apiFormat: "openai",
  },
  perplexity: {
    baseUrl: "https://api.perplexity.ai",
    defaultModel: "llama-3.1-sonar-small-128k-online",
    apiFormat: "openai",
  },
};

export function getProviderConfig(provider: string): ProviderConfig | undefined {
  return PROVIDER_CONFIGS[provider.toLowerCase()];
}

export function detectProviderFromKey(apiKey: string): string | undefined {
  if (apiKey.startsWith("sk-ant-")) return "anthropic";
  if (apiKey.startsWith("sk-or-")) return "openrouter";
  if (apiKey.startsWith("sk-")) return "openai";
  if (apiKey.startsWith("xai-")) return "grok";
  return undefined;
}
