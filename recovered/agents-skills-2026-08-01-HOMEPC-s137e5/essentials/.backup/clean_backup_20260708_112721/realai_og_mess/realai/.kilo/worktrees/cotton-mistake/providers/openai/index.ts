import OpenAI from "openai";
import type { Provider } from "../types";

const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export const openaiProvider: Provider = {
  id: "openai",
  name: "OpenAI",
  models: [
    { name: "gpt-4.1", context: 128000, type: "text" },
    { name: "gpt-4.1-mini", context: 64000, type: "text" },
  ],
  async call({ model, messages, temperature, maxTokens }) {
    const response = await client.chat.completions.create({
      model,
      messages,
      temperature,
      max_tokens: maxTokens,
    });

    return response.choices[0]?.message?.content ?? "";
  },
};