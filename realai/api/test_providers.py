"""Tests for provider registry endpoints."""

from realai.server.providers import get_provider, list_providers, provider_for_model
from realai.server.router import dispatch_request


def test_provider_registry_lists_declared_providers():
    providers = list_providers()
    ids = {provider['id'] for provider in providers}

    assert 'local' in ids
    assert 'openai' in ids
    assert 'anthropic' in ids


def test_provider_lookup_for_model_returns_local_provider():
    provider = provider_for_model('realai-1.0')
    assert provider['id'] == 'local'
    assert provider['health']['status'] in ('ready', 'disabled', 'missing_credentials')


def test_provider_endpoints_return_provider_details():
    status, response, content_type = dispatch_request('GET', '/v1/providers')
    assert status == 200
    assert content_type == 'application/json'
    assert response['object'] == 'list'
    assert any(provider['id'] == 'local' for provider in response['data'])

    read_status, read_response, _ = dispatch_request('GET', '/v1/providers/local')
    assert read_status == 200
    assert read_response['id'] == 'local'
    assert read_response['label'] == 'Local Runtime'
