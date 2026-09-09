# Pulse database migrations and SQLite concurrency

## Database boundaries

Pulse owns the SQLite database configured by `RESEARCH_DB`.

OpenGSC owns its own SQLite database and Prisma migration history. Pulse opens
OpenGSC read-only. Pulse migrations never modify the OpenGSC schema.

## Migration rule

All Pulse-owned schema changes live in `audit-app/db/migrations/`.

Normal request, report, crawler, integration, and service code must not execute
schema-changing SQL. Existing `ensure_*` helpers remain temporarily as no-op
compatibility hooks because callers still reference them; they no longer create
or alter schema.

Application startup validates that every known migration is applied. Startup
does not apply migrations.

Deployment sequence:

```bash
docker compose build audit-app
docker compose run --rm audit-app python -m db.migrate up
docker compose run --rm audit-app python -m db.migrate status
docker compose up -d --force-recreate
```

Never edit a migration that has already been deployed. Add a new monotonically
numbered migration.

`0001_baseline.sql` represents the materialized production/development schema
that existed before explicit migrations. `0002` adds schema that previously
existed only behind lazy runtime initialization. `0003` contains one-time
legacy data backfills that previously happened opportunistically at runtime.

## Schema ownership

`audit-app/db/ownership.py` contains one explicit owner for every Pulse-owned
table. Schema changes belong to the owning module even when other modules read
the table. The migration subsystem owns `schema_migration`.

## SQLite connection policy

Every runtime SQLite connection in `audit-app` goes through
`db.sqlite.connect_sqlite()`.

Writable Pulse connections use:

- WAL journal mode;
- `synchronous=NORMAL`;
- foreign keys enabled;
- a 30-second SQLite busy timeout;
- Python's connection timeout aligned with that busy timeout.

Read-only connections use:

- URI `mode=ro`;
- `query_only=ON`;
- foreign keys enabled;
- the same busy timeout;
- no attempt to alter journal mode on externally owned databases.

## Current concurrency assumptions

Pulse currently assumes a small number of request/worker processes and short
write transactions. WAL allows readers to continue while a writer is active,
but SQLite still permits only one writer at a time.

Rules for the current architecture:

1. Keep write transactions short.
2. Do not hold a write transaction open across network/provider work.
3. Prefer coherent batch writes over unnecessary repeated commits.
4. Let the busy timeout absorb brief writer overlap.
5. Treat sustained lock contention as a scaling signal; do not keep increasing
   the timeout.
6. The durable job system may initially use the same SQLite database, but job
   claiming must use short atomic transactions.

If worker parallelism or write volume grows enough that lock contention becomes
routine, evaluate moving the Pulse operational store to a client/server
database before increasing concurrency further.
