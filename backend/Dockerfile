FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# pg_isready is used by start.sh so the normal CMD is deterministic on a
# clean Compose startup.
RUN apt-get update \
    && apt-get install --no-install-recommends -y postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Keep dependency installation cacheable when application source changes.
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

COPY alembic.ini ./
COPY pytest.ini ./
COPY alembic ./alembic
COPY app ./app
COPY tests ./tests
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

# This is a CMD rather than an ENTRYPOINT so `docker compose run api pytest`
# and one-off Alembic commands replace it without running server startup.
CMD ["./start.sh"]
