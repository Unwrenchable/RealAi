export type ChatMessage = {
    role: "user" | "assistant" | "system";
    content: string;
};
export declare function realaiChat(opts: {
    baseUrl?: string;
    model?: string;
    messages: ChatMessage[];
}): Promise<string>;
