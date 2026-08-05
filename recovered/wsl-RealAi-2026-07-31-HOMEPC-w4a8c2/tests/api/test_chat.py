"""Tests for structured chat, memory, and tasks endpoints."""

from realai.server.router import dispatch_request


def test_chat_completion_returns_openai_style_payload():
    status, response, content_type = dispatch_request(
        'POST',
        '/v1/chat/completions',
        {
            'model': 'realai-1.0',
            'messages': [{'role': 'user', 'content': 'Hello there'}],
            'temperature': 0.2,
            'max_tokens': 32,
        },
    )

    assert status == 200
    assert content_type == 'application/json'
    assert response['model'] == 'realai-1.0'
    assert response['choices'][0]['message']['role'] == 'assistant'
    assert response['choices'][0]['message']['content']


def test_memory_endpoints_persist_and_retrieve():
    dispatch_request(
        'POST',
        '/v1/memory/store',
        {
            'user_id': 'memory-user',
            'agent_id': 'planner',
            'content': 'The preferred deployment region is westus3.',
            'metadata': {'source': 'test'},
        },
    )

    status, response, _content_type = dispatch_request(
        'POST',
        '/v1/memory/inspect',
        {'user_id': 'memory-user', 'agent_id': 'planner'},
    )
    assert status == 200
    assert len(response['data']) >= 1
    assert response['data'][-1]['content'] == 'The preferred deployment region is westus3.'

    clear_status, clear_response, _ = dispatch_request(
        'POST',
        '/v1/memory/clear',
        {'user_id': 'memory-user', 'agent_id': 'planner'},
    )
    assert clear_status == 200
    assert clear_response['deleted'] >= 1


def test_task_endpoints_return_persisted_steps():
    status, response, _content_type = dispatch_request(
        'POST',
        '/v1/tasks',
        {'task': 'Prepare release checklist', 'context': 'Production launch'},
    )
    assert status == 200
    task_id = response['id']
    assert response['status'] == 'completed'
    assert len(response['steps']) == 4

    read_status, read_response, _ = dispatch_request('GET', '/v1/tasks/{0}'.format(task_id))
    assert read_status == 200
    assert read_response['id'] == task_id
    assert read_response['result']['task'] == 'Prepare release checklist'
