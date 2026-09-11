import { openaiProvider } from "./openai";
import { realaiProvider } from "./realai";
import type { Provider } from "./types";

const providers: Record<string, Provider> = {
  openai: openaiProvider,
  realai: realaiProvider,
};

export function getProvider(id: string): Provider {
  const provider = providers[id];
  if (!provider) {
    throw new Error(`Unknown provider: ${id}`);
  }
  return provider;
}

export function listProviders(): Provider[] {
  return Object.values(providers);
}