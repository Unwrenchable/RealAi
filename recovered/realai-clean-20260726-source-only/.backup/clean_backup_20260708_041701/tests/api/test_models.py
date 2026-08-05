"""Tests for model registry normalization and model endpoints."""

from realai.server.config import get_model_config, list_models
from realai.server.router import dispatch_request


def test_registry_normalizes_model_manifest():
    models = list_models()

    assert 'realai-1.0' in models
    assert 'realai-embed' in models

    chat_model = get_model_config('realai-1.0')
    embed_model = get_model_config('realai-embed')

    assert chat_model['type'] == 'chat'
    assert embed_model['type'] == 'embedding'
    assert embed_model['embedding_dimensions'] == 64


def test_models_endpoint_lists_registered_models():
    status, response, content_type = dispatch_request('GET', '/v1/models')

    assert status == 200
    assert content_type == 'application/json'
    assert response['object'] == 'list'
    assert any(model['id'] == 'realai-1.0' for model in response['data'])
    assert any(model['id'] == 'realai-embed' for model in response['data'])
