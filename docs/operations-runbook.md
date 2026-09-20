
# Kynka Production 1.0 — Operations Runbook

## Scope
Etapas 51–54 add operational configuration, container health checks, safe SQLite
backup, PostgreSQL migration operator, preflight and deployment diagnostics.

They do **not** switch legacy business repositories to PostgreSQL.

## Local production preflight
Run `python scripts/production_preflight.py`.

## SQLite backup
Run `python scripts/backup_sqlite.py`.
The script uses SQLite's online backup API and validates the result with
`PRAGMA integrity_check`. Backups are written under `backups/` by default.

## PostgreSQL migrations
With the existing local `.env` loaded:
`python scripts/postgresql_migrate.py status`
`python scripts/postgresql_migrate.py apply`

The script never prints the PostgreSQL password.

## Docker
`docker compose config`
`docker compose build kynka-api`
The API image runs as the unprivileged `kynka` user and has an HTTP healthcheck.

The PostgreSQL service remains under the `postgres` profile and keeps the
existing named volume `kynka-postgres-data`.

## Production-like environments
For staging/production set `KYNKA_STRICT_STARTUP=true`.
Set `KYNKA_REQUIRE_POSTGRESQL_TARGET=true` only when PostgreSQL availability
must participate in readiness. This still does not migrate legacy repositories.
