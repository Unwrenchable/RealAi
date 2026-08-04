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
export declare class RealAI {
    private apiKey?;
    private baseUrl;
    constructor(opts?: RealAIOptions);
    private request;
    chat(request: ChatCompletionRequest): Promise<any>;
    embeddings(request: EmbeddingsRequest): Promise<any>;
    models(): Promise<any>;
    providers(): Promise<any>;
    health(): Promise<any>;
    createTask(request: TaskRequest): Promise<any>;
    listTasks(): Promise<any>;
}
