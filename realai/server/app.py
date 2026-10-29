"""Structured RealAI inference server."""

import json
import logging
import os
from wsgiref.simple_server import make_server

from .router import dispatch_request

logger = logging.getLogger(__name__)  # was referenced in _dispatch_json but never defined

# Request body cap (Security LOW): anything larger gets 413 before it is read or parsed.
MAX_BODY_BYTES = 1024 * 1024
_TOO_LARGE = json.dumps({'error': {'message': 'Request body too large.'}}).encode('utf-8')


async def _send_413(send):
    await send({'type': 'http.response.start', 'status': 413, 'headers': [
        (b'content-type', b'application/json'), (b'content-length', str(len(_TOO_LARGE)).encode('ascii'))]})
    await send({'type': 'http.response.body', 'body': _TOO_LARGE})


class _BodyLimitASGI(object):
    """ASGI wrapper: 413 when Content-Length or the streamed body exceeds MAX_BODY_BYTES."""

    def __init__(self, app):
        self.inner = app

    async def __call__(self, scope, receive, send):
        if scope.get('type') != 'http':
            return await self.inner(scope, receive, send)
        for key, value in scope.get('headers') or []:
            if key.lower() == b'content-length':
                try:
                    if int(value) > MAX_BODY_BYTES:
                        return await _send_413(send)
                except ValueError:
                    pass
        chunks, total, more = [], 0, True
        while more:
            message = await receive()
            if message.get('type') == 'http.disconnect':
                return
            if message.get('type') != 'http.request':
                continue
            chunk = message.get('body', b'')
            total += len(chunk)
            if total > MAX_BODY_BYTES:
                return await _send_413(send)
            chunks.append(chunk)
            more = message.get('more_body', False)
        body, sent = b''.join(chunks), [False]

        async def replay():
            if not sent[0]:
                sent[0] = True
                return {'type': 'http.request', 'body': body, 'more_body': False}
            return await receive()

        return await self.inner(scope, replay, send)

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import Response
    from pydantic import BaseModel
except ImportError:
    FastAPI = None
    HTTPException = None
    Request = None
    Response = None
    BaseModel = None


class _ASGIApplication(object):
    """Minimal ASGI fallback used when FastAPI is unavailable."""

    async def __call__(self, scope, receive, send):
        if scope.get('type') != 'http':
            return

        body = b''
        more_body = True
        while more_body:
            message = await receive()
            if message.get('type') != 'http.request':
                continue
            body += message.get('body', b'')
            if len(body) > MAX_BODY_BYTES:
                return await _send_413(send)
            more_body = message.get('more_body', False)

        payload = None
        if body:
            try:
                payload = json.loads(body.decode('utf-8'))
            except ValueError:
                await _send_json(send, 400, {'error': {'message': 'Request body must be valid JSON.'}})
                return

        status_code, data, content_type = dispatch_request(
            scope.get('method', 'GET'),
            scope.get('path', '/'),
            payload,
        )
        if content_type.startswith('application/json'):
            await _send_json(send, status_code, data)
        else:
            await _send_text(send, status_code, data, content_type)


async def _send_json(send, status_code, data):
    body = json.dumps(data).encode('utf-8')
    await send({
        'type': 'http.response.start',
        'status': status_code,
        'headers': [
            (b'content-type', b'application/json'),
            (b'content-length', str(len(body)).encode('ascii')),
        ],
    })
    await send({'type': 'http.response.body', 'body': body})


async def _send_text(send, status_code, data, content_type):
    body = data.encode('utf-8')
    await send({
        'type': 'http.response.start',
        'status': status_code,
        'headers': [
            (b'content-type', content_type.encode('utf-8')),
            (b'content-length', str(len(body)).encode('ascii')),
        ],
    })
    await send({'type': 'http.response.body', 'body': body})


if FastAPI is not None and BaseModel is not None:
    class ChatRequest(BaseModel):
        """Chat completion request."""

        model: str
        messages: list
        temperature: float = 0.2
        max_tokens: int = 1024


    class EmbeddingRequest(BaseModel):
        """Embedding request."""

        model: str
        input: list

    class ImageGenerationRequest(BaseModel):
        prompt: str
        size: str = '1024x1024'
        n: int = 1

    class AudioTranscriptionRequest(BaseModel):
        file: str
        language: str = 'en'

    class AudioSpeechRequest(BaseModel):
        input: str
        voice: str = 'alloy'

    class MemoryStoreRequest(BaseModel):
        user_id: str = 'anonymous'
        agent_id: str = 'default'
        content: str
        metadata: dict = {}

    class MemoryInspectRequest(BaseModel):
        user_id: str = 'anonymous'
        agent_id: str = 'default'

    class TaskRequest(BaseModel):
        task: str
        context: str = ''


    app = FastAPI(title='RealAI Provider')
    app.add_middleware(_BodyLimitASGI)

    def _dispatch_json(method, path, payload=None):
        try:
            status, data, _content_type = dispatch_request(method, path, payload)
            if status >= 400 and HTTPException is not None:
                message = data.get('error', {}).get('message', 'Request failed')
                if status >= 500:
                    message = 'Internal server error'
                raise HTTPException(status_code=status, detail=message)
            return data
        except Exception as exc:
            if HTTPException is not None and isinstance(exc, HTTPException):
                raise
            logger.exception('Unhandled app dispatch exception: %s', exc)
            if HTTPException is not None:
                raise HTTPException(status_code=500, detail='Internal server error')
            return {'error': {'message': 'Internal server error'}}

    @app.post('/v1/chat/completions')
    def chat(request: ChatRequest):
        return _dispatch_json('POST', '/v1/chat/completions', request.dict())

    @app.post('/v1/embeddings')
    def embeddings(request: EmbeddingRequest):
        return _dispatch_json('POST', '/v1/embeddings', request.dict())

    @app.get('/v1/models')
    def models():
        return _dispatch_json('GET', '/v1/models')

    @app.get('/v1/models/{model_id}')
    def model_details(model_id: str):
        return _dispatch_json('GET', '/v1/models/{0}'.format(model_id))

    @app.get('/v1/providers')
    def providers():
        return _dispatch_json('GET', '/v1/providers')

    @app.get('/v1/providers/{provider_id}')
    def provider_details(provider_id: str):
        return _dispatch_json('GET', '/v1/providers/{0}'.format(provider_id))

    @app.post('/v1/images/generations')
    def image_generations(request: ImageGenerationRequest):
        return _dispatch_json('POST', '/v1/images/generations', request.dict())

    @app.post('/v1/audio/transcriptions')
    def audio_transcriptions(request: AudioTranscriptionRequest):
        return _dispatch_json('POST', '/v1/audio/transcriptions', request.dict())

    @app.post('/v1/audio/speech')
    def audio_speech(request: AudioSpeechRequest):
        return _dispatch_json('POST', '/v1/audio/speech', request.dict())

    @app.post('/v1/memory/store')
    def memory_store(request: MemoryStoreRequest):
        return _dispatch_json('POST', '/v1/memory/store', request.dict())

    @app.post('/v1/memory/inspect')
    def memory_inspect(request: MemoryInspectRequest):
        return _dispatch_json('POST', '/v1/memory/inspect', request.dict())

    @app.post('/v1/memory/clear')
    def memory_clear(request: MemoryInspectRequest):
        return _dispatch_json('POST', '/v1/memory/clear', request.dict())

    @app.get('/v1/tools')
    def tools():
        return _dispatch_json('GET', '/v1/tools')

    @app.post('/v1/tasks')
    def tasks_create(request: TaskRequest):
        return _dispatch_json('POST', '/v1/tasks', request.dict())

    @app.get('/v1/tasks')
    def tasks_list():
        return _dispatch_json('GET', '/v1/tasks')

    @app.get('/v1/tasks/{task_id}')
    def tasks_get(task_id: str):
        return _dispatch_json('GET', '/v1/tasks/{0}'.format(task_id))

    @app.post('/v1/tools/route')
    async def tools_route(request: Request):
        # Routes only (ranks tool names); never executes a tool. REALAI_TOOLS_ROUTE=0 disables (-> 404).
        try:
            payload = await request.json()
        except ValueError:
            payload = None
        return _dispatch_json('POST', '/v1/tools/route', payload if isinstance(payload, dict) else {})

    @app.get('/health')
    def health():
        return _dispatch_json('GET', '/health')

    @app.get('/metrics')
    def metrics():
        status_code, data, content_type = dispatch_request('GET', '/metrics')
        if Response is not None:
            return Response(content=data, media_type=content_type)
        return data

    if os.environ.get('REALAI_SERVER_MERGED_ROUTES', '').strip().lower() in ('1', 'true', 'yes', 'on'):
        # Opt-in catch-all (registered last, so every structured route above wins) -> router -> legacy bridge.
        @app.api_route('/{full_path:path}', methods=['GET', 'POST', 'DELETE'])
        async def merged_routes(full_path: str, request: Request):
            raw = await request.body()
            try:
                payload = json.loads(raw.decode('utf-8')) if raw else None
            except ValueError:
                return Response(content=json.dumps({'error': {'message': 'Request body must be valid JSON.'}}),
                                status_code=400, media_type='application/json')
            status, data, ctype = dispatch_request(request.method, '/' + full_path, payload)
            body = json.dumps(data) if ctype.startswith('application/json') else data
            return Response(content=body, status_code=status, media_type=ctype)
else:
    app = _ASGIApplication()


def wsgi_app(environ, start_response):
    """WSGI entrypoint for the structured server."""
    method = environ.get('REQUEST_METHOD', 'GET')
    path = environ.get('PATH_INFO', '/')
    payload = None
    content_length = environ.get('CONTENT_LENGTH') or '0'
    try:
        body_size = int(content_length)
    except ValueError:
        body_size = 0
    if body_size > MAX_BODY_BYTES:
        start_response('413 Payload Too Large', [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(_TOO_LARGE))),
        ])
        return [_TOO_LARGE]
    if body_size > 0:
        raw_body = environ['wsgi.input'].read(body_size)
        if raw_body:
            try:
                payload = json.loads(raw_body.decode('utf-8'))
            except ValueError:
                body = json.dumps({'error': {'message': 'Request body must be valid JSON.'}}).encode('utf-8')
                start_response('400 Bad Request', [
                    ('Content-Type', 'application/json'),
                    ('Content-Length', str(len(body))),
                ])
                return [body]

    status_code, data, content_type = dispatch_request(method, path, payload)
    body = json.dumps(data).encode('utf-8') if content_type.startswith('application/json') else data.encode('utf-8')
    start_response('{0} {1}'.format(status_code, _reason_phrase(status_code)), [
        ('Content-Type', content_type),
        ('Content-Length', str(len(body))),
    ])
    return [body]


def _reason_phrase(status_code):
    """Return a simple HTTP reason phrase."""
    if status_code == 200:
        return 'OK'
    if status_code == 400:
        return 'Bad Request'
    if status_code == 404:
        return 'Not Found'
    if status_code == 413:
        return 'Payload Too Large'
    return 'Internal Server Error'


def main(host=None, port=8000):
    """Run the structured WSGI server (default 127.0.0.1; set REALAI_SERVER_HOST=0.0.0.0 to expose)."""
    if not host:
        host = os.environ.get('REALAI_SERVER_HOST') or '127.0.0.1'
    httpd = make_server(host, int(port), wsgi_app)
    print('Structured RealAI server listening on http://{0}:{1}'.format(host, port))
    httpd.serve_forever()


if __name__ == '__main__':
    # Optional --host/--port. Default is localhost only (127.0.0.1:8000); opt in to LAN with
    # --host 0.0.0.0 or REALAI_SERVER_HOST=0.0.0.0.
    import argparse

    _ap = argparse.ArgumentParser(description='RealAI structured server (:8000)')
    _ap.add_argument('--host', default=os.environ.get('REALAI_SERVER_HOST') or '127.0.0.1')
    _ap.add_argument('--port', type=int, default=8000)
    _a = _ap.parse_args()
    main(_a.host, _a.port)
