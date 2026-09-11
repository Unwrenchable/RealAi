/**
 * RealAI TypeScript SDK
 * Structured client for the RealAI platform surface.
 */

export interface RealAIOptions {
  apiKey?: string;
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
  stream?: boolean;
}

export interface EmbeddingsRequest {
  model: string;
  input: string[];
}

export interface TaskRequest {
  task: string;
  context?: string;
}

export class RealAI {
  private apiKey?: string;
  private baseUrl: string;

  constructor(opts: RealAIOptions = {}) {
    this.apiKey = opts.apiKey;
    this.baseUrl = (opts.baseUrl || process.env.REALAI_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const headers = new Headers(init?.headers || {});
    if (!headers.has("Content-Type") && init?.body) {
      headers.set("Content-Type", "application/json");
    }
    if (this.apiKey) {
      headers.set("Authorization", `Bearer ${this.apiKey}`);
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers,
    });

    if (!response.ok) {
      throw new Error(`RealAI API error: ${response.status} ${response.statusText}`);
    }

    return response.json() as Promise<T>;
  }

  chat(request: ChatCompletionRequest): Promise<any> {
    return this.request("/v1/chat/completions", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  embeddings(request: EmbeddingsRequest): Promise<any> {
    return this.request("/v1/embeddings", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  models(): Promise<any> {
    return this.request("/v1/models");
  }

  providers(): Promise<any> {
    return this.request("/v1/providers");
  }

  health(): Promise<any> {
    return this.request("/health");
  }

  createTask(request: TaskRequest): Promise<any> {
    return this.request("/v1/tasks", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  listTasks(): Promise<any> {
    return this.request("/v1/tasks");
  }
}
