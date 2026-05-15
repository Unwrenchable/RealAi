"""Python SDK facade for the structured RealAI server."""

import os

import requests


class RealAIClient(object):
    """HTTP client for the structured RealAI server."""

    def __init__(self, api_url='http://localhost:8000', timeout=30):
        self.api_url = (api_url or os.environ.get('REALAI_API_URL') or 'http://localhost:8000').rstrip('/')
        self.timeout = timeout

    def _request(self, method, path, payload=None):
        response = requests.request(
            method,
            '{0}{1}'.format(self.api_url, path),
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        if not response.content:
            return None
        return response.json()

    def chat(self, model, messages, **kwargs):
        """Call the chat completions endpoint."""
        payload = {'model': model, 'messages': messages}
        payload.update(kwargs)
        return self._request('POST', '/v1/chat/completions', payload)

    def embeddings(self, model, inputs):
        """Call the embeddings endpoint."""
        return self._request('POST', '/v1/embeddings', {'model': model, 'input': inputs})

    def models(self):
        """List registered models."""
        return self._request('GET', '/v1/models')

    def model(self, model_id):
        """Read a single model record."""
        return self._request('GET', '/v1/models/{0}'.format(model_id))

    def providers(self):
        """List configured providers."""
        return self._request('GET', '/v1/providers')

    def provider(self, provider_id):
        """Read a single provider record."""
        return self._request('GET', '/v1/providers/{0}'.format(provider_id))

    def health(self):
        """Return server health."""
        return self._request('GET', '/health')

    def create_task(self, task, context='', **kwargs):
        """Create a structured task."""
        payload = {'task': task, 'context': context}
        payload.update(kwargs)
        return self._request('POST', '/v1/tasks', payload)

    def list_tasks(self):
        """List persisted tasks."""
        return self._request('GET', '/v1/tasks')

    def get_task(self, task_id):
        """Read a persisted task."""
        return self._request('GET', '/v1/tasks/{0}'.format(task_id))

    def store_memory(self, content, user_id='anonymous', agent_id='default', metadata=None):
        """Store scoped memory."""
        return self._request(
            'POST',
            '/v1/memory/store',
            {
                'content': content,
                'user_id': user_id,
                'agent_id': agent_id,
                'metadata': metadata or {},
            },
        )

    def inspect_memory(self, user_id='anonymous', agent_id='default'):
        """Inspect scoped memory."""
        return self._request(
            'POST',
            '/v1/memory/inspect',
            {'user_id': user_id, 'agent_id': agent_id},
        )

    def clear_memory(self, user_id='anonymous', agent_id='default'):
        """Clear scoped memory."""
        return self._request(
            'POST',
            '/v1/memory/clear',
            {'user_id': user_id, 'agent_id': agent_id},
        )


def create_client(api_url='http://localhost:8000', timeout=30):
    """Create an HTTP SDK client for the structured RealAI server."""
    return RealAIClient(api_url=api_url, timeout=timeout)
