FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0

WORKDIR /app
# Dependencies first, so code changes do not invalidate the cached dependency layer.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev --no-editable


FROM python:3.12-slim

RUN useradd --create-home app
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
USER app

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "cache_service.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
