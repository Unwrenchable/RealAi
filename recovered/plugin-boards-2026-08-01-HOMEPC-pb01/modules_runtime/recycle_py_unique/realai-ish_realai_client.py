"""Python SDK facade for the structured RealAI server."""

import os

import requests


class RealAIClient(object):
    """HTTP client for the structured RealAI server."""

    def __init__(self, api_url='http://localhost:8000'):
        self.api_url = (api_url or os.environ.get('REALAI_API_URL') or 'http://localhost:8000').rstrip('/')

    def chat(self, model, messages, **kwargs):
        """Call the chat completions endpoint."""
        response = requests.post(
            '{0}/v1/chat/completions'.format(self.api_url),
            json={
                'model': model,
                'messages': messages,
                **kwargs
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def embeddings(self, model, inputs):
        """Call the embeddings endpoint."""
        response = requests.post(
            '{0}/v1/embeddings'.format(self.api_url),
            json={
                'model': model,
                'input': inputs
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


def create_client(api_url='http://localhost:8000'):
    """Create an HTTP SDK client for the structured RealAI server."""
    return RealAIClient(api_url=api_url)
