FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# uv is installed via pip from PyPI. We pin a known-good version to keep
# builds reproducible; bump it intentionally.
RUN pip install --no-cache-dir uv==0.5.4

# Install dependencies first for better layer caching. The venv lives at
# /opt/venv (outside /app) so the docker-compose `:/app` bind mount can't
# shadow it at runtime.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .

# Final sync now that the project itself is on disk (installs the project
# itself into the same /opt/venv).
RUN uv sync --frozen --no-dev

ENV PATH="/opt/venv/bin:${PATH}"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
