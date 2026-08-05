"""Inference helpers for the structured RealAI server."""

import time

from .backends import RESOLVER, SamplingConfig
from .config import get_model_config
from .logging_utils import setup_logging
from .metrics import LATENCY, REQUESTS, TOKENS

logger = setup_logging()


def chat_completion(model_name, messages, temperature=0.2, max_tokens=1024):
    """Run a chat completion request."""
    cfg = get_model_config(model_name)
    if cfg['type'] != 'chat':
        raise ValueError('Model {0} is not chat type'.format(model_name))

    REQUESTS.labels(endpoint='chat', model=model_name).inc()
    start = time.time()

    prompt = ''
    for message in messages:
        prompt += '{0}: {1}\n'.format(message['role'], message['content'])

    sampling = SamplingConfig(
        temperature=temperature,
        top_p=float(cfg.get('top_p', 1.0)),
        repetition_penalty=float(cfg.get('repetition_penalty', 1.0)),
        max_tokens=max_tokens,
    )
    text, backend_name = RESOLVER.generate(
        cfg.get('backend', ''),
        cfg.get('path', model_name),
        prompt,
        sampling,
    )

    LATENCY.labels(endpoint='chat', model=model_name).observe(time.time() - start)
    TOKENS.labels(model=model_name, direction='output').inc(len(text.split()))

    return {
        'id': 'chatcmpl-realai',
        'model': model_name,
        'choices': [
            {
                'index': 0,
                'message': {'role': 'assistant', 'content': text},
                'finish_reason': 'stop',
            }
        ],
        'backend': backend_name,
    }
