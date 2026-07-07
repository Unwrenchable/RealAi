"""RealAI API Server - Fusion UI Priority Fixed"""

import hashlib
import json
import os
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

from . import RealAI, PROVIDER_CONFIGS, PROVIDER_ENV_VARS, _KEY_PREFIX_TO_PROVIDER
from .model_registry import MODEL_REGISTRY, get_model_metadata

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

_DEFAULT_DB_PATH = os.path.join(
    os.environ.get("REALAI_DATA_DIR", os.path.expanduser("~/.realai")),
    "conversations.db",
)

def init_db(db_path: str = _DEFAULT_DB_PATH) -> str:
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
    <span id="key-status" class="status-none" style="display:none;">No API key</span>
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
// ... (your existing script remains unchanged) ...
</script>
</body>
</html>"""

# ---------------------------------------------------------------------------
# Main Handler
# ---------------------------------------------------------------------------

class RealAIAPIHandler(BaseHTTPRequestHandler):
    def _send_response(self, code: int, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        if isinstance(data, dict):
            self.wfile.write(json.dumps(data).encode('utf-8'))
        else:
            self.wfile.write(str(data).encode('utf-8'))

    def _send_html_response(self, code: int, html: str):
        """Fixed method to send HTML responses"""
        self.send_response(code)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def do_GET(self):
        parsed_path = urlparse(self.path)

        # === FUSION UI PRIORITY ===
        if parsed_path.path in ('/', '/ui', '/index.html'):
            fusion_dir = os.environ.get("REALAI_UI_PATH", "fusion-ui")
            wants_fusion = os.environ.get("REALAI_DEFAULT_UI") == "fusion"

            index_path = Path(__file__).parent.parent / fusion_dir / "index.html"

            print(f"DEBUG Fusion: wants_fusion={wants_fusion}, path={fusion_dir}, exists={index_path.exists()}")

            if wants_fusion and index_path.exists():
                try:
                    html = index_path.read_text(encoding="utf-8")
                    print(f"✅ Serving Fusion UI from {fusion_dir}/index.html")
                    self._send_html_response(200, html)
                    return
                except Exception as e:
                    print(f"Warning: Failed to serve Fusion UI: {e}")

            # Fallback to embedded default UI
            print("⚠️ Falling back to embedded default RealAI Chat UI")
            self._send_html_response(200, _WEB_UI_HTML)
            return

        # Handle other routes (health, models, etc.)
        if parsed_path.path == '/health':
            self._send_response(200, {"status": "healthy", "model": "realai-2.0"})
            return

        if parsed_path.path == '/v1/models':
            # Keep your existing models list logic here
            self._send_response(200, {"object": "list", "data": []})  # placeholder - replace with your full list
            return

        self._send_response(404, {"error": "Not found"})

    # Keep all your existing do_POST, do_DELETE, log_message, etc. below this point
    # (I omitted them here for brevity - keep them exactly as they are in your file)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")

# ---------------------------------------------------------------------------
# Run Server
# ---------------------------------------------------------------------------

def run_server(host: str = "127.0.0.1", port: int = 8000):
    init_db()

    server_address = (host, port)
    httpd = HTTPServer(server_address, RealAIAPIHandler)

    print("="*60)
    print("RealAI API Server - Fusion UI Priority")
    print("="*60)
    print(f"Server running at http://{host}:{port}")
    print(f"→ Fusion UI: http://{host}:{port}/")
    print("="*60)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
