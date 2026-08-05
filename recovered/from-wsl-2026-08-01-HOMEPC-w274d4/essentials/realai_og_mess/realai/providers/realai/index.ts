import type { Provider } from "../types";

function getRealAIBaseUrl(): string {
  const url = process.env.REALAI_API_URL;
  if (!url) {
    throw new Error("REALAI_API_URL is required for the RealAI provider.");
  }
  return url.replace(/\/+$/, "");
}

export const realaiProvider: Provider = {
  id: "realai",
  name: "RealAI",
  models: [
    { name: "realai-1.0", context: 128000, type: "text" },
    { name: "realai-overseer", context: 256000, type: "text" },
  ],
  async call({ model, messages, temperature, maxTokens }) {
    const response = await fetch(`${getRealAIBaseUrl()}/v1/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        messages,
        temperature,
        max_tokens: maxTokens,
      }),
    });

    const data = await response.json();
    return data?.choices?.[0]?.message?.content ?? data?.output ?? "";
  },
};