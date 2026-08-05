"""Routing helpers for the structured RealAI server."""

import time

from .config import get_model_config, list_model_objects, list_models, load_settings
from .embeddings import embed
from .inference import chat_completion
from .logging_utils import setup_logging
from .memory_store import MEMORY
from .metrics import CONTENT_TYPE_LATEST, generate_latest
from .orchestration import TASKS
from .tools_runtime import TOOLS

logger = setup_logging()


class RequestValidationError(Exception):
    """Raised when a request body is invalid."""

    def __init__(self, message, status_code=400):
        super(RequestValidationError, self).__init__(message)
        self.status_code = status_code


def _require_dict(payload):
    if not isinstance(payload, dict):
        raise RequestValidationError('Request body must be a JSON object.')
    return payload


def _require_messages(messages):
    if not isinstance(messages, list) or not messages:
        raise RequestValidationError('messages must be a non-empty list.')
    for item in messages:
        if not isinstance(item, dict) or 'role' not in item or 'content' not in item:
            raise RequestValidationError('Each message must include role and content.')
    return messages


def _require_input_texts(values):
    if isinstance(values, str):
        return [values]
    if not isinstance(values, list) or not values:
        raise RequestValidationError('input must be a non-empty string or list of strings.')
    for value in values:
        if not isinstance(value, str):
            raise RequestValidationError('All embedding inputs must be strings.')
    return values


def _coalesce_model(payload, model_type='chat'):
    model_name = payload.get('model')
    if model_name:
        return model_name
    settings = load_settings()
    return settings.default_chat_model if model_type == 'chat' else settings.default_embedding_model


def _coerce_float(name, value, default, min_value=0.0, max_value=2.0):
    if value is None:
        return default
    try:
        val = float(value)
    except (TypeError, ValueError):
        raise RequestValidationError('{0} must be a number.'.format(name))
    if val < min_value or val > max_value:
        raise RequestValidationError('{0} must be between {1} and {2}.'.format(name, min_value, max_value))
    return val


def _coerce_int(name, value, default, min_value=1):
    if value is None:
        return default
    try:
        val = int(value)
    except (TypeError, ValueError):
        raise RequestValidationError('{0} must be an integer.'.format(name))
    if val < min_value:
        raise RequestValidationError('{0} must be >= {1}.'.format(name, min_value))
    return val


def health_response():
    """Return a health payload for the structured server."""
    settings = load_settings()
    return {
        'status': 'ok',
        'provider': settings.provider,
        'profile': settings.profile,
        'available_models': list_models(),
    }


def handle_chat_request(payload):
    """Handle a chat completions request."""
    payload = _require_dict(payload)
    model_name = _coalesce_model(payload, model_type='chat')
    messages = _require_messages(payload.get('messages'))
    messages_for_inference = list(messages)
    temperature = _coerce_float('temperature', payload.get('temperature', 0.2), 0.2)
    max_tokens = _coerce_int('max_tokens', payload.get('max_tokens', 1024), 1024)
    stream = bool(payload.get('stream', False))
    tools = payload.get('tools', [])
    if tools and not isinstance(tools, list):
        raise RequestValidationError('tools must be a list when provided.')

    retrieved = []
    user_id = payload.get('user_id', 'anonymous')
    agent_id = payload.get('agent_id', 'default')
    if messages:
        retrieved = MEMORY.retrieve(user_id, agent_id, str(messages[-1].get('content', '')), top_k=3)
    memory_context = '\n'.join(item.get('summary', '') for item in retrieved if item.get('summary'))
    if memory_context:
        messages_for_inference.append({'role': 'system', 'content': 'Relevant memory: {0}'.format(memory_context)})

    try:
        return chat_completion(
            model_name,
            messages_for_inference,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        logger.warning('Structured chat fallback used for %s: %s', model_name, exc)
        return {
            'id': 'chatcmpl-realai-fallback',
            'model': model_name,
            'choices': [
                {
                    'index': 0,
                    'message': {'role': 'assistant', 'content': 'Fallback response: local model runtime unavailable.'},
                    'finish_reason': 'stop',
                }
            ],
            'backend': 'structured-fallback',
        }


def handle_embeddings_request(payload):
    """Handle an embeddings request."""
    payload = _require_dict(payload)
    model_name = _coalesce_model(payload, model_type='embedding')
    inputs = _require_input_texts(payload.get('input'))
    cfg = get_model_config(model_name)
    vectors = embed(model_name, inputs)
    return {
        'object': 'list',
        'model': model_name,
        'dimensions': cfg.get('embedding_dimensions', len(vectors[0]) if vectors else 0),
        'data': [
            {
                'object': 'embedding',
                'index': index,
                'embedding': vector,
            }
            for index, vector in enumerate(vectors)
        ],
    }


def handle_images_request(payload):
    payload = _require_dict(payload)
    prompt = payload.get('prompt')
    if not isinstance(prompt, str) or not prompt.strip():
        raise RequestValidationError('prompt is required.')
    n = _coerce_int('n', payload.get('n', 1), 1)
    size = payload.get('size', '1024x1024')
    return {
        'created': int(time.time()),
        'data': [
            {'url': 'https://realai.local/generated/{0}.png'.format(index), 'revised_prompt': prompt, 'size': size}
            for index in range(n)
        ],
    }


def handle_audio_transcription(payload):
    payload = _require_dict(payload)
    audio_file = payload.get('file') or payload.get('audio_file')
    if not isinstance(audio_file, str) or not audio_file:
        raise RequestValidationError('file is required.')
    return {
        'text': 'Transcription placeholder for {0}'.format(audio_file),
        'language': payload.get('language', 'en'),
    }


def handle_audio_speech(payload):
    payload = _require_dict(payload)
    text = payload.get('input') or payload.get('text')
    if not isinstance(text, str) or not text.strip():
        raise RequestValidationError('input is required.')
    return {
        'audio_url': 'https://realai.local/audio/speech.wav',
        'voice': payload.get('voice', 'alloy'),
        'format': payload.get('format', 'wav'),
    }


def handle_models_list():
    return {'object': 'list', 'data': list_model_objects()}


def handle_model_read(path):
    marker = '/v1/models/'
    if marker not in path:
        raise RequestValidationError('Invalid model path.')
    model_id = path.split(marker, 1)[1]
    if not model_id:
        raise RequestValidationError('model_id is required.')
    cfg = get_model_config(model_id)
    return {
        'id': model_id,
        'object': 'model',
        'owned_by': cfg.get('owned_by', 'realai'),
        'type': cfg.get('type', 'chat'),
        'backend': cfg.get('backend', 'unknown'),
        'context_length': cfg.get('context_length'),
        'embedding_dimensions': cfg.get('embedding_dimensions'),
        'capabilities': cfg.get('capabilities', []),
        'path': cfg.get('path'),
    }


def handle_memory_store(payload):
    payload = _require_dict(payload)
    content = payload.get('content')
    if not isinstance(content, str) or not content.strip():
        raise RequestValidationError('content is required.')
    result = MEMORY.add(
        payload.get('user_id', 'anonymous'),
        payload.get('agent_id', 'default'),
        content,
        metadata=payload.get('metadata', {}),
    )
    return {'status': 'stored', 'memory': result}


def handle_memory_list(payload):
    payload = _require_dict(payload)
    data = MEMORY.list(payload.get('user_id', 'anonymous'), payload.get('agent_id', 'default'))
    return {'object': 'list', 'data': data}


def handle_memory_clear(payload):
    payload = _require_dict(payload)
    deleted = MEMORY.clear(payload.get('user_id', 'anonymous'), payload.get('agent_id', 'default'))
    return {'status': 'ok', 'deleted': deleted}


def handle_tools_list():
    return {'object': 'list', 'data': TOOLS.list_tools()}


def handle_tasks_create(payload):
    payload = _require_dict(payload)
    task = payload.get('task')
    if not isinstance(task, str) or not task.strip():
        raise RequestValidationError('task is required.')
    state = TASKS.create_task(payload)
    return state


def handle_tasks_list():
    return {'object': 'list', 'data': TASKS.list_tasks()}


def handle_task_read(path):
    marker = '/v1/tasks/'
    if marker not in path:
        raise RequestValidationError('Invalid task path.')
    task_id = path.split(marker, 1)[1]
    if not task_id:
        raise RequestValidationError('task_id is required.')
    return TASKS.get_task(task_id)


def _canonical_path(path):
    """Map compatibility shims to canonical v1 paths."""
    settings = load_settings()
    if not settings.enable_legacy_paths:
        return path
    remap = {
        '/chat/completions': '/v1/chat/completions',
        '/embeddings': '/v1/embeddings',
        '/audio/transcriptions': '/v1/audio/transcriptions',
        '/audio/speech': '/v1/audio/speech',
        '/images/generations': '/v1/images/generations',
        '/models': '/v1/models',
    }
    return remap.get(path, path)


def dispatch_request(method, path, payload=None):
    """Dispatch a request to the structured server router."""
    try:
        path = _canonical_path(path)
        if method == 'GET' and path == '/health':
            return 200, health_response(), 'application/json'
        if method == 'GET' and path == '/metrics':
            return 200, generate_latest().decode('utf-8'), CONTENT_TYPE_LATEST
        if method == 'GET' and path == '/v1/models':
            return 200, handle_models_list(), 'application/json'
        if method == 'GET' and path.startswith('/v1/models/'):
            return 200, handle_model_read(path), 'application/json'
        if method == 'POST' and path == '/v1/chat/completions':
            return 200, handle_chat_request(payload or {}), 'application/json'
        if method == 'POST' and path == '/v1/embeddings':
            return 200, handle_embeddings_request(payload or {}), 'application/json'
        if method == 'POST' and path == '/v1/images/generations':
            return 200, handle_images_request(payload or {}), 'application/json'
        if method == 'POST' and path == '/v1/audio/transcriptions':
            return 200, handle_audio_transcription(payload or {}), 'application/json'
        if method == 'POST' and path == '/v1/audio/speech':
            return 200, handle_audio_speech(payload or {}), 'application/json'
        if method == 'POST' and path == '/v1/memory/store':
            return 200, handle_memory_store(payload or {}), 'application/json'
        if method == 'POST' and path == '/v1/memory/inspect':
            return 200, handle_memory_list(payload or {}), 'application/json'
        if method == 'POST' and path == '/v1/memory/clear':
            return 200, handle_memory_clear(payload or {}), 'application/json'
        if method == 'GET' and path == '/v1/tools':
            return 200, handle_tools_list(), 'application/json'
        if method == 'POST' and path == '/v1/tasks':
            return 200, handle_tasks_create(payload or {}), 'application/json'
        if method == 'GET' and path == '/v1/tasks':
            return 200, handle_tasks_list(), 'application/json'
        if method == 'GET' and path.startswith('/v1/tasks/'):
            return 200, handle_task_read(path), 'application/json'
        return 404, {'error': {'message': 'Not found'}}, 'application/json'
    except RequestValidationError as exc:
        return exc.status_code, {'error': {'message': str(exc)}}, 'application/json'
    except ValueError as exc:
        return 404, {'error': {'message': str(exc)}}, 'application/json'
    except Exception as exc:
        logger.exception('Unhandled server router exception: %s', exc)
        return 500, {'error': {'message': 'Internal server error'}}, 'application/json'
