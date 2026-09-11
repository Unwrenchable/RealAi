"""Provider registry and adapter normalization hooks."""

import os
from dataclasses import dataclass
from typing import Any, Dict, List

from .config import get_model_config, load_settings


def _normalize_provider_config(payload: Dict[str, Any], provider_id: str) -> Dict[str, Any]:
    config = dict(payload or {})
    config.setdefault('enabled', False)
    config.setdefault('label', provider_id.replace('-', ' ').title())
    config.setdefault('type', 'api')
    config.setdefault('api_base', '')
    config.setdefault('api_key_env', '')
    config.setdefault('capabilities', [])
    config.setdefault('retry_policy', {'max_retries': 2, 'backoff_seconds': 0.5})
    return config


@dataclass
class ProviderRecord:
    provider_id: str
    config: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        env_var = self.config.get('api_key_env', '')
        return {
            'id': self.provider_id,
            'label': self.config.get('label', self.provider_id),
            'type': self.config.get('type', 'api'),
            'enabled': bool(self.config.get('enabled', False)),
            'api_base': self.config.get('api_base', ''),
            'default_backend': self.config.get('default_backend'),
            'fallback_backend': self.config.get('fallback_backend'),
            'capabilities': list(self.config.get('capabilities', [])),
            'retry_policy': dict(self.config.get('retry_policy', {})),
            'api_key_env': env_var,
            'configured': bool(env_var and os.environ.get(env_var)),
            'health': provider_health(self.provider_id),
        }


def list_provider_configs() -> Dict[str, Dict[str, Any]]:
    settings = load_settings()
    raw = settings.providers.get('providers', settings.providers)
    if not isinstance(raw, dict):
        return {}
    return {
        provider_id: _normalize_provider_config(payload if isinstance(payload, dict) else {}, provider_id)
        for provider_id, payload in raw.items()
    }


def list_providers() -> List[Dict[str, Any]]:
    providers = []
    for provider_id, payload in sorted(list_provider_configs().items()):
        providers.append(ProviderRecord(provider_id=provider_id, config=payload).to_dict())
    return providers


def get_provider(provider_id: str) -> Dict[str, Any]:
    providers = list_provider_configs()
    if provider_id not in providers:
        raise ValueError('Unknown provider {0}'.format(provider_id))
    return ProviderRecord(provider_id=provider_id, config=providers[provider_id]).to_dict()


def provider_for_model(model_name: str) -> Dict[str, Any]:
    model = get_model_config(model_name)
    provider_id = model.get('provider') or load_settings().provider
    return get_provider(str(provider_id))


def normalize_provider_response(provider: str, payload: Dict[str, Any]):
    """Normalize provider-specific payloads into a common chat shape."""
    name = (provider or '').lower()
    if name == 'anthropic':
        content = payload.get('content', '')
        if isinstance(content, list) and content:
            content = content[0].get('text', '')
        return {'content': content, 'provider': 'anthropic'}
    if name == 'gemini':
        candidates = payload.get('candidates', [])
        text = ''
        if candidates:
            parts = candidates[0].get('content', {}).get('parts', [])
            if parts:
                text = parts[0].get('text', '')
        return {'content': text, 'provider': 'gemini'}
    if name == 'openai':
        choices = payload.get('choices', [])
        text = ''
        if choices:
            text = choices[0].get('message', {}).get('content', '')
        return {'content': text, 'provider': 'openai'}
    return {'content': payload.get('content', ''), 'provider': provider or 'unknown'}


def provider_health(provider: str):
    """Return normalized provider health shape."""
    config = list_provider_configs().get(provider, {})
    env_var = config.get('api_key_env', '')
    enabled = bool(config.get('enabled', False))
    configured = bool(env_var and os.environ.get(env_var)) if env_var else enabled
    if config.get('type') == 'local':
        status = 'ready' if enabled else 'disabled'
    elif not enabled:
        status = 'disabled'
    elif configured:
        status = 'ready'
    else:
        status = 'missing_credentials'
    return {
        'provider': provider,
        'status': status,
        'enabled': enabled,
        'configured': configured,
        'retry_policy': dict(config.get('retry_policy', {'max_retries': 2, 'backoff_seconds': 0.5})),
    }
