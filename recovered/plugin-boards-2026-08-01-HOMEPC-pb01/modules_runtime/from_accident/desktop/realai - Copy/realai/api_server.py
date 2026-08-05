"""
RealAI API Server

A simple HTTP server that provides an OpenAI-compatible REST API.
This allows you to use RealAI with any OpenAI-compatible client libraries.

Run with: python -m realai.api_server

API Key handling
----------------
Pass your provider API key in the standard ``Authorization: Bearer <key>``
header.  RealAI auto-detects the provider from the key prefix and forwards
requests to the real AI service.  You can also supply ``X-Provider`` to pick
the provider explicitly, and ``X-Base-URL`` to override the endpoint.
"""

import hashlib
import json
import os
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from . import RealAI, PROVIDER_CONFIGS, PROVIDER_ENV_VARS, _KEY_PREFIX_TO_PROVIDER

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

#: Path to the SQLite database file.  Override via ``REALAI_DB_PATH``.
_DEFAULT_DB_PATH = os.path.join(
    os.environ.get("REALAI_DATA_DIR", os.path.expanduser("~/.realai")),
    "conversations.db",
)


def init_db(db_path: str = _DEFAULT_DB_PATH) -> str:
    """Initialise the SQLite database, creating tables if they don't exist.

    Safe to call multiple times; uses ``CREATE TABLE IF NOT EXISTS`` so it is
    idempotent.  Returns the resolved *db_path* for convenience.

    Schema
    ------
    users
        Keyed by ``external_id`` — an opaque string identifying a caller.
        Values are either a short hash of the bearer token
        (``key:<sha256_prefix>``) or an anonymous tag (``anon:<client_ip>``).

    chat_messages
        One row per message exchanged, linked to a user by ``user_external_id``
        so that the full history for any identity can be fetched without a JOIN.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT    NOT NULL UNIQUE,
                created_at  INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_external_id TEXT    NOT NULL,
                role             TEXT    NOT NULL,
                content          TEXT    NOT NULL,
                created_at       INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
            );

            CREATE INDEX IF NOT EXISTS idx_messages_user
                ON chat_messages(user_external_id);
            """
        )
        con.commit()
    finally:
        con.close()
    return db_path

# ---------------------------------------------------------------------------
# Provider metadata for the web UI
# ---------------------------------------------------------------------------

_PROVIDER_META = {
    "openai":     {"label": "OpenAI",        "placeholder": "sk-..."},
    "anthropic":  {"label": "Anthropic",     "placeholder": "sk-ant-..."},
    "grok":       {"label": "xAI / Grok",    "placeholder": "xai-..."},
    "gemini":     {"label": "Google Gemini", "placeholder": "AIza..."},
    "openrouter": {"label": "OpenRouter",    "placeholder": "sk-or-v1-..."},
    "mistral":    {"label": "Mistral AI",    "placeholder": "..."},
    "together":   {"label": "Together AI",   "placeholder": "..."},
    "deepseek":   {"label": "DeepSeek",      "placeholder": "..."},
    "perplexity": {"label": "Perplexity AI", "placeholder": "pplx-..."},
}

# ---------------------------------------------------------------------------
# Web UI – single-page chat application served at GET / and GET /ui
# ---------------------------------------------------------------------------

_WEB_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RealAI Chat</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #0d0d1a; --bg2: #13132a; --bg3: #1a1a3e;
  --border: #2a2a5a; --text: #e0e0ff; --text2: #9090cc;
  --accent: #7c5cfc; --user-bg: #1a1a5a; --ai-bg: #13132a;
  --error: #c62828; --input-bg: #1a1a3e;
}
body {
  font-family: 'Segoe UI', system-ui, sans-serif;
  background: var(--bg); color: var(--text);
  height: 100vh; display: flex; flex-direction: column; overflow: hidden;
}
header {
  background: var(--bg2); border-bottom: 1px solid var(--border);
  padding: 12px 20px; display: flex; align-items: center;
  justify-content: space-between; flex-shrink: 0;
}
.logo { font-size: 1.4rem; font-weight: 700; }
.logo .accent { color: var(--accent); }
.header-right { display: flex; align-items: center; gap: 10px; }
#key-status {
  font-size: 0.78rem; padding: 3px 10px; border-radius: 12px; white-space: nowrap;
}
.status-ok  { background: #1a4a30; color: #4caf50; }
.status-none { background: #3a1a1a; color: #ef9a9a; }
.settings-bar {
  background: var(--bg2); border-bottom: 1px solid var(--border);
  padding: 10px 20px; display: flex; align-items: center;
  gap: 10px; flex-wrap: wrap; flex-shrink: 0;
}
.settings-bar label { font-size: 0.8rem; color: var(--text2); white-space: nowrap; }
.settings-bar select, .settings-bar input[type=password],
.settings-bar input[type=text] {
  background: var(--input-bg); border: 1px solid var(--border);
  color: var(--text); padding: 6px 10px; border-radius: 6px; font-size: 0.85rem;
}
.settings-bar select:focus, .settings-bar input:focus {
  outline: none; border-color: var(--accent);
}
#api-key-input { width: 260px; font-family: monospace; }
.btn {
  padding: 7px 14px; border: none; border-radius: 6px; cursor: pointer;
  font-size: 0.83rem; font-weight: 600; transition: opacity 0.15s;
}
.btn:hover { opacity: 0.85; }
.btn:active { opacity: 0.7; }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-primary  { background: var(--accent); color: #fff; }
.btn-secondary { background: var(--bg3); color: var(--text); border: 1px solid var(--border); }
.btn-danger   { background: var(--error); color: #fff; }
.btn-sm { padding: 5px 10px; font-size: 0.78rem; }
#chat-messages {
  flex: 1; overflow-y: auto; padding: 20px;
  display: flex; flex-direction: column; gap: 16px;
}
#chat-messages::-webkit-scrollbar { width: 6px; }
#chat-messages::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
.message { display: flex; flex-direction: column; max-width: 80%; }
.message.user { align-self: flex-end; }
.message.assistant, .message.error { align-self: flex-start; }
.message-meta {
  font-size: 0.72rem; color: var(--text2); margin-bottom: 4px; padding: 0 4px;
}
.message.user .message-meta { text-align: right; }
.message-bubble {
  padding: 12px 16px; border-radius: 14px; line-height: 1.6;
  font-size: 0.92rem; word-break: break-word; white-space: pre-wrap;
}
.message.user      .message-bubble { background: var(--user-bg); border: 1px solid #2a2a7a; border-bottom-right-radius: 4px; }
.message.assistant .message-bubble { background: var(--ai-bg);   border: 1px solid var(--border); border-bottom-left-radius: 4px; }
.message.error     .message-bubble { background: #2a1010; border: 1px solid var(--error); color: #ef9a9a; }
.typing-dots { display: inline-flex; gap: 4px; align-items: center; padding: 4px 0; }
.typing-dots span {
  width: 8px; height: 8px; background: var(--text2); border-radius: 50%;
  animation: blink 1.2s infinite;
}
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0%,80%,100% { opacity: 0.2; } 40% { opacity: 1; } }
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
.message { animation: fadeIn 0.2s ease; }
#welcome {
  text-align: center; margin: auto; padding: 40px;
}
#welcome .big-icon { font-size: 3.5rem; margin-bottom: 14px; }
#welcome h2 { font-size: 1.5rem; margin-bottom: 8px; }
#welcome p  { color: var(--text2); margin-bottom: 18px; }
.cap-grid { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; max-width: 540px; }
.cap-pill {
  background: var(--bg3); border: 1px solid var(--border);
  padding: 5px 12px; border-radius: 20px; font-size: 0.8rem; color: var(--text2);
}
.input-area {
  background: var(--bg2); border-top: 1px solid var(--border);
  padding: 12px 20px; flex-shrink: 0;
}
.input-row { display: flex; gap: 10px; align-items: flex-end; }
#message-input {
  flex: 1; background: var(--input-bg); border: 1px solid var(--border);
  color: var(--text); padding: 10px 14px; border-radius: 10px;
  font-size: 0.92rem; resize: none; min-height: 44px; max-height: 160px;
  font-family: inherit; line-height: 1.5;
}
#message-input:focus { outline: none; border-color: var(--accent); }
#send-btn {
  width: 44px; height: 44px; border-radius: 10px; padding: 0;
  display: flex; align-items: center; justify-content: center; font-size: 1.2rem; flex-shrink: 0;
}
.input-hint { font-size: 0.74rem; color: var(--text2); margin-top: 6px; }
#toast {
  position: fixed; bottom: 76px; left: 50%; transform: translateX(-50%);
  background: var(--bg3); border: 1px solid var(--border); color: var(--text);
  padding: 9px 18px; border-radius: 8px; font-size: 0.84rem;
  opacity: 0; transition: opacity 0.3s; pointer-events: none; z-index: 100;
}
#toast.show { opacity: 1; }
@media (max-width: 600px) {
  #api-key-input { width: 140px; }
  .message { max-width: 95%; }
  .settings-bar { gap: 7px; }
}
</style>
</head>
<body>

<header>
  <div class="logo">&#x1F916; Real<span class="accent">AI</span>
    <span style="font-size:0.68rem;color:var(--text2);font-weight:400"> v2.0</span>
  </div>
  <div class="header-right">
    <span id="key-status" class="status-none">No API key</span>
    <button class="btn btn-secondary btn-sm" onclick="clearChat()">Clear chat</button>
  </div>
</header>

<div class="settings-bar">
  <label for="provider-select">Provider</label>
  <select id="provider-select" onchange="onSettingChange()">
    <option value="auto">Auto-detect from key</option>
    <option value="openai">OpenAI</option>
    <option value="anthropic">Anthropic (Claude)</option>
    <option value="grok">xAI / Grok</option>
    <option value="gemini">Google Gemini</option>
    <option value="openrouter">OpenRouter</option>
    <option value="mistral">Mistral AI</option>
    <option value="together">Together AI</option>
    <option value="deepseek">DeepSeek</option>
    <option value="perplexity">Perplexity AI</option>
  </select>

  <label for="model-select">Model</label>
  <select id="model-select" onchange="onSettingChange()">
    <option value="realai-2.0">realai-2.0</option>
  </select>

  <label for="api-key-input">API Key</label>
  <input type="password" id="api-key-input"
         placeholder="Paste your provider API key&#x2026;"
         oninput="onKeyInput()"
         onkeydown="if(event.key==='Enter')saveKey()">
  <button class="btn btn-sm btn-secondary" onclick="toggleKeyVis()" title="Show / hide key">&#x1F441;</button>
  <button class="btn btn-sm btn-primary" onclick="saveKey()">Save key</button>
  <button class="btn btn-sm btn-secondary" onclick="clearKey()">Clear</button>
</div>
<div id="provider-hint" style="display:none;background:#3a1a1a;color:#ef9a9a;font-size:0.8rem;padding:6px 20px;border-bottom:1px solid var(--border)"></div>

<div id="chat-messages">
  <div id="welcome">
    <div class="big-icon">&#x1F916;</div>
    <h2>Welcome to RealAI</h2>
    <p>Paste your API key above, pick a provider &amp; model, then start chatting.</p>
    <div class="cap-grid">
      <span class="cap-pill">&#x1F4AC; Chat</span>
      <span class="cap-pill">&#x1F517; Chain-of-thought</span>
      <span class="cap-pill">&#x1F52C; Knowledge synthesis</span>
      <span class="cap-pill">&#x1F916; Multi-agent</span>
      <span class="cap-pill">&#x1F310; Web research</span>
      <span class="cap-pill">&#x1F4BB; Code generation</span>
      <span class="cap-pill">&#x1F3E2; Business planning</span>
      <span class="cap-pill">&#x26D3; Web3</span>
    </div>
  </div>
</div>

<div class="input-area">
  <div class="input-row">
    <textarea id="message-input" rows="1"
              placeholder="Type your message&#x2026; (Enter to send, Shift+Enter for new line)"
              onkeydown="handleKey(event)"
              oninput="autoResize(this)"></textarea>
    <button class="btn btn-primary" id="send-btn" onclick="sendMessage()" title="Send (Enter)">&#x2191;</button>
  </div>
  <div class="input-hint">Enter&#xA0;to&#xA0;send &nbsp;&#xB7;&nbsp; Shift+Enter&#xA0;for&#xA0;new&#xA0;line &nbsp;&#xB7;&nbsp; Your key is stored only in your browser</div>
</div>

<div id="toast"></div>

<script>
// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
var KEY_STORE      = 'realai_api_key';
var PROVIDER_STORE = 'realai_provider';
var MODEL_STORE    = 'realai_model';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
var messages  = [];
var isLoading = false;

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
window.addEventListener('DOMContentLoaded', function() {
  loadSettings();
  loadModels();
});

function loadSettings() {
  var key      = sessionStorage.getItem(KEY_STORE)     || '';
  var provider = localStorage.getItem(PROVIDER_STORE) || 'auto';
  document.getElementById('api-key-input').value = key;
  var ps = document.getElementById('provider-select');
  if ([].slice.call(ps.options).some(function(o){ return o.value === provider; })) {
    ps.value = provider;
  }
  updateKeyStatus(key);
}

function loadModels() {
  fetch('/v1/models').then(function(r){ return r.json(); }).then(function(data) {
    var select = document.getElementById('model-select');
    select.innerHTML = '';
    (data.data || []).forEach(function(m) {
      var opt = document.createElement('option');
      opt.value = m.id; opt.textContent = m.id;
      select.appendChild(opt);
    });
    var saved = localStorage.getItem(MODEL_STORE) || 'realai-2.0';
    if ([].slice.call(select.options).some(function(o){ return o.value === saved; })) {
      select.value = saved;
    }
  }).catch(function(){});
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------
function onSettingChange() {
  localStorage.setItem(PROVIDER_STORE, document.getElementById('provider-select').value);
  localStorage.setItem(MODEL_STORE,    document.getElementById('model-select').value);
}

// Mirrors the server-side _KEY_PREFIX_TO_PROVIDER map.
function detectProvider(key) {
  if (!key) return null;
  if (key.startsWith('sk-ant-'))   return 'anthropic';
  if (key.startsWith('sk-or-v1-')) return 'openrouter';
  if (key.startsWith('sk-proj-'))  return 'openai';
  if (key.startsWith('sk-'))       return 'openai';
  if (key.startsWith('xai-'))      return 'grok';
  if (key.startsWith('AIza'))      return 'gemini';
  if (key.startsWith('pplx-'))     return 'perplexity';
  return null;
}

function onKeyInput() {
  var key = document.getElementById('api-key-input').value;
  updateKeyStatus(key);
  // Auto-select provider when the key prefix is recognizable.
  var detected = detectProvider(key);
  var select = document.getElementById('provider-select');
  if (detected) {
    select.value = detected;
    localStorage.setItem(PROVIDER_STORE, detected);
    showProviderHint('');
  } else if (key && key.trim()) {
    // Key is present but prefix is not recognized — prompt the user.
    showProviderHint('\\u26A0\\uFE0F Key not recognized — please select your provider from the dropdown above.');
  } else {
    showProviderHint('');
  }
}

function showProviderHint(msg) {
  var el = document.getElementById('provider-hint');
  if (!el) return;
  el.textContent = msg;
  el.style.display = msg ? 'block' : 'none';
}

function saveKey() {
  var key      = document.getElementById('api-key-input').value.trim();
  var provider = document.getElementById('provider-select').value;
  var model    = document.getElementById('model-select').value;
  if (key) {
    sessionStorage.setItem(KEY_STORE, key);
    localStorage.removeItem(KEY_STORE);
  } else {
    sessionStorage.removeItem(KEY_STORE);
    localStorage.removeItem(KEY_STORE);
  }
  localStorage.setItem(PROVIDER_STORE, provider);
  localStorage.setItem(MODEL_STORE, model);
  updateKeyStatus(key);
  toast(key ? '\\u2713 API key saved for this session only' : 'API key cleared');
}

function clearKey() {
  sessionStorage.removeItem(KEY_STORE);
  localStorage.removeItem(KEY_STORE);
  document.getElementById('api-key-input').value = '';
  updateKeyStatus('');
  showProviderHint('');
  toast('API key cleared');
}

function toggleKeyVis() {
  var inp = document.getElementById('api-key-input');
  inp.type = (inp.type === 'password') ? 'text' : 'password';
}

function updateKeyStatus(key) {
  var el = document.getElementById('key-status');
  if (key && key.trim()) {
    el.textContent = '\\uD83D\\uDD11 Key set';
    el.className = 'status-ok';
  } else {
    el.textContent = 'No API key';
    el.className = 'status-none';
  }
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------
function clearChat() {
  messages = [];
  var c = document.getElementById('chat-messages');
  c.innerHTML = '<div id="welcome"><div class="big-icon">&#x1F916;</div>'
    + '<h2>Welcome to RealAI</h2>'
    + '<p>Paste your API key above, pick a provider &amp; model, then start chatting.</p>'
    + '<div class="cap-grid">'
    + '<span class="cap-pill">&#x1F4AC; Chat</span>'
    + '<span class="cap-pill">&#x1F517; Chain-of-thought</span>'
    + '<span class="cap-pill">&#x1F52C; Knowledge synthesis</span>'
    + '<span class="cap-pill">&#x1F916; Multi-agent</span>'
    + '<span class="cap-pill">&#x1F310; Web research</span>'
    + '<span class="cap-pill">&#x1F4BB; Code generation</span>'
    + '<span class="cap-pill">&#x1F3E2; Business planning</span>'
    + '<span class="cap-pill">&#x26D3;&#xFE0F; Web3</span>'
    + '</div></div>';
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

function sendMessage() {
  if (isLoading) return;
  var input = document.getElementById('message-input');
  var text  = input.value.trim();
  if (!text) return;

  var welcome = document.getElementById('welcome');
  if (welcome) welcome.remove();

  messages.push({ role: 'user', content: text });
  appendMessage('user', text);

  input.value = '';
  input.style.height = 'auto';

  var loadingId = 'loading-' + Date.now();
  appendLoading(loadingId);
  isLoading = true;
  document.getElementById('send-btn').disabled = true;

  var apiKey   = sessionStorage.getItem(KEY_STORE)    || localStorage.getItem(KEY_STORE) || '';
  var provider = localStorage.getItem(PROVIDER_STORE) || 'auto';
  var model    = document.getElementById('model-select').value || 'realai-2.0';

  var headers = { 'Content-Type': 'application/json' };
  if (apiKey)                    headers['Authorization'] = 'Bearer ' + apiKey;
  if (provider && provider !== 'auto') headers['X-Provider'] = provider;

  fetch('/v1/chat/completions', {
    method: 'POST',
    headers: headers,
    body: JSON.stringify({ model: model, messages: messages.slice(-20), temperature: 0.7 })
  })
  .then(function(r) { return r.json().then(function(d){ return { ok: r.ok, data: d }; }); })
  .then(function(res) {
    removeLoading(loadingId);
    if (!res.ok) {
      appendMessage('error', '\\u26A0 ' + (res.data.error || 'HTTP error'));
    } else {
      var content = (res.data.choices || [{}])[0].message
                    ? res.data.choices[0].message.content
                    : '(empty response)';
      messages.push({ role: 'assistant', content: content });
      appendMessage('assistant', content);
    }
  })
  .catch(function(err) {
    removeLoading(loadingId);
    appendMessage('error', '\\u26A0 Network error: ' + err.message);
  })
  .finally(function() {
    isLoading = false;
    document.getElementById('send-btn').disabled = false;
    document.getElementById('message-input').focus();
  });
}

function appendMessage(role, content) {
  var c = document.getElementById('chat-messages');
  var label = role === 'user' ? 'You' : role === 'assistant' ? 'RealAI' : 'Error';
  var div = document.createElement('div');
  div.className = 'message ' + role;
  div.innerHTML = '<div class="message-meta">' + escHtml(label) + '</div>'
                + '<div class="message-bubble">' + escHtml(content) + '</div>';
  c.appendChild(div);
  c.scrollTop = c.scrollHeight;
}

function appendLoading(id) {
  var c = document.getElementById('chat-messages');
  var div = document.createElement('div');
  div.className = 'message assistant'; div.id = id;
  div.innerHTML = '<div class="message-meta">RealAI</div>'
                + '<div class="message-bubble"><div class="typing-dots">'
                + '<span></span><span></span><span></span></div></div>';
  c.appendChild(div);
  c.scrollTop = c.scrollHeight;
}

function removeLoading(id) {
  var el = document.getElementById(id);
  if (el) el.remove();
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------
var _toastTimer;
function toast(msg) {
  var el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(function(){ el.classList.remove('show'); }, 2800);
}
</script>
</body>
</html>"""


class RealAIAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for RealAI API."""

    def _send_response(self, status_code: int, data):
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_html_response(self, status_code: int, html: str):
        """Send an HTML response."""
        body = html.encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        """Read and parse JSON body."""
        raw_cl = self.headers.get('Content-Length', '0')
        try:
            content_length = int(raw_cl)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid Content-Length header: {raw_cl!r}")
        body = self.rfile.read(content_length)
        return json.loads(body.decode()) if body else {}

    def _resolve_user_id(self) -> str:
        """Return a stable external identifier for the calling user.

        Resolution order
        ----------------
        1. If an ``Authorization: Bearer <key>`` header is present, return
           ``key:<first-16-hex-chars-of-sha256(key)>``.  This gives a
           consistent, non-reversible identity without storing the raw key.
        2. Otherwise return ``anon:<client_ip>``, where ``client_ip`` is read
           from ``X-Forwarded-For`` (first entry) or ``X-Real-IP`` before
           falling back to the TCP connection address.  This ensures the
           correct address is used when the server runs behind a reverse proxy
           or load balancer.
        """
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            raw_key = auth[len("Bearer "):].strip()
            if raw_key:
                digest = hashlib.sha256(raw_key.encode()).hexdigest()
                return f"key:{digest[:16]}"
        # Prefer forwarded-for headers so the anonymous identity reflects the
        # real client rather than the address of an intermediate proxy.
        forwarded_for = self.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = (
                self.headers.get("X-Real-IP")
                or (self.client_address[0] if self.client_address else "unknown")
            )
        return f"anon:{client_ip}"

    def _get_model(self, model_name: str = "realai-2.0") -> RealAI:
        """Build a :class:`~realai.RealAI` instance from request headers.

        Reads the API key from the ``Authorization: Bearer <key>`` header, the
        optional provider override from ``X-Provider``, and the optional base
        URL from ``X-Base-URL``.

        When no ``Authorization`` header is present the method falls back to
        ``REALAI_<PROVIDER>_API_KEY`` environment variables so the GUI launcher
        can pass keys via the process environment without requiring callers to
        set the header explicitly.
        """
        auth = self.headers.get("Authorization", "")
        api_key = auth[len("Bearer "):].strip() if auth.startswith("Bearer ") else None
        provider = self.headers.get("X-Provider") or None
        base_url = self.headers.get("X-Base-URL") or None

        # Fall back to environment variables set by the GUI launcher.
        # Priority follows the insertion order of PROVIDER_ENV_VARS
        # (openai → anthropic → grok → gemini); the first key found wins.
        if not api_key:
            for _provider, _env_var in PROVIDER_ENV_VARS.items():
                _key = os.environ.get(_env_var, "")
                if _key:
                    api_key = _key
                    if not provider:
                        provider = _provider
                    break

        return RealAI(model_name=model_name, api_key=api_key,
                      provider=provider, base_url=base_url)

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers',
                         'Content-Type, Authorization, X-Provider, X-Base-URL')
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)

        if parsed_path.path in ('/', '/ui'):
            self._send_html_response(200, _WEB_UI_HTML)

        elif parsed_path.path == '/ui/providers':
            # Return provider metadata so the web UI can populate helper text.
            # Never exposes actual key values — only label and placeholder text.
            providers = []
            for name, meta in _PROVIDER_META.items():
                providers.append({
                    "id": name,
                    "label": meta["label"],
                    "placeholder": meta["placeholder"],
                })
            self._send_response(200, providers)

        elif parsed_path.path == '/v1/models':
            # List available models: RealAI's own plus any configured providers.
            models = [
                {
                    "id": "realai-2.0",
                    "object": "model",
                    "created": 1708308000,
                    "owned_by": "realai",
                    "permission": [],
                    "root": "realai-2.0",
                    "parent": None,
                }
            ]
            for provider_name, cfg in PROVIDER_CONFIGS.items():
                models.append({
                    "id": cfg["default_model"],
                    "object": "model",
                    "created": 1708308000,
                    "owned_by": provider_name,
                    "permission": [],
                    "root": cfg["default_model"],
                    "parent": None,
                })
            self._send_response(200, {"object": "list", "data": models})

        elif parsed_path.path.startswith('/v1/models/'):
            model_id = parsed_path.path[len('/v1/models/'):]
            model = self._get_model(model_name=model_id)
            response = model.get_model_info()
            response["object"] = "model"
            response["id"] = model_id
            self._send_response(200, response)

        elif parsed_path.path == '/v1/capabilities':
            model = self._get_model()
            self._send_response(200, model.get_capability_catalog())

        elif parsed_path.path == '/v1/providers/capabilities':
            model = self._get_model()
            provider = parse_qs(parsed_path.query).get("provider", [None])[0]
            self._send_response(200, model.get_provider_capabilities(provider=provider))

        elif parsed_path.path == '/health':
            self._send_response(200, {"status": "healthy", "model": "realai-2.0"})

        else:
            self._send_response(404, {"error": "Not found"})

    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)

        try:
            body = self._read_body()
            # The 'model' field in the body is passed through to RealAI as the
            # preferred provider model name.  Provider routing still depends on
            # the API key and X-Provider header; if no key is supplied the
            # response falls back to RealAI's placeholder regardless of model.
            model_name = body.get('model', 'realai-2.0')

            # When the caller provides a Bearer token but no explicit
            # X-Provider, attempt prefix-based detection.  If no prefix
            # matches, return a clear 400 so the caller knows to pick a
            # provider explicitly (e.g. via the web-UI dropdown or the
            # X-Provider header) rather than silently receiving placeholder
            # responses.
            _auth_header = self.headers.get("Authorization", "")
            _bearer_key = (
                _auth_header[len("Bearer "):].strip()
                if _auth_header.startswith("Bearer ")
                else None
            )
            if _bearer_key and not (self.headers.get("X-Provider") or None):
                _detected = any(
                    _bearer_key.startswith(p)
                    for p in _KEY_PREFIX_TO_PROVIDER
                )
                if not _detected:
                    raise ValueError(
                        "Cannot auto-detect provider from your API key. "
                        "Please select a provider using the Provider dropdown "
                        "in the web UI, or add an X-Provider header "
                        "(openai, anthropic, grok, gemini, openrouter, "
                        "mistral, together, deepseek, perplexity)."
                    )

            model = self._get_model(model_name=model_name)

            if parsed_path.path == '/v1/chat/completions':
                response = model.chat_completion(
                    messages=body.get('messages', []),
                    temperature=body.get('temperature', 0.7),
                    max_tokens=body.get('max_tokens'),
                    stream=body.get('stream', False)
                )
                self._send_response(200, response)

            elif parsed_path.path == '/v1/completions':
                response = model.text_completion(
                    prompt=body.get('prompt', ''),
                    temperature=body.get('temperature', 0.7),
                    max_tokens=body.get('max_tokens')
                )
                self._send_response(200, response)

            elif parsed_path.path == '/v1/images/generations':
                response = model.generate_image(
                    prompt=body.get('prompt', ''),
                    size=body.get('size', '1024x1024'),
                    quality=body.get('quality', 'standard'),
                    n=body.get('n', 1)
                )
                self._send_response(200, response)

            elif parsed_path.path == '/v1/videos/generations':
                response = model.generate_video(
                    prompt=body.get('prompt', ''),
                    image_url=body.get('image_url'),
                    size=body.get('size', '1280x720'),
                    duration=body.get('duration', 5),
                    fps=body.get('fps', 24),
                    n=body.get('n', 1),
                    response_format=body.get('response_format', 'url'),
                    model=body.get('model')
                )
                self._send_response(200, response)

            elif parsed_path.path == '/v1/embeddings':
                response = model.create_embeddings(
                    input_text=body.get('input', ''),
                    model=body.get('model', 'realai-embeddings')
                )
                self._send_response(200, response)

            elif parsed_path.path == '/v1/audio/transcriptions':
                response = model.transcribe_audio(
                    audio_file=body.get('file', ''),
                    language=body.get('language'),
                    prompt=body.get('prompt')
                )
                self._send_response(200, response)

            elif parsed_path.path == '/v1/audio/speech':
                response = model.generate_audio(
                    text=body.get('input', ''),
                    voice=body.get('voice', 'alloy'),
                    model=body.get('model', 'realai-tts')
                )
                self._send_response(200, response)

            elif parsed_path.path == '/v1/reasoning/chain':
                response = model.chain_of_thought(
                    problem=body.get('problem', ''),
                    domain=body.get('domain')
                )
                self._send_response(200, response)

            elif parsed_path.path == '/v1/synthesis/knowledge':
                response = model.synthesize_knowledge(
                    topics=body.get('topics', []),
                    output_format=body.get('output_format', 'narrative')
                )
                self._send_response(200, response)

            elif parsed_path.path == '/v1/reflection/analyze':
                response = model.self_reflect(
                    interaction_history=body.get('interaction_history'),
                    focus=body.get('focus', 'general')
                )
                self._send_response(200, response)

            elif parsed_path.path == '/v1/agents/orchestrate':
                response = model.orchestrate_agents(
                    task=body.get('task', ''),
                    agent_roles=body.get('agent_roles')
                )
                self._send_response(200, response)

            else:
                self._send_response(404, {"error": "Endpoint not found"})

        except json.JSONDecodeError:
            self._send_response(400, {"error": "Invalid JSON"})
        except ValueError as e:
            self._send_response(400, {"error": str(e)})
        except Exception as e:
            self._send_response(500, {"error": str(e)})

    def log_message(self, format, *args):
        """Log API requests."""
        print(f"[{self.log_date_time_string()}] {format % args}")


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """
    Start the RealAI API server.

    Args:
        host (str): Host to bind to
        port (int): Port to listen on
    """
    # Initialise the database once before accepting any requests.
    db_path = os.environ.get("REALAI_DB_PATH", _DEFAULT_DB_PATH)
    init_db(db_path)

    server_address = (host, port)
    httpd = HTTPServer(server_address, RealAIAPIHandler)

    ui_host = 'localhost' if host in ('0.0.0.0', '::') else host
    print("="*60)
    print("RealAI API Server")
    print("="*60)
    print(f"Server running at http://{host}:{port}")
    print(f"\n  *** Open the chat UI: http://{ui_host}:{port}/ ***\n")
    print("Available endpoints:")
    print("  GET  /              Web chat UI (browser)")
    print("  GET  /ui            Web chat UI (browser, alias)")
    print("  GET  /ui/providers  Provider metadata (JSON)")
    print("  GET  /health")
    print("  GET  /v1/models")
    print("  GET  /v1/models/<model-id>")
    print("  GET  /v1/capabilities")
    print("  GET  /v1/providers/capabilities?provider=<name>")
    print("  POST /v1/chat/completions")
    print("  POST /v1/completions")
    print("  POST /v1/images/generations")
    print("  POST /v1/embeddings")
    print("  POST /v1/audio/transcriptions")
    print("  POST /v1/audio/speech")
    print("  POST /v1/reasoning/chain")
    print("  POST /v1/synthesis/knowledge")
    print("  POST /v1/reflection/analyze")
    print("  POST /v1/agents/orchestrate")
    print("\nPass your API key via:  Authorization: Bearer <key>")
    print("Override provider via:  X-Provider: openai|anthropic|grok|gemini|openrouter|mistral|together|deepseek|perplexity")
    print("Override base URL via:  X-Base-URL: https://...")
    print("\nPress Ctrl+C to stop the server")
    print("="*60)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        httpd.shutdown()


def main():
    """Entry point for running the API server as a module."""
    port = int(os.environ.get("PORT", 8000))
    run_server(port=port)


if __name__ == "__main__":
    main()
