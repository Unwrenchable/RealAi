FROM python:3.11-slim

WORKDIR /app

# curl for compose healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Context is filtered by .dockerignore (no recovered/temp_repos/weights)
COPY main.py .
COPY realai ./realai
COPY core ./core
COPY abilities ./abilities
COPY modules ./modules
COPY plugins ./plugins
COPY agent_tools ./agent_tools
COPY apps ./apps
COPY config ./config

ENV REALAI_ENV=production \
    PYTHONUNBUFFERED=1 \
    REALAI_HEALTH_PROBE_LOCAL=0

EXPOSE 8000

# Root main.py serves blueprint-shaped /health (honest redis/postgres/vulkan probes)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
