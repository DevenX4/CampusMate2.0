# CampusMate API: FastAPI + the ingestion worker thread + the embedded vector store.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# The code lives in /app/backend, so the settings' repository root is /app: the dataset is
# mounted at /app/data, the storage volume at /app/storage, and models sit in /app/model_cache.
WORKDIR /app/backend

# Dependencies first, in their own layer: rebuilt only when pyproject.toml or the lock changes.
# Runtime packages only, at exactly the versions the tests passed with (-c requirements.lock).
COPY pyproject.toml requirements.lock ./
RUN mkdir app && touch app/__init__.py \
    && pip install -c requirements.lock . \
    && rm -rf app

# The embedding model, downloaded at build time so the container starts offline.
ENV MODEL_CACHE_DIR=/app/model_cache
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir='/app/model_cache')"

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
RUN pip install --no-deps . \
    && useradd --uid 10001 --create-home campusmate \
    && mkdir -p /app/storage \
    && chown -R campusmate /app/storage /app/model_cache

COPY --chmod=0755 docker/entrypoint.sh /usr/local/bin/campusmate-entrypoint
USER campusmate

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
    CMD python -c "import sys, urllib.request; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/system/ready', timeout=4).status != 200)"
ENTRYPOINT ["campusmate-entrypoint"]
# Only nginx can reach this port (compose network), so its X-Forwarded-For can be trusted.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
