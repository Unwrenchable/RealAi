"""Metrics helpers for the structured RealAI server."""

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
except ImportError:
    CONTENT_TYPE_LATEST = 'text/plain; version=0.0.4'

    class _MetricHandle(object):
        """Minimal in-memory metric handle."""

        def __init__(self):
            self.value = 0.0

        def inc(self, amount=1):
            self.value += amount

        def observe(self, amount):
            self.value += amount

    class _Metric(object):
        """Minimal metric implementation compatible with prometheus_client."""

        def __init__(self, name, description, label_names):
            self.name = name
            self.description = description
            self.label_names = tuple(label_names)
            self._values = {}

        def labels(self, **labels):
            key = tuple((name, labels.get(name, '')) for name in self.label_names)
            if key not in self._values:
                self._values[key] = _MetricHandle()
            return self._values[key]

        def render(self):
            lines = ['# HELP {0} {1}'.format(self.name, self.description)]
            lines.append('# TYPE {0} counter'.format(self.name))
            for key, handle in sorted(self._values.items()):
                if key:
                    label_text = ','.join('{0}="{1}"'.format(name, value) for name, value in key)
                    lines.append('{0}{{{1}}} {2}'.format(self.name, label_text, handle.value))
                else:
                    lines.append('{0} {1}'.format(self.name, handle.value))
            return '\n'.join(lines)

    _FALLBACK_METRICS = []

    def Counter(name, description, label_names):
        metric = _Metric(name, description, label_names)
        _FALLBACK_METRICS.append(metric)
        return metric

    def Histogram(name, description, label_names):
        metric = _Metric(name, description, label_names)
        _FALLBACK_METRICS.append(metric)
        return metric

    def generate_latest():
        rendered = []
        for metric in _FALLBACK_METRICS:
            rendered.append(metric.render())
        return ('\n'.join(rendered) + '\n').encode('utf-8')


REQUESTS = Counter('realai_requests_total', 'Total API requests', ['endpoint', 'model'])
TOKENS = Counter('realai_tokens_total', 'Total tokens processed', ['model', 'direction'])
LATENCY = Histogram('realai_request_latency_seconds', 'Request latency', ['endpoint', 'model'])
