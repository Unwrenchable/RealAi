// ---------------------------------------------------------------------------
// Message types
// ---------------------------------------------------------------------------

export type MessageRole = "user" | "assistant" | "system" | "tool";

export interface Message {
  role: MessageRole;
  content: string;
  name?: string;
}

// ---------------------------------------------------------------------------
// Chat completions
// ---------------------------------------------------------------------------

export interface ChatOptions {
  model?: string;
  temperature?: number;
  maxTokens?: number;
  topP?: number;
  stop?: string | string[];
  stream?: false;
  systemPrompt?: string;
}

export interface ChatChoice {
  index: number;
  message: { role: string; content: string };
  finish_reason: string;
}

export interface ChatUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface ChatResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: ChatChoice[];
  usage: ChatUsage;
}

// ---------------------------------------------------------------------------
// Image generation
// ---------------------------------------------------------------------------

export interface ImageOptions {
  model?: string;
  size?: "256x256" | "512x512" | "1024x1024" | "1792x1024" | "1024x1792";
  quality?: "standard" | "hd";
  n?: number;
  style?: "vivid" | "natural";
}

export interface ImageData {
  url?: string;
  b64_json?: string;
  revised_prompt?: string;
}

export interface ImageResponse {
  created: number;
  data: ImageData[];
}

// ---------------------------------------------------------------------------
// Vision / image analysis
// ---------------------------------------------------------------------------

export interface ImageAnalysisOptions {
  model?: string;
  maxTokens?: number;
}

export interface ImageAnalysisResponse {
  description: string;
  model: string;
  tokens: number;
}

// ---------------------------------------------------------------------------
// Code generation
// ---------------------------------------------------------------------------

export interface CodeOptions {
  model?: string;
  temperature?: number;
  maxTokens?: number;
}

export interface CodeResponse {
  code: string;
  language: string;
  explanation?: string;
  model: string;
}

// ---------------------------------------------------------------------------
// Embeddings
// ---------------------------------------------------------------------------

export interface EmbeddingsOptions {
  model?: string;
}

export interface EmbeddingData {
  object: "embedding";
  index: number;
  embedding: number[];
}

export interface EmbeddingsResponse {
  object: "list";
  data: EmbeddingData[];
  model: string;
  usage: { prompt_tokens: number; total_tokens: number };
}

// ---------------------------------------------------------------------------
// Translation
// ---------------------------------------------------------------------------

export interface TranslationOptions {
  model?: string;
  sourceLanguage?: string;
}

export interface TranslationResponse {
  translatedText: string;
  sourceLanguage: string;
  targetLanguage: string;
  model: string;
}

// ---------------------------------------------------------------------------
// Web research
// ---------------------------------------------------------------------------

export interface WebResearchOptions {
  model?: string;
  maxResults?: number;
  includeUrls?: boolean;
}

export interface WebResearchResult {
  title: string;
  url?: string;
  snippet: string;
  relevance?: number;
}

export interface WebResearchResponse {
  query: string;
  summary: string;
  results: WebResearchResult[];
  model: string;
}

// ---------------------------------------------------------------------------
// Client config
// ---------------------------------------------------------------------------

export interface RealAIClientConfig {
  apiKey?: string;
  baseUrl?: string;
  provider?: string;
  model?: string;
  timeout?: number;
  defaultHeaders?: Record<string, string>;
}

// ---------------------------------------------------------------------------
// Error
// ---------------------------------------------------------------------------

export interface RealAIErrorData {
  message: string;
  type?: string;
  code?: string;
  statusCode?: number;
}
