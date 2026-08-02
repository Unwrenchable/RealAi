"""Routing helpers for the structured RealAI server."""

import re
import time
from pathlib import Path

from .config import get_model_config, list_model_objects, list_models, load_settings
from .embeddings import embed
from .inference import chat_completion
from .logging_utils import setup_logging
from realai import RealAI
from .memory_store import MEMORY
from .metrics import CONTENT_TYPE_LATEST, generate_latest
from .orchestration import TASKS
from .providers import get_provider, list_providers, provider_for_model
from .tools_runtime import TOOLS
from realai.world_model import BELIEF_UPDATER, GOAL_TRACKER, PLANNING_ENGINE, WORLD_STATE
from plugins import list_plugins as list_plugin_definitions
from .router_plug import ROUTER_PLUGINS
from realai.safety import SAFETY_FILTER
from .self_evolving import SELF_EVOLVING
from .synthetic_organs import SYNTHETIC_ORGANS

logger = setup_logging()


def _runtime_skill_names():
    return sorted([
        'planner',
        'critic',
        'executor',
        'worker',
        'safety',
        'synthesizer',
    ], key=str)


def _runtime_agent_names():
    return sorted([
        'planner',
        'executor',
        'critic',
        'worker',
        'safety',
        'synthesizer',
    ], key=str)


def _get_runtime_docs_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _write_runtime_docs() -> None:
    root = _get_runtime_docs_root()
    tools = sorted((item.get('name') for item in TOOLS.list_tools() if isinstance(item, dict) and item.get('name')), key=str)
    skills = _runtime_skill_names()

    tools_doc = root / 'tools.md'
    skills_doc = root / 'skills.md'
    tools_doc.write_text(
        '# RealAI Tools\n\n'
        'This document is generated from the canonical tool runtime.\n\n'
        + ''.join(f'- {name}\n' for name in tools) + '\n',
        encoding='utf-8',
    )
    skills_doc.write_text(
        '# RealAI Skills\n\n'
        'This document is generated from the canonical skill/runtime registry.\n\n'
        + ''.join(f'- {name}\n' for name in skills) + '\n',
        encoding='utf-8',
    )


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
    _write_runtime_docs()
    settings = load_settings()
    plugin_names = [plugin.get('name') for plugin in list_plugin_definitions() if isinstance(plugin, dict) and plugin.get('name')]
    skill_names = _runtime_skill_names()
    agent_names = _runtime_agent_names()
    return {
        'status': 'ok',
        'provider': settings.provider,
        'profile': settings.profile,
        'available_models': list_models(),
        'providers': list_providers(),
        'runtime': {
            'memory': {'enabled': True, 'records': MEMORY.list('anonymous', 'default')},
            'plugins': {'count': len(plugin_names), 'enabled': True, 'names': plugin_names},
            'world': {'enabled': True, 'facts': WORLD_STATE.all_facts()},
            'tools': {'count': len(TOOLS.list_tools()), 'enabled': True},
            'skills': {'count': len(skill_names), 'enabled': True, 'names': skill_names},
            'agents': {'count': len(agent_names), 'enabled': True, 'names': agent_names},
        },
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
        'provider': cfg.get('provider', load_settings().provider),
        'type': cfg.get('type', 'chat'),
        'backend': cfg.get('backend', 'unknown'),
        'context_length': cfg.get('context_length'),
        'embedding_dimensions': cfg.get('embedding_dimensions'),
        'capabilities': cfg.get('capabilities', []),
        'path': cfg.get('path'),
    }


def handle_providers_list():
    return {'object': 'list', 'data': list_providers()}


def handle_provider_read(path):
    marker = '/v1/providers/'
    if marker not in path:
        raise RequestValidationError('Invalid provider path.')
    provider_id = path.split(marker, 1)[1]
    if not provider_id:
        raise RequestValidationError('provider_id is required.')
    return get_provider(provider_id)


def handle_provider_route(payload):
    payload = _require_dict(payload)
    model_name = payload.get('model') or load_settings().default_chat_model
    if not isinstance(model_name, str) or not model_name.strip():
        raise RequestValidationError('model is required.')
    provider = provider_for_model(model_name)
    model_cfg = get_model_config(model_name)
    return {
        'model': model_name,
        'routing': {
            'provider': provider.get('id'),
            'backend': model_cfg.get('backend', 'unknown'),
            'type': provider.get('type', 'api'),
            'health': provider.get('health', {}),
            'capabilities': model_cfg.get('capabilities', []),
            'selected': provider.get('enabled', False) and provider.get('health', {}).get('status') in {'ready', 'disabled'},
        }
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


def handle_tool_execute(payload):
    payload = _require_dict(payload)
    tool_name = payload.get('name')
    if not isinstance(tool_name, str) or not tool_name.strip():
        raise RequestValidationError('name is required.')
    params = payload.get('params', {})
    if not isinstance(params, dict):
        raise RequestValidationError('params must be an object when provided.')
    result = TOOLS.execute(tool_name, params=params, actor=payload.get('actor', 'system'))
    return {'ok': True, 'tool': tool_name, 'result': result}


def handle_tool_route(payload):
    payload = _require_dict(payload)
    text = payload.get('text')
    if not isinstance(text, str) or not text.strip():
        raise RequestValidationError('text is required.')
    allowed = payload.get('allowed_tools', [])
    if not isinstance(allowed, list) or not allowed:
        allowed = [tool['name'] for tool in TOOLS.list_tools()]
    lowered = [item for item in allowed if isinstance(item, str)]

    keyword_map = {
        'web_search': ['search', 'web', 'news', 'latest', 'find', 'browse'],
        'file_read': ['file', 'read', 'open', 'inspect', 'directory'],
        'web3_solana_rpc': ['solana', 'wallet', 'blockchain', 'rpc', 'transaction'],
    }

    text_lower = text.lower()
    scored = []
    for tool_name in lowered:
        if tool_name not in keyword_map:
            continue
        base_score = 0
        for keyword in keyword_map[tool_name]:
            if keyword in text_lower:
                base_score += 1
        plugin_score = ROUTER_PLUGINS.evaluate(tool_name, text, provider=payload.get('provider'), chain=payload.get('chain', False))
        total_score = base_score + plugin_score
        if total_score > 0 or tool_name == lowered[0]:
            scored.append((total_score, tool_name))

    if not scored:
        selected = lowered[0] if lowered else None
    else:
        selected = sorted(scored, key=lambda item: (-item[0], item[1]))[0][1]

    manifest = None
    if selected:
        try:
            manifest = TOOLS.get(selected)
        except ValueError:
            manifest = None

    chain = []
    if payload.get('chain', False):
        ordered = [item for item in lowered if item in {'file_read', 'web_search'}]
        if 'file_read' in ordered and 'web_search' in ordered:
            chain = [
                {'name': 'file_read', 'reason': 'local context first'},
                {'name': 'web_search', 'reason': 'follow-up web lookup'},
            ]

    return {
        'ok': True,
        'text': text,
        'routing': {
            'selected': manifest.to_dict() if manifest else {'name': selected},
            'provider': payload.get('provider', 'default'),
            'allowed_tools': lowered,
            'reason': 'plugin-based intent match',
            'chain': chain[: int(payload.get('max_tools', len(chain)) or len(chain))],
        },
    }


def handle_skills_list():
    return {
        'object': 'list',
        'data': [
            {'name': name, 'kind': 'skill', 'description': '{0} runtime skill'.format(name)}
            for name in _runtime_skill_names()
        ],
    }


def handle_agents_list():
    return {
        'object': 'list',
        'data': [
            {'name': name, 'kind': 'agent', 'description': '{0} runtime agent'.format(name)}
            for name in _runtime_agent_names()
        ],
    }


def handle_plugins_list():
    data = []
    for plugin in list_plugin_definitions():
        data.append({'name': plugin['name'], 'metadata': {'description': plugin['description'], 'module': plugin['module']}})
    return {'object': 'list', 'data': data}


def handle_plugin_execute(payload):
    payload = _require_dict(payload)
    name = payload.get('name')
    if not isinstance(name, str) or not name.strip():
        raise RequestValidationError('name is required.')

    plugin_module_name = None
    for plugin in list_plugin_definitions():
        if plugin.get('name') == name:
            plugin_module_name = plugin.get('module')
            break
    if not plugin_module_name:
        raise RequestValidationError('Unknown plugin.')

    module = __import__(plugin_module_name, fromlist=['register'])
    metadata = module.register(type('DummyModel', (), {})) if hasattr(module, 'register') else {}
    return {'ok': True, 'plugin': name, 'metadata': metadata, 'data': payload.get('data', {})}


def _serialize_world_facts():
    facts = {}
    for key, entry in WORLD_STATE.all_facts().items():
        if isinstance(entry, dict) and 'value' in entry:
            facts[key] = entry['value']
        else:
            facts[key] = entry
    return facts


def handle_world_state():
    return {'object': 'world_state', 'world': {'facts': _serialize_world_facts(), 'observations': len(WORLD_STATE._observations)}}


def handle_world_observe(payload):
    payload = _require_dict(payload)
    content = payload.get('content')
    if not isinstance(content, str) or not content.strip():
        raise RequestValidationError('content is required.')
    observation = WORLD_STATE.observe(content, source=payload.get('source', 'api'))
    BELIEF_UPDATER.update(WORLD_STATE, observation)
    plan = PLANNING_ENGINE.plan(content, WORLD_STATE, max_steps=3)
    GOAL_TRACKER.add_goal(content)
    return {'observed': True, 'world': {'facts': _serialize_world_facts(), 'observations': len(WORLD_STATE._observations)}, 'plan': plan}


def handle_reflection_analyze(payload):
    payload = _require_dict(payload)
    text = payload.get('text')
    if not isinstance(text, str) or not text.strip():
        raise RequestValidationError('text is required.')
    goal = payload.get('goal') or 'improve understanding'
    sentences = [segment.strip() for segment in text.split('.') if segment.strip()]
    summary = ' '.join(sentences[:3])
    if len(summary.split()) > 20:
        summary = ' '.join(summary.split()[:20]) + '...'
    return {
        'reflection': {
            'summary': summary,
            'goal': goal,
            'model': 'realai-1.0',
            'focus': 'local-runtime-reflection',
        }
    }


def handle_synthesis_knowledge(payload):
    payload = _require_dict(payload)
    facts = payload.get('facts')
    if not isinstance(facts, list) or not facts:
        raise RequestValidationError('facts must be a non-empty list.')
    model = RealAI(model_name='realai-1.0', provider='local', use_local=True)
    result = model.synthesize_knowledge(facts)
    return {
        'synthesis': {
            'summary': result.get('synthesis') or result.get('summary') or str(result),
            'connections': result.get('connections', []),
            'topics': result.get('topics', facts),
        }
    }


def handle_agents_orchestrate(payload):
    payload = _require_dict(payload)
    task = payload.get('task')
    if not isinstance(task, str) or not task.strip():
        raise RequestValidationError('task is required.')
    agents = payload.get('agents')
    if agents is None:
        agents = ['planner', 'executor']
    if not isinstance(agents, list) or not agents:
        raise RequestValidationError('agents must be a non-empty list when provided.')
    model = RealAI(model_name='realai-1.0', provider='local', use_local=True)
    result = model.orchestrate_agents(task, agent_roles=agents)
    return {
        'orchestration': {
            'task': task,
            'agents': agents,
            'status': result.get('status', 'success'),
            'summary': result.get('final_output') or result.get('summary') or str(result),
            'verification': result.get('verification', {}),
        }
    }


def handle_self_evolve(payload):
    payload = _require_dict(payload)
    text = payload.get('text')
    if not isinstance(text, str) or not text.strip():
        raise RequestValidationError('text is required.')
    tool_name = payload.get('tool_name') if isinstance(payload.get('tool_name'), str) and payload.get('tool_name').strip() else None
    diagnosis = SELF_EVOLVING.diagnose(text, tool_name=tool_name)
    critic = SELF_EVOLVING.shadow_critic(text)
    plugin = SELF_EVOLVING.generate_plugin(diagnosis)
    return {
        'ok': True,
        'self_evolution': {
            'diagnosis': diagnosis,
            'shadow_critic': critic,
            'generated_plugin': plugin,
            'state': SELF_EVOLVING.state(),
        }
    }


def handle_synthetic_organism(payload):
    payload = _require_dict(payload)
    name = payload.get('name')
    species = payload.get('species')
    prompt = payload.get('prompt') or payload.get('description') or ''
    target = payload.get('target') if isinstance(payload.get('target'), str) and payload.get('target').strip() else None

    if not isinstance(name, str) or not name.strip():
        raise RequestValidationError('name is required.')
    if not isinstance(species, str) or not species.strip():
        raise RequestValidationError('species is required.')

    record = SYNTHETIC_ORGANS.create_organism(name.strip(), species.strip(), prompt.strip())
    safety_result = SAFETY_FILTER.check_input(prompt or name)
    guardian = {
        'status': 'ok' if safety_result.ok else 'flagged' if safety_result.flagged else 'blocked',
        'reason': safety_result.reason,
    }
    return {
        'ok': True,
        'organism': record,
        'guardian': guardian,
        'curiosity': SYNTHETIC_ORGANS.curate_curiosity(target=target, prompt=prompt),
        'archeology': SYNTHETIC_ORGANS.archeology(target=target),
    }


def handle_synthetic_organisms_list():
    return {'object': 'list', 'data': SYNTHETIC_ORGANS.list_organisms()}


def handle_synthetic_organism_read(path):
    marker = '/v1/synthetic/organisms/'
    if not path.startswith(marker):
        raise RequestValidationError('Invalid synthetic organism path.', status_code=404)
    organism_id = path[len(marker):]
    if not organism_id:
        raise RequestValidationError('organism_id is required.', status_code=404)
    organism = SYNTHETIC_ORGANS.get_organism(organism_id)
    if not organism:
        raise RequestValidationError('organism not found.', status_code=404)
    return {'object': 'synthetic_organism', 'data': organism}


def handle_synthetic_curiosity(payload):
    payload = _require_dict(payload)
    target = payload.get('target') if isinstance(payload.get('target'), str) and payload.get('target').strip() else None
    prompt = payload.get('prompt') if isinstance(payload.get('prompt'), str) else None
    return SYNTHETIC_ORGANS.curate_curiosity(target=target, prompt=prompt)


def handle_synthetic_archeology(payload):
    payload = _require_dict(payload)
    target = payload.get('target') if isinstance(payload.get('target'), str) and payload.get('target').strip() else None
    return SYNTHETIC_ORGANS.archeology(target=target)


def handle_workspace_catalog(payload):
    payload = _require_dict(payload)
    root = payload.get('root') if isinstance(payload.get('root'), str) and payload.get('root').strip() else str(Path('.').resolve())
    base = Path(root).expanduser().resolve()
    if not base.exists():
        raise RequestValidationError('root path does not exist.')

    ignored_dirs = {
        '.git', '.hg', '.svn',
        '__pycache__', '.venv', 'venv',
        'node_modules', 'dist', 'build',
        '.next', '.pytest_cache', '.mypy_cache',
    }
    ignored_names = {'.DS_Store', 'Thumbs.db'}
    ignored_suffixes = {'.pyc', '.pyo', '.log', '.tmp'}

    repair_markers = re.compile(r'(todo|fixme|hack|temp|wip|placeholder|rough|legacy|broken|debug|stub)', re.I)
    structure_markers = re.compile(r'(router|service|manager|state|schema|adapter|registry|workflow|plugin|memory|agent)', re.I)
    test_markers = re.compile(r'(^|/)(test|spec|fixture|mock)(/|$)', re.I)
    version_markers = re.compile(r'\b(v1|v2|v3|alpha|beta|rc)\b', re.I)

    entries = []
    for path in base.rglob('*'):
        if not path.is_file():
            continue

        rel_parts = path.parts
        if any(part in ignored_dirs for part in rel_parts):
            continue

        if path.name in ignored_names or path.suffix.lower() in ignored_suffixes:
            continue

        rel = path.relative_to(base).as_posix()
        try:
            text = path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue

        weight = 0
        notes = []

        if path.suffix.lower() in {'.py', '.js', '.ts', '.tsx', '.jsx', '.json', '.yaml', '.yml', '.md'}:
            weight += 1

        if repair_markers.search(text):
            weight += 3
            notes.append('repair-like wording')

        if structure_markers.search(text):
            weight += 2
            notes.append('structural clues')

        if test_markers.search(rel):
            weight += 1
            notes.append('test-like path')

        if version_markers.search(text):
            weight += 1
            notes.append('version hints')

        if path.suffix.lower() in {'.py', '.ts', '.js'} and len(text.strip()) > 0:
            weight += 1

        if weight > 0:
            entries.append({
                'path': rel,
                'weight': weight,
                'notes': notes or ['general file'],
                'kind': path.suffix.lower() or 'file',
            })

    entries.sort(key=lambda item: (-item['weight'], item['path']))

    buckets = {
        'priority': [],
        'tests': [],
        'repair': [],
        'other': [],
    }
    for item in entries:
        if 'repair-like wording' in item['notes']:
            buckets['repair'].append(item)
        elif 'test-like path' in item['notes']:
            buckets['tests'].append(item)
        elif item['weight'] >= 4:
            buckets['priority'].append(item)
        else:
            buckets['other'].append(item)

    return {
        'root': base.as_posix(),
        'snapshot': {
            'files_considered': len(entries),
            'top_weight': entries[0]['weight'] if entries else 0,
        },
        'story': [
            {
                'path': item['path'],
                'weight': item['weight'],
                'notes': item['notes'],
            }
            for item in entries[:10]
        ],
        'buckets': {
            key: value[:8]
            for key, value in buckets.items()
        },
    }


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
        if method == 'GET' and path == '/v1/providers':
            return 200, handle_providers_list(), 'application/json'
        if method == 'GET' and path.startswith('/v1/providers/'):
            return 200, handle_provider_read(path), 'application/json'
        if method == 'POST' and path == '/v1/providers/route':
            return 200, handle_provider_route(payload or {}), 'application/json'
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
        if method == 'POST' and path == '/v1/tools/execute':
            return 200, handle_tool_execute(payload or {}), 'application/json'
        if method == 'POST' and path == '/v1/tools/route':
            return 200, handle_tool_route(payload or {}), 'application/json'
        if method == 'GET' and path == '/v1/skills':
            return 200, handle_skills_list(), 'application/json'
        if method == 'GET' and path == '/v1/agents':
            return 200, handle_agents_list(), 'application/json'
        if method == 'GET' and path == '/v1/plugins':
            return 200, handle_plugins_list(), 'application/json'
        if method == 'POST' and path == '/v1/plugins/execute':
            return 200, handle_plugin_execute(payload or {}), 'application/json'
        if method == 'GET' and path == '/v1/world/state':
            return 200, handle_world_state(), 'application/json'
        if method == 'POST' and path == '/v1/world/observe':
            return 200, handle_world_observe(payload or {}), 'application/json'
        if method == 'POST' and path == '/v1/reflection/analyze':
            return 200, handle_reflection_analyze(payload or {}), 'application/json'
        if method == 'POST' and path == '/v1/synthesis/knowledge':
            return 200, handle_synthesis_knowledge(payload or {}), 'application/json'
        if method == 'POST' and path == '/v1/agents/orchestrate':
            return 200, handle_agents_orchestrate(payload or {}), 'application/json'
        if method == 'POST' and path == '/v1/self/evolve':
            return 200, handle_self_evolve(payload or {}), 'application/json'
        if method == 'POST' and path in {'/v1/synthetic/organism', '/v1/synthetic/organisms', '/v1/synthetic-organism', '/v1/synthetic-organisms'}:
            return 200, handle_synthetic_organism(payload or {}), 'application/json'
        if method == 'GET' and path == '/v1/synthetic/organisms':
            return 200, handle_synthetic_organisms_list(), 'application/json'
        if method == 'GET' and path.startswith('/v1/synthetic/organisms/'):
            return 200, handle_synthetic_organism_read(path), 'application/json'
        if method == 'POST' and path == '/v1/curiosity':
            return 200, handle_synthetic_curiosity(payload or {}), 'application/json'
        if method == 'POST' and path == '/v1/archeology':
            return 200, handle_synthetic_archeology(payload or {}), 'application/json'
        if method == 'POST' and path == '/v1/workspace/catalog':
            return 200, handle_workspace_catalog(payload or {}), 'application/json'
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
