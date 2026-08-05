/// <reference lib="dom" />

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onDone: (fullContent: string) => void;
  onError: (error: string) => void;
}

export class RealAIClient {
  // ... (rest of your code)
  private baseUrl = 'http://127.0.0.1:8000';
  selectedModel = 'realai-2.0';

  constructor(baseUrl?: string) {
    if (baseUrl) {
      this.baseUrl = baseUrl;
    }
  }

  setModel(model: string) {
    this.selectedModel = model;
  }

  private async _fetch(path: string, options?: RequestInit): Promise<any> {
    const url = `${this.baseUrl}${path}`;
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers || {}),
      },
    });
    if (!res.ok) {
      const body = await res.text();
      let msg: string;
      try {
        const json = JSON.parse(body);
        msg = json.error || json.message || body;
      } catch {
        msg = body || `HTTP ${res.status}`;
      }
      throw new Error(`API ${res.status}: ${msg}`);
    }
    return res.json();
  }

  // ==================== HEALTH & STATUS ====================

  async getHealth(): Promise<{ status: string; model?: string }> {
    const res = await fetch(`${this.baseUrl}/health`, { signal: AbortSignal.timeout(5000) });
    return res.json();
  }

  async getStatus(): Promise<{ status: string; service?: string; model?: string; port?: string }> {
    return this._fetch('/v1/status');
  }

  async getCapabilities(): Promise<any> {
    return this._fetch('/v1/capabilities');
  }

  // ==================== MODELS ====================

  async listModels(): Promise<{ data: Array<{ id: string; object: string }> }> {
    return this._fetch('/v1/models');
  }

  async getModel(modelId: string): Promise<any> {
    return this._fetch(`/v1/models/${modelId}`);
  }

  // ==================== CHAT (non-streaming) ====================

  async chat(messages: ChatMessage[]): Promise<string> {
    const body = {
      model: this.selectedModel,
      messages,
      temperature: 0.7,
    };
    const json = await this._fetch('/v1/chat/completions', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    return json.choices?.[0]?.message?.content || '';
  }

  // Convenience: single-turn chat
  async chatPrompt(prompt: string): Promise<string> {
    return this.chat([{ role: 'user', content: prompt }]);
  }

  // ==================== CHAT (streaming) ====================

  async streamChat(messages: ChatMessage[], callbacks: StreamCallbacks): Promise<void> {
    const body = {
      model: this.selectedModel,
      messages,
      temperature: 0.7,
      stream: true,
    };

    try {
      const res = await fetch(`${this.baseUrl}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const errorText = await res.text();
        callbacks.onError(`HTTP ${res.status}: ${errorText}`);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        callbacks.onError('No response body');
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';
      let fullContent = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');

        // Keep the last partial line in the buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();

          // OpenAI SSE format: data: {...}
          if (trimmed.startsWith('data: ')) {
            const dataStr = trimmed.slice(6).trim();
            if (dataStr === '[DONE]') {
              callbacks.onDone(fullContent);
              return;
            }
            try {
              const data = JSON.parse(dataStr);
              const content = data.choices?.[0]?.delta?.content || '';
              if (content) {
                fullContent += content;
                callbacks.onToken(content);
              }
              // Check for finish_reason
              if (data.choices?.[0]?.finish_reason === 'stop') {
                callbacks.onDone(fullContent);
                return;
              }
            } catch {
              // Skip malformed JSON lines
            }
          }
        }
      }

      // If we got here without a [DONE] or finish_reason, complete anyway
      if (buffer.trim()) {
        // Try to parse any remaining data
        const trimmed = buffer.trim();
        if (trimmed.startsWith('data: ')) {
          const dataStr = trimmed.slice(6).trim();
          if (dataStr !== '[DONE]') {
            try {
              const data = JSON.parse(dataStr);
              const content = data.choices?.[0]?.delta?.content || '';
              if (content) {
                fullContent += content;
                callbacks.onToken(content);
              }
            } catch { /* skip */ }
          }
        }
      }
      callbacks.onDone(fullContent);
    } catch (e) {
      callbacks.onError(e instanceof Error ? e.message : 'Stream error');
    }
  }

  // Convenience: single-turn streaming
  async streamChatPrompt(prompt: string, callbacks: StreamCallbacks): Promise<void> {
    return this.streamChat([{ role: 'user', content: prompt }], callbacks);
  }

  // ==================== COMPLETIONS ====================

  async getCompletion(code: string, cursorPosition: number): Promise<string> {
    const body = {
      model: this.selectedModel,
      prompt: code,
      max_tokens: 100,
      temperature: 0.3,
    };
    const json = await this._fetch('/v1/completions', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    // OpenAI-style: choices[0].text
    return json.choices?.[0]?.text || '';
  }

  // ==================== WORLD STATE ====================

  async getWorldState(): Promise<{ facts?: Array<any> }> {
    return this._fetch('/v1/world/state');
  }

  // ==================== MEMORY ====================

  async storeMemory(content: string, tags?: string[], namespace?: string): Promise<{ item_id?: string; status?: string }> {
    return this._fetch('/v1/memory/store', {
      method: 'POST',
      body: JSON.stringify({ content, tags, namespace }),
    });
  }

  // ==================== AGENTS ====================

  async orchestrateAgents(task: string, agentRoles?: string[]): Promise<any> {
    return this._fetch('/v1/agents/orchestrate', {
      method: 'POST',
      body: JSON.stringify({ task, agent_roles: agentRoles }),
    });
  }

  // ==================== TOOLS ====================

  async listTools(): Promise<{ tools: Array<any> }> {
    return this._fetch('/v1/tools');
  }

  // ==================== PLUGINS ====================

  async listPlugins(): Promise<{ plugins: Array<any> }> {
    return this._fetch('/v1/plugins');
  }

  // ==================== PERSONAS ====================

  async listPersonas(): Promise<{ personas: Array<any> }> {
    return this._fetch('/v1/personas');
  }
}
