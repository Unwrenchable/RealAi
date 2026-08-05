"""Structured RealAI inference server."""

import json
from wsgiref.simple_server import make_server

from .router import dispatch_request

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import Response
    from pydantic import BaseModel
except ImportError:
    FastAPI = None
    HTTPException = None
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

    @app.get('/health')
    def health():
        return _dispatch_json('GET', '/health')

    @app.get('/metrics')
    def metrics():
        status_code, data, content_type = dispatch_request('GET', '/metrics')
        if Response is not None:
            return Response(content=data, media_type=content_type)
        return data
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
    return 'Internal Server Error'


def main(host='0.0.0.0', port=8000):
    """Run the structured WSGI server."""
    httpd = make_server(host, int(port), wsgi_app)
    print('Structured RealAI server listening on http://{0}:{1}'.format(host, port))
    httpd.serve_forever()


if __name__ == '__main__':
    main()
