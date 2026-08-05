"""Smoke tests for the local structured server surface."""

from realai.server.router import dispatch_request


def test_health():
    status, response, _content_type = dispatch_request('GET', '/health')
    assert status == 200
    assert response['status'] == 'ok'


def test_models():
    status, response, _content_type = dispatch_request('GET', '/v1/models')
    assert status == 200
    assert response['object'] == 'list'
    assert any(model['id'] == 'realai-1.0' for model in response['data'])


def test_chat():
    status, response, _content_type = dispatch_request(
        'POST',
        '/v1/chat/completions',
        {
            'model': 'realai-1.0',
            'messages': [{'role': 'user', 'content': 'Say hello in one sentence.'}],
            'max_tokens': 50,
        },
    )
    assert status == 200
    assert response['choices'][0]['message']['content']
