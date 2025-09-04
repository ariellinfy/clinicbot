
# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1         PYTHONUNBUFFERED=1

# Faster installs with uv and build cache
RUN apt-get update && apt-get install -y --no-install-recommends         build-essential git curl ca-certificates         && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh &&         ln -s /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app
COPY backend/requirements.txt /tmp/requirements.txt

# Use BuildKit cache mounts to avoid re-downloading wheels
RUN --mount=type=cache,target=/root/.cache/uv         uv pip install --system --upgrade pip &&         uv pip install --system -r /tmp/requirements.txt

COPY backend/app /app/app
RUN mkdir -p /app/data/json /app/data/chroma_db

EXPOSE 8000
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
