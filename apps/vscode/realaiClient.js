"use strict";
/// <reference lib="dom" />
Object.defineProperty(exports, "__esModule", { value: true });
exports.RealAIClient = void 0;
class RealAIClient {
    constructor(baseUrl) {
        // ... (rest of your code)
        this.baseUrl = 'http://127.0.0.1:8000';
        this.selectedModel = 'realai-2.0';
        if (baseUrl) {
            this.baseUrl = baseUrl;
        }
    }
    setModel(model) {
        this.selectedModel = model;
    }
    async _fetch(path, options) {
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
            let msg;
            try {
                const json = JSON.parse(body);
                msg = json.error || json.message || body;
            }
            catch {
                msg = body || `HTTP ${res.status}`;
            }
            throw new Error(`API ${res.status}: ${msg}`);
        }
        return res.json();
    }
    // ==================== HEALTH & STATUS ====================
    async getHealth() {
        const res = await fetch(`${this.baseUrl}/health`, { signal: AbortSignal.timeout(5000) });
        return res.json();
    }
    async getStatus() {
        return this._fetch('/v1/status');
    }
    async getCapabilities() {
        return this._fetch('/v1/capabilities');
    }
    // ==================== MODELS ====================
    async listModels() {
        return this._fetch('/v1/models');
    }
    async getModel(modelId) {
        return this._fetch(`/v1/models/${modelId}`);
    }
    // ==================== CHAT (non-streaming) ====================
    async chat(messages) {
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
    async chatPrompt(prompt) {
        return this.chat([{ role: 'user', content: prompt }]);
    }
    // ==================== CHAT (streaming) ====================
    async streamChat(messages, callbacks) {
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
                if (done)
                    break;
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
                        }
                        catch {
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
                        }
                        catch { /* skip */ }
                    }
                }
            }
            callbacks.onDone(fullContent);
        }
        catch (e) {
            callbacks.onError(e instanceof Error ? e.message : 'Stream error');
        }
    }
    // Convenience: single-turn streaming
    async streamChatPrompt(prompt, callbacks) {
        return this.streamChat([{ role: 'user', content: prompt }], callbacks);
    }
    // ==================== COMPLETIONS ====================
    async getCompletion(code, cursorPosition) {
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
    async getWorldState() {
        return this._fetch('/v1/world/state');
    }
    // ==================== MEMORY ====================
    async storeMemory(content, tags, namespace) {
        return this._fetch('/v1/memory/store', {
            method: 'POST',
            body: JSON.stringify({ content, tags, namespace }),
        });
    }
    // ==================== AGENTS ====================
    async orchestrateAgents(task, agentRoles) {
        return this._fetch('/v1/agents/orchestrate', {
            method: 'POST',
            body: JSON.stringify({ task, agent_roles: agentRoles }),
        });
    }
    // ==================== TOOLS ====================
    async listTools() {
        return this._fetch('/v1/tools');
    }
    // ==================== PLUGINS ====================
    async listPlugins() {
        return this._fetch('/v1/plugins');
    }
    // ==================== PERSONAS ====================
    async listPersonas() {
        return this._fetch('/v1/personas');
    }
}
exports.RealAIClient = RealAIClient;
