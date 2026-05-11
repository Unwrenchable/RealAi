/**
 * RealAI TypeScript SDK
 * OpenAI-compatible client for RealAI platform
 */

export interface RealAIOptions {
  apiKey: string;
  baseUrl?: string;
}

export interface ChatCompletionMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ChatCompletionRequest {
  model: string;
  messages: ChatCompletionMessage[];
  temperature?: number;
  max_tokens?: number;
}

export class RealAI {
  private apiKey: string;
  private baseUrl: string;

  constructor(opts: RealAIOptions) {
    this.apiKey = opts.apiKey;
    this.baseUrl = (opts.baseUrl || "https://api.realai.com").replace(/\/+$/, "");
  }

  async chat(request: ChatCompletionRequest): Promise<any> {
    const response = await fetch(`${this.baseUrl}/v1/chat/completions`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${this.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`RealAI API error: ${response.statusText}`);
    }

    return response.json();
  }

  async models(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/v1/models`, {
      headers: {
        "Authorization": `Bearer ${this.apiKey}`,
      },
    });

    if (!response.ok) {
      throw new Error(`RealAI API error: ${response.statusText}`);
    }

    return response.json();
  }
}
