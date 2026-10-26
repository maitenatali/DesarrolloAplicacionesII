FROM python:3.12-slim AS build
WORKDIR /src
COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install \
    "flask>=3.0,<4" "sqlalchemy>=2.0,<3" "flask-sqlalchemy>=3.1,<4" "flask-migrate>=4.0,<5" \
    "psycopg[binary]>=3.1,<4" "pydantic>=2.5,<3" "spectree>=1.2" "pyjwt[crypto]>=2.8,<3" \
    "requests>=2.31,<3" "cachetools>=5.3" "gunicorn>=22"

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 FLASK_APP=wsgi.py
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app
COPY --from=build /install /usr/local
WORKDIR /app
COPY --chown=app:app app ./app
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app wsgi.py ./
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD curl -fsS http://localhost:${PORT:-8080}/api/v1/health || exit 1
# sync workers: acta generation makes outbound calls, hence the 60 s timeout
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "3", "--timeout", "60", "wsgi:app"]
