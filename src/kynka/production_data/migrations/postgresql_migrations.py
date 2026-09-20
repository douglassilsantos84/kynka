\
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from kynka.production_data.postgresql import PostgreSQLTarget


@dataclass(frozen=True)
class PostgreSQLMigration:
    version: str
    description: str
    statements: tuple[str, ...]


BASELINE_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS organizations(
        id BIGSERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users(
        id BIGSERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TEXT NOT NULL,
        last_login_at TEXT
    )
    """,
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email_lower ON users(LOWER(email))",
    """
    CREATE TABLE IF NOT EXISTS organization_memberships(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        user_id BIGINT NOT NULL,
        role TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(organization_id,user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_tokens(
        id BIGSERIAL PRIMARY KEY,
        token_hash TEXT NOT NULL UNIQUE,
        user_id BIGINT NOT NULL,
        organization_id BIGINT NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        revoked_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS platform_events(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT,
        actor_user_id BIGINT,
        event_type TEXT NOT NULL,
        entity_type TEXT,
        entity_id TEXT,
        payload TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notifications(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        user_id BIGINT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        kind TEXT NOT NULL DEFAULT 'info',
        created_at TEXT NOT NULL,
        read_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mobile_devices(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        user_id BIGINT NOT NULL,
        device_id TEXT NOT NULL,
        platform TEXT NOT NULL DEFAULT 'unknown',
        app_version TEXT,
        push_token TEXT,
        last_seen_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(organization_id,user_id,device_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS realtime_events(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        event_type TEXT NOT NULL,
        entity_type TEXT,
        entity_id TEXT,
        payload_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_realtime_events_org ON realtime_events(organization_id,id DESC)",
    """
    CREATE TABLE IF NOT EXISTS mobile_sync_operations(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        user_id BIGINT NOT NULL,
        client_operation_id TEXT NOT NULL,
        operation_type TEXT NOT NULL,
        payload_json TEXT NOT NULL DEFAULT '{}',
        status TEXT NOT NULL DEFAULT 'accepted',
        result_json TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(organization_id,user_id,client_operation_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS multimodal_sessions(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        user_id BIGINT NOT NULL,
        client_session_id TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS multimodal_events(
        id BIGSERIAL PRIMARY KEY,
        session_id BIGINT NOT NULL,
        event_type TEXT NOT NULL,
        payload_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS avatar_states(
        session_id BIGINT PRIMARY KEY,
        state TEXT NOT NULL,
        expression TEXT,
        speaking_text TEXT,
        visemes_json TEXT NOT NULL DEFAULT '[]',
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS spatial_sessions(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        user_id BIGINT NOT NULL,
        client_session_id TEXT NOT NULL,
        client_type TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS spatial_anchors(
        id BIGSERIAL PRIMARY KEY,
        session_id BIGINT NOT NULL,
        anchor_key TEXT NOT NULL,
        anchor_type TEXT NOT NULL,
        transform_json TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS spatial_objects(
        id BIGSERIAL PRIMARY KEY,
        session_id BIGINT NOT NULL,
        object_key TEXT NOT NULL,
        object_type TEXT NOT NULL,
        transform_json TEXT NOT NULL,
        resource_type TEXT,
        resource_id TEXT,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS spatial_interactions(
        id BIGSERIAL PRIMARY KEY,
        session_id BIGINT NOT NULL,
        interaction_type TEXT NOT NULL,
        target_object_key TEXT,
        intent TEXT,
        payload_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    )
    """,
)


def build_baseline_migrations() -> tuple[PostgreSQLMigration, ...]:
    return (
        PostgreSQLMigration(
            version="0040_0001",
            description="production identity mobile realtime spatial baseline",
            statements=tuple(statement.strip() for statement in BASELINE_STATEMENTS),
        ),
    )


class PostgreSQLMigrationManager:
    """Transactional, versioned PostgreSQL migrations.

    This manager is intentionally independent from SQLite MigrationManager.
    It never reads or writes the SQLite operational database.
    """

    def __init__(
        self,
        target: PostgreSQLTarget,
        migrations: Iterable[PostgreSQLMigration] | None = None,
    ) -> None:
        self.target = target
        self.migrations = tuple(migrations or build_baseline_migrations())

    def _ensure_table(self, connection) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS kynka_schema_migrations(
                    version TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL
                )
                """
            )

    def status(self) -> list[dict]:
        with self.target.connect() as connection:
            self._ensure_table(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT version, description, applied_at
                    FROM kynka_schema_migrations
                    ORDER BY version
                    """
                )
                rows = cursor.fetchall()
        return [
            {
                "version": row[0],
                "description": row[1],
                "applied_at": row[2].isoformat(),
            }
            for row in rows
        ]

    def apply(self) -> list[str]:
        applied_now: list[str] = []
        with self.target.connect() as connection:
            self._ensure_table(connection)
            with connection.cursor() as cursor:
                cursor.execute("SELECT version FROM kynka_schema_migrations")
                applied = {row[0] for row in cursor.fetchall()}

            for migration in self.migrations:
                if migration.version in applied:
                    continue
                # psycopg connection context gives commit/rollback semantics.
                with connection.transaction():
                    with connection.cursor() as cursor:
                        for statement in migration.statements:
                            cursor.execute(statement)
                        cursor.execute(
                            """
                            INSERT INTO kynka_schema_migrations(
                                version, description, applied_at
                            ) VALUES (%s, %s, %s)
                            """,
                            (
                                migration.version,
                                migration.description,
                                datetime.now(timezone.utc),
                            ),
                        )
                applied_now.append(migration.version)
        return applied_now
