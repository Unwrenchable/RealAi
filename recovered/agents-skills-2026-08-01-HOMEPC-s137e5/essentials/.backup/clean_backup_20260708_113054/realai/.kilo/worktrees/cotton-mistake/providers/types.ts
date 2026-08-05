export interface ProviderMessage {
  role: string;
  content: string;
}

export interface ProviderModel {
  name: string;
  context: number;
  type: "text" | "vision" | "audio" | "embedding";
}

export interface ProviderCallOptions {
  model: string;
  messages: ProviderMessage[];
  temperature?: number;
  maxTokens?: number;
}

export interface Provider {
  id: string;
  name: string;
  models: ProviderModel[];
  call: (options: ProviderCallOptions) => Promise<string>;
}