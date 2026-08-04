import type {
  RealAIClientConfig,
  Message,
  ChatOptions,
  ChatResponse,
  ImageOptions,
  ImageResponse,
  ImageAnalysisOptions,
  ImageAnalysisResponse,
  CodeOptions,
  CodeResponse,
  EmbeddingsOptions,
  EmbeddingsResponse,
  TranslationOptions,
  TranslationResponse,
  WebResearchOptions,
  WebResearchResponse,
} from "./types";
import { detectProviderFromKey, getProviderConfig } from "./providers";

export class RealAIError extends Error {
  readonly statusCode?: number;
  readonly type?: string;
  readonly code?: string;

  constructor(message: string, statusCode?: number, type?: string, code?: string) {
    super(message);
    this.name = "RealAIError";
    this.statusCode = statusCode;
    this.type = type;
    this.code = code;
  }
}

export class RealAIClient {
  private readonly apiKey: string | undefined;
  private readonly baseUrl: string;
  private readonly provider: string;
  private readonly defaultModel: string;
  private readonly timeout: number;
  private readonly defaultHeaders: Record<string, string>;

  constructor(config: RealAIClientConfig = {}) {
    this.apiKey = config.apiKey ?? process.env["REALAI_API_KEY"];
    this.timeout = config.timeout ?? 30_000;
    this.defaultHeaders = config.defaultHeaders ?? {};

    const detectedProvider =
      config.provider ??
      (this.apiKey ? detectProviderFromKey(this.apiKey) : undefined) ??
      "openai";

    this.provider = detectedProvider;

    const providerConfig = getProviderConfig(this.provider);
    this.baseUrl = config.baseUrl ?? providerConfig?.baseUrl ?? "http://localhost:8000";
    this.defaultModel = config.model ?? providerConfig?.defaultModel ?? "gpt-4o-mini";
  }

  private buildHeaders(extra: Record<string, string> = {}): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...this.defaultHeaders,
      ...extra,
    };
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }
    return headers;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    let response: Response;
    try {
      response = await fetch(url, {
        method,
        headers: this.buildHeaders(),
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      throw new RealAIError(`Network error: ${msg}`);
    } finally {
      clearTimeout(timer);
    }

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}`;
      try {
        const errData = (await response.json()) as { error?: { message?: string; type?: string; code?: string } };
        errorMessage = errData?.error?.message ?? errorMessage;
        throw new RealAIError(errorMessage, response.status, errData?.error?.type, errData?.error?.code);
      } catch (e) {
        if (e instanceof RealAIError) throw e;
        throw new RealAIError(errorMessage, response.status);
      }
    }

    return response.json() as Promise<T>;
  }

  /**
   * Send a chat completion request.
   */
  async chat(messages: Message[], options: ChatOptions = {}): Promise<ChatResponse> {
    const payload: Record<string, unknown> = {
      model: options.model ?? this.defaultModel,
      messages: options.systemPrompt
        ? [{ role: "system", content: options.systemPrompt }, ...messages]
        : messages,
    };

    if (options.temperature !== undefined) payload["temperature"] = options.temperature;
    if (options.maxTokens !== undefined) payload["max_tokens"] = options.maxTokens;
    if (options.topP !== undefined) payload["top_p"] = options.topP;
    if (options.stop !== undefined) payload["stop"] = options.stop;

    return this.request<ChatResponse>("POST", "/v1/chat/completions", payload);
  }

  /**
   * Generate an image from a text prompt.
   */
  async generateImage(prompt: string, options: ImageOptions = {}): Promise<ImageResponse> {
    return this.request<ImageResponse>("POST", "/v1/images/generations", {
      prompt,
      model: options.model ?? "dall-e-3",
      size: options.size ?? "1024x1024",
      quality: options.quality ?? "standard",
      n: options.n ?? 1,
      ...(options.style ? { style: options.style } : {}),
    });
  }

  /**
   * Analyze an image at the given URL with an optional prompt.
   */
  async analyzeImage(
    imageUrl: string,
    prompt = "Describe this image in detail.",
    options: ImageAnalysisOptions = {}
  ): Promise<ImageAnalysisResponse> {
    const res = await this.request<ChatResponse>("POST", "/v1/chat/completions", {
      model: options.model ?? "gpt-4o",
      max_tokens: options.maxTokens ?? 1024,
      messages: [
        {
          role: "user",
          content: [
            { type: "text", text: prompt },
            { type: "image_url", image_url: { url: imageUrl } },
          ],
        },
      ],
    });

    return {
      description: res.choices[0]?.message?.content ?? "",
      model: res.model,
      tokens: res.usage?.total_tokens ?? 0,
    };
  }

  /**
   * Generate code for the given prompt and language.
   */
  async generateCode(
    prompt: string,
    language = "python",
    options: CodeOptions = {}
  ): Promise<CodeResponse> {
    const systemPrompt = `You are an expert ${language} programmer. Return ONLY the code without explanation unless asked. Use clean, idiomatic ${language}.`;

    const res = await this.request<ChatResponse>("POST", "/v1/chat/completions", {
      model: options.model ?? this.defaultModel,
      temperature: options.temperature ?? 0.2,
      max_tokens: options.maxTokens ?? 2048,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: prompt },
      ],
    });

    const content = res.choices[0]?.message?.content ?? "";
    const codeMatch = content.match(/```(?:\w+)?\n([\s\S]*?)```/);
    const code = codeMatch ? codeMatch[1].trim() : content.trim();

    return {
      code,
      language,
      model: res.model,
    };
  }

  /**
   * Generate text embeddings for one or more inputs.
   */
  async generateEmbeddings(
    texts: string | string[],
    options: EmbeddingsOptions = {}
  ): Promise<EmbeddingsResponse> {
    return this.request<EmbeddingsResponse>("POST", "/v1/embeddings", {
      model: options.model ?? "text-embedding-3-small",
      input: texts,
    });
  }

  /**
   * Translate text into the target language.
   */
  async translate(
    text: string,
    targetLanguage: string,
    options: TranslationOptions = {}
  ): Promise<TranslationResponse> {
    const sourceLanguage = options.sourceLanguage ?? "auto-detect";
    const systemPrompt = `You are a professional translator. Translate the user's text to ${targetLanguage}. Return ONLY the translated text, nothing else.`;

    const res = await this.request<ChatResponse>("POST", "/v1/chat/completions", {
      model: options.model ?? this.defaultModel,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: text },
      ],
    });

    return {
      translatedText: res.choices[0]?.message?.content ?? "",
      sourceLanguage,
      targetLanguage,
      model: res.model,
    };
  }

  /**
   * Perform web research on a query and return a summary with sources.
   */
  async webResearch(
    query: string,
    options: WebResearchOptions = {}
  ): Promise<WebResearchResponse> {
    const systemPrompt = `You are a research assistant. For the given query, provide:
1. A comprehensive summary (2-3 paragraphs)
2. Up to ${options.maxResults ?? 5} relevant findings as a JSON array

Respond in this exact JSON format:
{
  "summary": "<summary text>",
  "results": [
    { "title": "<title>", "snippet": "<snippet>", "relevance": 0.9 }
  ]
}`;

    const res = await this.request<ChatResponse>("POST", "/v1/chat/completions", {
      model: options.model ?? this.defaultModel,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: query },
      ],
    });

    const content = res.choices[0]?.message?.content ?? "{}";
    let parsed: { summary?: string; results?: WebResearchResponse["results"] };
    try {
      const jsonMatch = content.match(/\{[\s\S]*\}/);
      parsed = jsonMatch ? (JSON.parse(jsonMatch[0]) as typeof parsed) : {};
    } catch {
      parsed = { summary: content, results: [] };
    }

    return {
      query,
      summary: parsed.summary ?? content,
      results: parsed.results ?? [],
      model: res.model,
    };
  }
}
