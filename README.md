# payload-cache

A small FastAPI service that builds a payload out of two lists of strings and caches every call
to the (slow, external) transformer, plus a CLI client for it.

```
POST /payload        {"list_1": [...], "list_2": [...]}  ->  {"id": "...", "message": "..."}
GET  /payload/{id}                                        ->  {"output": "A, X, B, Y, ..."}
GET  /health
```

`POST` answers `201` when the payload is new and `200` with the existing id when the same
input was already generated.

## Running

```bash
docker compose up --build
```

The API is on http://localhost:8000 (docs at `/docs`). Postgres is exposed on port 5433 so it
does not clash with a local one; set `DB_PORT` to use another port (and update the database
URLs below to match).

Without Docker for the app itself:

```bash
uv sync
docker compose up -d db
cp .env.example .env
uv run uvicorn cache_service.main:create_app --factory --reload
```

Settings come from environment variables (or `.env`):

| Variable | Default | |
|---|---|---|
| `CACHE_SERVICE_DATABASE_URL` | required | `postgresql+asyncpg://...` |
| `CACHE_SERVICE_TRANSFORMER_DELAY_SECONDS` | `0.5` | latency of the simulated transformer |

## CLI

```bash
uv run cache-cli -j '{"list_1": ["a", "b"], "list_2": ["c", "d"]}' -r 3
uv run cache-cli -H http://localhost:8000 -i payload.json -o results.jsonl
cat payload.json | uv run cache-cli -i -
```

Each iteration sends `POST` + `GET` and writes one JSON line with the id, whether the payload
was created, the round trip time and the output. Running with `-r 3` shows the cache at work:
the first call takes the transformer delay, the next ones take a few milliseconds.

Exactly one of `--input` / `--json` is required; arguments are validated by Pydantic Settings
before any request is made, and errors are reported as one line with a non-zero exit code.

## Tests

```bash
docker compose up -d db
uv run pytest
```

Unit tests cover the payload helpers and CLI argument parsing. API tests run the real app
against Postgres (`TEST_DATABASE_URL`, defaults to the compose database) with a fake
transformer that records its calls, so they check the main requirement directly: a string is
never sent to the transformer twice. Tests truncate the tables, so do not point them at a
database you care about.

Static checks: `uv run ruff check .` and `uv run mypy`.

## How it works

`POST /payload` goes through `PayloadService.create`:

1. Hash the input (`sha256` of the two lists as JSON) and look for an existing payload with
   that hash. If it exists, return its id. Nothing else happens.
2. Collect the unique strings of both lists and load the ones already transformed in a single
   `SELECT ... WHERE input_hash IN (...)`.
3. Call the transformer only for the missing strings, concurrently.
4. Store the new transformations and the payload in one transaction and return the id.

The cache is per string, not per payload, so a new payload that shares strings with an old one
only pays for the new strings. Strings are keyed by their hash because Postgres cannot index
arbitrarily long text.

Both inserts use `ON CONFLICT DO NOTHING`. Two requests racing on the same input do not fail
with a unique violation; the one that loses reads the id the other one stored, so both clients
get the same id.

## Decisions and assumptions

- **`-h` for `--help`.** The task lists `-h` for both `--host` and `--help`. argparse cannot
  have both, so `--help` keeps `-h` and the host is `-H`.
- **Input limits.** Lists must be non-empty, of the same length, at most 1000 items, strings at
  most 1000 characters. An empty payload has no meaning, and the limits stop one request from
  turning into an unbounded number of transformer calls.
- **Strings are used as is.** No trimming or case folding: `"a"` and `"a "` are different
  inputs to the transformer, so they are cached separately.
- **The output is stored.** `GET` is a single primary key lookup instead of rebuilding the
  output from the cache.
- **Random ids.** The id is a UUID, not the input hash, so it does not reveal anything about
  the input.

## Known limitations

- Two concurrent requests with the same *new* string both call the transformer. The result is
  still correct (the second insert is ignored), it just costs an extra call. Fixing it needs a
  per-string lock, e.g. an in-process map of pending calls or a Postgres advisory lock.
- If one transformer call fails, the whole request fails with 500 and nothing is stored, even
  the calls that succeeded.
- Tables are created on startup with `create_all`. Any schema change should go through Alembic.
- Cached transformations never expire. If the transformer changed its behaviour, the cache
  would need a version column or a cleanup.
- No authentication or rate limiting.
