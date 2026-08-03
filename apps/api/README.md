# Social Media AI OS — Backend

FastAPI + SQLAlchemy + Alembic + Celery. See the
[repo root README](../../README.md) for the full picture and
[`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) for how this fits with
the frontend.

## Development

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # set DATABASE_URL, AI provider keys, etc.
alembic upgrade head
uvicorn app.main:app --reload
```

API docs at `/docs` once running. Health check at `/health`.

## Tests

Needs a reachable Postgres database. `tests/conftest.py` hardcodes
`postgresql+psycopg://postgres:postgres@localhost:5432/social_os_test` —
create that database (or edit the connection string) before running:

```bash
pytest
ruff check app tests
```

## Background jobs

```bash
celery -A app.celery_app worker --loglevel=info
celery -A app.celery_app beat --loglevel=info
```

Beat publishes due scheduled posts every 60 seconds and sends daily/weekly/
monthly summary notifications on cron.
