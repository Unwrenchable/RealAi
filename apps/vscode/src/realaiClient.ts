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

export interface ChatRequestOptions {
  temperature?: number;
  maxTokens?: number;
  agentId?: string;
  memory?: boolean;
  tools?: boolean;
  multiAgent?: boolean;
}

/** Console / extension chat abort (ms). Keep probes shorter separately. */
export const CHAT_TIMEOUT_MS = 180_000;
export const DEFAULT_FETCH_TIMEOUT_MS = 60_000;

export class RealAIClient {
  private baseUrl = 'http://127.0.0.1:8001';
  selectedModel = 'realai-hive';
  /** Empty by default — some hive agents inject a shell-executor persona. */
  defaultAgentId = '';
  memoryEnabled = true;
  /** Match browser console: tools on by default (X-RealAI-Tools: on). */
  toolsEnabled = true;
  /** Match browser console speak-aloud / orch TTS. */
  voiceEnabled = true;

  constructor(baseUrl?: string) {
    if (baseUrl) {
      this.baseUrl = baseUrl;
    }
  }

  setModel(model: string) {
    this.selectedModel = model;
  }

  getBaseUrl(): string {
    return this.baseUrl;
  }

  async probeUrl(url: string, timeoutMs = 2500): Promise<boolean> {
    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(timeoutMs) });
      return res.ok;
    } catch {
      return false;
    }
  }

  async getSelfHealStatus(): Promise<any> {
    return this._fetch('/v1/self-heal/status');
  }

  async getLora(): Promise<any> {
    return this._fetch('/v1/lora');
  }

  async getRecovery(): Promise<any> {
    return this._fetch('/v1/recovery');
  }

  async runAbility(ability: string, input?: unknown, context?: Record<string, unknown>): Promise<any> {
    return this._fetch('/v1/abilities/run', {
      method: 'POST',
      body: JSON.stringify({ ability, input, context }),
    });
  }

  private async _fetch(path: string, options?: RequestInit): Promise<any> {
    const url = `${this.baseUrl}${path}`;
    const isChat = path.includes('/chat/completions') || path.includes('/v1/completions');
    const timeoutMs = isChat ? CHAT_TIMEOUT_MS : DEFAULT_FETCH_TIMEOUT_MS;
    const signal = options?.signal ?? AbortSignal.timeout(timeoutMs);
    try {
    const res = await fetch(url, {
      ...options,
      signal,
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
    } catch (e: any) {
      const msg = String(e?.message || e || '');
      if (/timed out|TimeoutError|abort/i.test(msg) || e?.name === 'TimeoutError' || e?.name === 'AbortError') {
        throw new Error(`signal timed out (chat abort ${Math.round(timeoutMs/1000)}s)`);
      }
      throw e;
    }
  }

  private buildBody(messages: ChatMessage[], opts: ChatRequestOptions = {}, stream = false) {
    const agentId = (opts.agentId ?? this.defaultAgentId ?? '').trim();
    const memory = opts.memory ?? this.memoryEnabled;
    const tools = opts.tools ?? this.toolsEnabled;
    const multiAgent = opts.multiAgent ?? false;

    // Important: never send tools:false — Vulkan rejects non-array tools.
    // Only send tools:true so the orchestrator rewrites it to a catalog array.
    const body: Record<string, unknown> = {
      model: this.selectedModel,
      messages,
      temperature: opts.temperature ?? 0.3,
      max_tokens: opts.maxTokens ?? 2048,
      stream,
      memory: !!memory,
    };
    if (agentId) body.agent_id = agentId;
    if (tools) body.tools = true;
    if (multiAgent) body.multi_agent = true;
    return body;
  }

  private buildHeaders(opts: ChatRequestOptions = {}): Record<string, string> {
    const agentId = (opts.agentId ?? this.defaultAgentId ?? '').trim();
    const memory = opts.memory ?? this.memoryEnabled;
    const tools = opts.tools ?? this.toolsEnabled;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (agentId) headers['X-RealAI-Agent-Id'] = agentId;
    headers['X-RealAI-Memory'] = memory ? 'on' : 'off';
    // Match browser console (/console): tools + voice headers.
    headers['X-RealAI-Tools'] = tools ? 'on' : 'off';
    headers['X-RealAI-Voice'] = this.voiceEnabled ? 'on' : 'off';
    if (opts.multiAgent) headers['X-RealAI-Multi-Agent'] = 'true';
    return headers;
  }

  async getHealth(): Promise<{ status: string; model?: string; service?: string }> {
    const res = await fetch(`${this.baseUrl}/health`, { signal: AbortSignal.timeout(5000) });
    return res.json();
  }

  async getHive(): Promise<any> {
    return this._fetch('/v1/hive');
  }

  async getCapabilities(): Promise<any> {
    return this._fetch('/v1/capabilities');
  }

  /**
   * Live Hive ability catalog. Tries GET /v1/abilities then /v1/abilities/list.
   * Never returns a baked-in static list — empty on failure with source explaining why.
   */
  async listAbilities(): Promise<{
    abilities: Array<{ id: string; name?: string; status?: string; [key: string]: unknown }>;
    source: string;
    raw: unknown;
  }> {
    const endpoints = ['/v1/abilities', '/v1/abilities/list'];
    let lastErr: unknown;
    for (const ep of endpoints) {
      try {
        const raw = await this._fetch(ep);
        const abilities = RealAIClient.normalizeAbilityRows(raw);
        return { abilities, source: `hive:${ep}`, raw };
      } catch (e) {
        lastErr = e;
      }
    }
    const msg = String((lastErr as any)?.message || lastErr || 'unreachable');
    return { abilities: [], source: `error:${msg}`, raw: null };
  }

  /** Normalize assorted Hive payloads into {id,name,status,...} rows. No static catalog. */
  private static normalizeAbilityRows(
    raw: unknown
  ): Array<{ id: string; name?: string; status?: string; [key: string]: unknown }> {
    const out: Array<{ id: string; name?: string; status?: string; [key: string]: unknown }> = [];
    const seen = new Set<string>();
    const push = (row: any) => {
      if (row == null) return;
      if (typeof row === 'string') {
        const id = row.trim();
        if (!id || seen.has(id)) return;
        seen.add(id);
        out.push({ id, name: id, status: 'LIVE' });
        return;
      }
      if (typeof row !== 'object') return;
      const id = String(
        row.id || row.ability || row.name || row.key || row.slug || ''
      ).trim();
      if (!id || seen.has(id)) return;
      seen.add(id);
      const name = String(row.name || row.title || row.label || id);
      const status = String(row.status || row.state || 'LIVE').toUpperCase();
      out.push({ ...row, id, name, status });
    };

    if (Array.isArray(raw)) {
      for (const row of raw) push(row);
      return out;
    }
    if (raw && typeof raw === 'object') {
      const obj = raw as Record<string, unknown>;
      const candidates = [obj.abilities, obj.data, obj.items, obj.results, obj.catalog];
      for (const c of candidates) {
        if (Array.isArray(c)) {
          for (const row of c) push(row);
          if (out.length) return out;
        }
      }
      for (const [k, v] of Object.entries(obj)) {
        if (['abilities', 'data', 'items', 'results', 'catalog', 'error', 'ok', 'source'].includes(k)) {
          continue;
        }
        if (v && typeof v === 'object' && !Array.isArray(v)) {
          push({ id: k, ...(v as object) });
        } else if (typeof v === 'string') {
          push({ id: k, status: v });
        }
      }
    }
    return out;
  }
  async listModels(): Promise<{ data: Array<{ id: string; object: string }> }> {
    return this._fetch('/v1/models');
  }

  async getModel(modelId: string): Promise<any> {
    return this._fetch(`/v1/models/${modelId}`);
  }

  async chat(messages: ChatMessage[], opts: ChatRequestOptions = {}): Promise<string> {
    const full = await this.chatFull(messages, opts);
    return full.content;
  }

  /** Full chat response (content + realai_meta.voice) — same shape browser console uses. */
  async chatFull(
    messages: ChatMessage[],
    opts: ChatRequestOptions = {}
  ): Promise<{ content: string; voice?: any; raw?: any }> {
    const json = await this._fetch('/v1/chat/completions', {
      method: 'POST',
      headers: this.buildHeaders(opts),
      body: JSON.stringify(this.buildBody(messages, opts, false)),
    });
    return {
      content: json.choices?.[0]?.message?.content || '',
      voice: json.realai_meta?.voice || null,
      raw: json,
    };
  }

  async chatPrompt(prompt: string, opts: ChatRequestOptions = {}): Promise<string> {
    return this.chat([{ role: 'user', content: prompt }], opts);
  }

  async streamChat(
    messages: ChatMessage[],
    callbacks: StreamCallbacks,
    opts: ChatRequestOptions = {}
  ): Promise<void> {
    try {
      const res = await fetch(`${this.baseUrl}/v1/chat/completions`, {
        method: 'POST',
        headers: this.buildHeaders(opts),
        body: JSON.stringify(this.buildBody(messages, opts, true)),
        signal: AbortSignal.timeout(CHAT_TIMEOUT_MS),
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
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data: ')) continue;
          const dataStr = trimmed.slice(6).trim();
          if (dataStr === '[DONE]') {
            callbacks.onDone(fullContent);
            return;
          }
          try {
            const data = JSON.parse(dataStr);
            const content = data.choices?.[0]?.delta?.content;
            if (typeof content === 'string' && content.length) {
              fullContent += content;
              callbacks.onToken(content);
            }
            if (data.choices?.[0]?.finish_reason === 'stop') {
              callbacks.onDone(fullContent);
              return;
            }
          } catch {
            // skip malformed SSE chunks
          }
        }
      }

      if (buffer.trim().startsWith('data: ')) {
        const dataStr = buffer.trim().slice(6).trim();
        if (dataStr !== '[DONE]') {
          try {
            const data = JSON.parse(dataStr);
            const content = data.choices?.[0]?.delta?.content;
            if (typeof content === 'string' && content.length) {
              fullContent += content;
              callbacks.onToken(content);
            }
          } catch {
            /* skip */
          }
        }
      }
      callbacks.onDone(fullContent);
    } catch (e) {
      callbacks.onError(e instanceof Error ? e.message : 'Stream error');
    }
  }

  async streamChatPrompt(
    prompt: string,
    callbacks: StreamCallbacks,
    opts: ChatRequestOptions = {}
  ): Promise<void> {
    return this.streamChat([{ role: 'user', content: prompt }], callbacks, opts);
  }

  async executeTool(name: string, args: Record<string, unknown> = {}): Promise<any> {
    return this._fetch('/v1/tools/execute', {
      method: 'POST',
      body: JSON.stringify({ name, arguments: args }),
    });
  }

  async listTools(): Promise<{ tools: Array<any> }> {
    return this._fetch('/v1/tools');
  }

  async listAgents(): Promise<any> {
    return this._fetch('/v1/agents');
  }

  async multiAgentRun(task: string, mode: string = 'pipeline'): Promise<any> {
    return this._fetch('/v1/multi-agent/run', {
      method: 'POST',
      body: JSON.stringify({ task, mode }),
    });
  }

  async runAgent(agentId: string, task: string, opts?: { multi?: boolean }): Promise<any> {
    return this._fetch('/v1/agents/run', {
      method: 'POST',
      body: JSON.stringify({
        agent_id: agentId || 'coder',
        task,
        multi: !!opts?.multi,
        use_multi: !!opts?.multi,
      }),
    });
  }

  async getCompletion(code: string, _cursorPosition: number): Promise<string> {
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
    return json.choices?.[0]?.text || '';
  }
}
