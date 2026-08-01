"""
realai Main API Server - Cleaned
"""

from aura.reasoning.core import get_reasoner
from aura.memory.engine import get_memory
from server_settings import settings
from model_registry import MODEL_REGISTRY, get_model_metadata
from realai import RealAI, PROVIDER_ENV_VARS, _KEY_PREFIX_TO_PROVIDER

import sys
import os
import json
import sqlite3
import requests
import hashlib

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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


_PROVIDER_META = {
    "openai": {"label": "OpenAI", "placeholder": "sk-..."},
    "anthropic": {"label": "Anthropic", "placeholder": "sk-ant-..."},
    "grok": {"label": "xAI / Grok", "placeholder": "xai-..."},
    "gemini": {"label": "Google Gemini", "placeholder": "AIza..."},
    "openrouter": {"label": "OpenRouter", "placeholder": "sk-or-v1-..."},
    "mistral": {"label": "Mistral AI", "placeholder": "..."},
    "together": {"label": "Together AI", "placeholder": "..."},
    "deepseek": {"label": "DeepSeek", "placeholder": "..."},
    "perplexity": {"label": "Perplexity AI", "placeholder": "pplx-..."},
}


_WEB_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>realai Chat</title>
</head>
<body style="font-family:system-ui,Segoe UI,Arial; background:#0d0d1a; color:#e0e0ff;">
  <div style="padding:16px; border-bottom:1px solid #2a2a5a;">
    <b>realai</b> <span style="opacity:.8">API server</span>
  </div>
  <div style="padding:16px;">
    <p>This UI is a minimal placeholder.</p>
    <p>Use API endpoints directly (see server logs).</p>
  </div>
</body>
</html>"""


class RealAIAPIHandler(BaseHTTPRequestHandler):
    def _send_response(self, status_code: int, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_html_response(self, status_code: int, html: str):
        body = html.encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        raw_cl = self.headers.get('Content-Length', '0')
        try:
            content_length = int(raw_cl)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid Content-Length header: {raw_cl!r}")
        body = self.rfile.read(content_length)
        return json.loads(body.decode()) if body else {}

    def _get_model(self, model_name: str = 'realai-2.0') -> 'RealAI':
        auth = self.headers.get('Authorization', '')
        api_key = auth[len('Bearer '):].strip() if auth.startswith('Bearer ') else None
        provider = self.headers.get('X-Provider') or None
        base_url = self.headers.get('X-Base-URL') or None

        if not api_key:
            for _provider, _env_var in PROVIDER_ENV_VARS.items():
                _key = os.environ.get(_env_var, '')
                if _key:
                    api_key = _key
                    if not provider:
                        provider = _provider
                    break

        # Keep compatibility with existing RealAI constructor signature.
        return RealAI(
            model_name=model_name,
            api_key=api_key,
            provider=provider,
            base_url=base_url,
        )

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Provider, X-Base-URL')
        self.end_headers()

    def do_GET(self):
        parsed_path = urlparse(self.path)

        if parsed_path.path in ('/', '/ui'):
            self._send_html_response(200, _WEB_UI_HTML)
            return

        if parsed_path.path == '/ui/providers':
            providers = [
                {
                    'id': name,
                    'label': meta['label'],
                    'placeholder': meta['placeholder'],
                }
                for name, meta in _PROVIDER_META.items()
            ]
            self._send_response(200, providers)
            return

        if parsed_path.path == '/v1/models':
            self._send_response(200, MODEL_REGISTRY.to_openai_list())
            return

        if parsed_path.path.startswith('/v1/models/'):
            model_id = parsed_path.path[len('/v1/models/'):]
            response = get_model_metadata(model_id)
            if response is None:
                self._send_response(404, {'error': f"Unknown model '{model_id}'"})
            else:
                self._send_response(200, response)
            return

        if parsed_path.path == '/v1/capabilities':
            self._send_response(200, MODEL_REGISTRY.to_capabilities_payload())
            return

        if parsed_path.path == '/v1/providers/capabilities':
            model = self._get_model()
            provider = parse_qs(parsed_path.query).get('provider', [None])[0]
            self._send_response(200, model.get_provider_capabilities(provider=provider))
            return

        if parsed_path.path == '/v1/tools':
            try:
                from realai.tools import TOOL_REGISTRY

                self._send_response(200, {'tools': TOOL_REGISTRY.to_openai_format()})
            except Exception as e:
                import traceback as _traceback

                _tb = _traceback.format_exc()
                self._send_response(500, {'error': str(e), 'trace': _tb})
            return

        if parsed_path.path == '/health':
            self._send_response(200, {'status': 'healthy', 'model': 'realai-2.0'})
            return

        self._send_response(404, {'error': 'Not found'})

    def do_POST(self):
        parsed_path = urlparse(self.path)
        try:
            body = self._read_body()
            model_name = body.get('model', 'realai-2.0')

            model = self._get_model(model_name=model_name)

            if parsed_path.path == '/v1/chat/completions':
                try:
                    llama_response = requests.post(
                        'http://127.0.0.1:8000/v1/chat/completions',
                        json=body,
                        timeout=60,
                    )
                    self._send_response(llama_response.status_code, llama_response.json())
                except Exception as e:
                    import traceback as _traceback

                    _tb = _traceback.format_exc()
                    self._send_response(500, {'error': str(e), 'trace': _tb})
                return

            if parsed_path.path == '/v1/completions':
                response = model.text_completion(
                    prompt=body.get('prompt', ''),
                    temperature=body.get('temperature', 0.7),
                    max_tokens=body.get('max_tokens'),
                )
                self._send_response(200, response)
                return

            self._send_response(404, {'error': 'Endpoint not found'})

        except json.JSONDecodeError:
            self._send_response(400, {'error': 'Invalid JSON'})
        except ValueError as e:
            self._send_response(400, {'error': str(e)})
        except Exception:
            self._send_response(500, {'error': 'Server error'})

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")


def run_server(host: str = '127.0.0.1', port: int = 8000):
    db_path = os.environ.get('REALAI_DB_PATH', _DEFAULT_DB_PATH)
    init_db(db_path)

    httpd = HTTPServer((host, port), RealAIAPIHandler)

    print('=' * 60)
    print('realai API Server')
    print('=' * 60)
    print(f'Server running at http://{host}:{port}')
    print('\n *** Open the chat UI: http://127.0.0.1:8000/ ***\n')
    print('Available endpoints:')
    print('  GET  /              Web chat UI (browser)')
    print('  GET  /ui/providers  Provider metadata (JSON)')
    print('  GET  /health')
    print('  GET  /v1/models')
    print('  GET  /v1/capabilities')
    print('  GET  /v1/providers/capabilities?provider=<name>')
    print('  GET  /v1/tools')
    print('  POST /v1/chat/completions')
    print('  POST /v1/completions')
    print('\nPress Ctrl+C to stop the server')
    print('=' * 60)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n\nShutting down server...')
        httpd.shutdown()


def main():
    port = int(os.environ.get('PORT', 8000))
    run_server(port=port)


if __name__ == '__main__':
    print('realai Main API Server running')
    run_server(port=settings.PORT)

