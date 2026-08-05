"""Tests for structured embeddings endpoint."""

from realai.server.router import dispatch_request


def test_embeddings_endpoint_returns_expected_shape():
    status, response, content_type = dispatch_request(
        'POST',
        '/v1/embeddings',
        {'model': 'realai-embed', 'input': ['alpha', 'beta']},
    )

    assert status == 200
    assert content_type == 'application/json'
    assert response['object'] == 'list'
    assert response['model'] == 'realai-embed'
    assert response['dimensions'] == 64
    assert len(response['data']) == 2
    assert len(response['data'][0]['embedding']) == 64
