/**
 * RealAI TypeScript SDK
 * Structured client for the RealAI platform surface.
 */
export class RealAI {
    constructor(opts = {}) {
        this.apiKey = opts.apiKey;
        this.baseUrl = (opts.baseUrl || process.env.REALAI_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
    }
    async request(path, init) {
        const headers = new Headers(init?.headers || {});
        if (!headers.has("Content-Type") && init?.body) {
            headers.set("Content-Type", "application/json");
        }
        if (this.apiKey) {
            headers.set("Authorization", `Bearer ${this.apiKey}`);
        }
        const response = await fetch(`${this.baseUrl}${path}`, {
            ...init,
            headers,
        });
        if (!response.ok) {
            throw new Error(`RealAI API error: ${response.status} ${response.statusText}`);
        }
        return response.json();
    }
    chat(request) {
        return this.request("/v1/chat/completions", {
            method: "POST",
            body: JSON.stringify(request),
        });
    }
    embeddings(request) {
        return this.request("/v1/embeddings", {
            method: "POST",
            body: JSON.stringify(request),
        });
    }
    models() {
        return this.request("/v1/models");
    }
    providers() {
        return this.request("/v1/providers");
    }
    health() {
        return this.request("/health");
    }
    createTask(request) {
        return this.request("/v1/tasks", {
            method: "POST",
            body: JSON.stringify(request),
        });
    }
    listTasks() {
        return this.request("/v1/tasks");
    }
}
