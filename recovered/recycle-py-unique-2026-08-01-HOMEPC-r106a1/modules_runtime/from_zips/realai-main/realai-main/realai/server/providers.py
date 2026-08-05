"""Provider adapter hooks for normalized behavior."""

from typing import Any, Dict


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
    return {
        'provider': provider,
        'status': 'configured',
        'retry_policy': {'max_retries': 2, 'backoff_seconds': 0.5},
    }

