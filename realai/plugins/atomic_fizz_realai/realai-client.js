'use strict';
/**
 * RealAI hive HTTP client (CJS) — OpenAI-compatible chat against :8001.
 * Promoted from AFC scripts/realai/realai-client.js into plugin gold.
 */
const DEFAULT_BASE =
  process.env.REALAI_API_BASE ||
  process.env.REALAI_PROVIDER_URL ||
  String(process.env.AI_PROXY_URL || '').replace(/\/v1\/chat\/completions\/?$/, '') ||
  'http://127.0.0.1:8001';
const DEFAULT_KEY =
  process.env.REALAI_API_KEY ||
  process.env.OPENAI_API_KEY ||
  process.env.AI_API_KEY ||
  'realai';
const DEFAULT_MODEL =
  process.env.REALAI_MODEL ||
  process.env.OPENAI_MODEL ||
  process.env.AI_MODEL ||
  'realai';

const LEGACY_MODEL_ALIASES = new Set(['realai-1.0', 'realai-2.0', 'realai-overseer']);
const RETRYABLE_STATUS_CODES = new Set([408, 425, 429, 500, 502, 503, 504]);

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function extractMessageText(data) {
  const content =
    data && data.choices && data.choices[0] && data.choices[0].message
      ? data.choices[0].message.content
      : null;
  if (typeof content === 'string' && content.trim()) return content;
  if (Array.isArray(content)) {
    const joined = content
      .map((part) => (typeof part === 'string' ? part : (part && part.text) || ''))
      .join('')
      .trim();
    if (joined) return joined;
  }
  throw new Error('RealAI response did not include message content.');
}

async function realaiChat(messages, options) {
  options = options || {};
  const baseUrl = String(options.baseUrl || DEFAULT_BASE).replace(/\/$/, '');
  const apiKey = options.apiKey || DEFAULT_KEY;
  let model = options.model || DEFAULT_MODEL;
  if (LEGACY_MODEL_ALIASES.has(model)) model = DEFAULT_MODEL;
  const url = baseUrl + '/v1/chat/completions';
  const body = {
    model: model,
    messages: messages,
    temperature: options.temperature != null ? options.temperature : 0.7,
  };
  const maxAttempts = options.retries != null ? options.retries : 2;
  let lastErr;
  for (let attempt = 0; attempt <= maxAttempts; attempt++) {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer ' + apiKey,
          'User-Agent': 'RealAI-atomic_fizz_realai-client/1.0',
        },
        body: JSON.stringify(body),
      });
      const raw = await response.text();
      let data;
      try {
        data = raw ? JSON.parse(raw) : {};
      } catch (e) {
        data = { raw: raw };
      }
      if (!response.ok) {
        const detail =
          (data.error && data.error.message) || data.detail || raw || 'Unknown RealAI error.';
        const error = new Error('RealAI request failed (' + response.status + '): ' + detail);
        error.status = response.status;
        if (RETRYABLE_STATUS_CODES.has(response.status) && attempt < maxAttempts) {
          await sleep(250 * (attempt + 1));
          lastErr = error;
          continue;
        }
        throw error;
      }
      return data;
    } catch (err) {
      lastErr = err;
      if (attempt < maxAttempts) {
        await sleep(250 * (attempt + 1));
        continue;
      }
      throw err;
    }
  }
  throw lastErr || new Error('RealAI request exhausted retries.');
}

async function realai(prompt, model) {
  if (model == null) model = DEFAULT_MODEL;
  if (!prompt || !String(prompt).trim()) {
    throw new Error('RealAI requires a non-empty prompt.');
  }
  const data = await realaiChat([{ role: 'user', content: String(prompt) }], { model: model });
  return extractMessageText(data);
}

async function health(baseUrl) {
  if (baseUrl == null) baseUrl = DEFAULT_BASE;
  const root = String(baseUrl).replace(/\/$/, '');
  const response = await fetch(root + '/health', {
    headers: { 'User-Agent': 'RealAI-atomic_fizz_realai-client/1.0' },
  });
  const text = await response.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch (e) {
    body = { raw: text };
  }
  return { ok: response.ok, status: response.status, body: body, baseUrl: root };
}

module.exports = {
  realai: realai,
  realaiChat: realaiChat,
  health: health,
  DEFAULT_BASE: DEFAULT_BASE,
  DEFAULT_MODEL: DEFAULT_MODEL,
};
