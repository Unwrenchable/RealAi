"""Project smoke tests for the current RealAI platform surface."""

from realai import ModelCapability, PROVIDER_CONFIGS, PROVIDER_ENV_VARS, RealAI, RealAIClient, _detect_provider
from realai.server.router import dispatch_request


def test_package_exports_are_available():
    assert RealAI is not None
    assert RealAIClient is not None
    assert ModelCapability is not None
    assert isinstance(PROVIDER_CONFIGS, dict)
    assert isinstance(PROVIDER_ENV_VARS, dict)


def test_provider_detection_smoke():
    assert _detect_provider('sk-test', None) == 'openai'
    assert _detect_provider('sk-ant-test', None) == 'anthropic'
    assert _detect_provider(None, 'gemini') == 'gemini'


def test_structured_server_smoke():
    health_status, health_response, _ = dispatch_request('GET', '/health')
    assert health_status == 200
    assert health_response['status'] == 'ok'
    assert 'realai-1.0' in health_response['available_models']

    chat_status, chat_response, _ = dispatch_request(
        'POST',
        '/v1/chat/completions',
        {
            'model': 'realai-1.0',
            'messages': [{'role': 'user', 'content': 'Summarize the platform.'}],
        },
    )
    assert chat_status == 200
    assert 'choices' in chat_response

    embedding_status, embedding_response, _ = dispatch_request(
        'POST',
        '/v1/embeddings',
        {'model': 'realai-embed', 'input': ['platform overview']},
    )
    assert embedding_status == 200
    assert len(embedding_response['data']) == 1
