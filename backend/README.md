## Local Development

1. Install uv

```
pip install uv
```

2. Install libraries.

```bash
uv sync
```

3. Start local server.

```bash
set -a && source .env && set +a
uv run uvicorn main:app --reload --port=8000
```

To skip Google OAuth during local development, start with `DEV_AUTH=true`:

```bash
DEV_AUTH=true uv run uvicorn main:app --reload --port=8000
```

This auto-sets a session cookie on the first request so you are logged in as "Dev User" without needing Google credentials.

4. Test

```bash
curl http://localhost:8000/hello
```



## Testing & Code Quality

Run tests:

```bash
uv run pytest -n auto --timeout=30 -v
```

Run linter:

```bash
uv run ruff check .
uv run ruff format --check .
```

Run type checker:

```bash
uv run mypy .
```
