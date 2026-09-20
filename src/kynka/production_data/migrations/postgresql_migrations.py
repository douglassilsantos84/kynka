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



BUSINESS_INTEGRATION_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS business_materials(
        organization_id BIGINT NOT NULL,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        quantity DOUBLE PRECISION NOT NULL DEFAULT 0,
        unit TEXT NOT NULL DEFAULT 'un',
        minimum_quantity DOUBLE PRECISION NOT NULL DEFAULT 0,
        PRIMARY KEY(organization_id, code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS business_inventory_movements(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        material_code TEXT NOT NULL,
        movement_type TEXT NOT NULL,
        quantity DOUBLE PRECISION NOT NULL,
        previous_quantity DOUBLE PRECISION NOT NULL,
        new_quantity DOUBLE PRECISION NOT NULL,
        reason TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_business_inventory_org_material ON business_inventory_movements(organization_id, material_code, id DESC)",
    """
    CREATE TABLE IF NOT EXISTS business_demands(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        kind TEXT NOT NULL DEFAULT 'project',
        client TEXT NOT NULL DEFAULT '',
        location TEXT NOT NULL DEFAULT '',
        start_date TEXT,
        status TEXT NOT NULL DEFAULT 'draft',
        notes TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        UNIQUE(organization_id, code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS business_demand_requirements(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        demand_id BIGINT NOT NULL,
        material_code TEXT NOT NULL,
        required_quantity DOUBLE PRECISION NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS business_stock_reservations(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        demand_id BIGINT NOT NULL,
        material_code TEXT NOT NULL,
        quantity DOUBLE PRECISION NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(organization_id, demand_id, material_code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS business_suppliers(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        nif TEXT NOT NULL DEFAULT '',
        email TEXT NOT NULL DEFAULT '',
        phone TEXT NOT NULL DEFAULT '',
        notes TEXT NOT NULL DEFAULT '',
        active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(organization_id, code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS business_supplier_materials(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        supplier_id BIGINT NOT NULL,
        material_code TEXT NOT NULL,
        unit_price DOUBLE PRECISION NOT NULL,
        lead_time_days INTEGER NOT NULL DEFAULT 0,
        minimum_order_quantity DOUBLE PRECISION NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        UNIQUE(organization_id, supplier_id, material_code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS business_supplier_price_history(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        supplier_id BIGINT NOT NULL,
        material_code TEXT NOT NULL,
        unit_price DOUBLE PRECISION NOT NULL,
        recorded_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS business_purchase_orders(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft',
        demand_ids_json TEXT NOT NULL DEFAULT '[]',
        demand_codes_json TEXT NOT NULL DEFAULT '[]',
        supplier_id BIGINT,
        supplier_code TEXT,
        supplier_name TEXT,
        total_estimated DOUBLE PRECISION NOT NULL DEFAULT 0,
        notes TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        ordered_at TEXT,
        completed_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS business_purchase_order_items(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        order_id BIGINT NOT NULL,
        material_code TEXT NOT NULL,
        material_name TEXT NOT NULL,
        unit TEXT NOT NULL,
        quantity_ordered DOUBLE PRECISION NOT NULL,
        quantity_received DOUBLE PRECISION NOT NULL DEFAULT 0,
        unit_price DOUBLE PRECISION NOT NULL DEFAULT 0,
        total_price DOUBLE PRECISION NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS business_material_requests(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        code TEXT NOT NULL,
        demand_id BIGINT NOT NULL,
        requester_name TEXT NOT NULL,
        priority TEXT NOT NULL DEFAULT 'normal',
        notes TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'requested',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        approved_at TEXT,
        ready_at TEXT,
        delivered_at TEXT,
        cancelled_at TEXT,
        UNIQUE(organization_id, code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS business_material_request_items(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        request_id BIGINT NOT NULL,
        material_code TEXT NOT NULL,
        material_name TEXT NOT NULL,
        unit TEXT NOT NULL,
        quantity_requested DOUBLE PRECISION NOT NULL,
        quantity_available DOUBLE PRECISION NOT NULL DEFAULT 0,
        quantity_separated DOUBLE PRECISION NOT NULL DEFAULT 0,
        shortage_quantity DOUBLE PRECISION NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS business_material_request_events(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        request_id BIGINT NOT NULL,
        event_type TEXT NOT NULL,
        from_status TEXT,
        to_status TEXT,
        actor TEXT NOT NULL DEFAULT '',
        notes TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS business_documents(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        original_name TEXT NOT NULL,
        stored_name TEXT NOT NULL,
        file_type TEXT NOT NULL,
        mime_type TEXT,
        size_bytes BIGINT NOT NULL DEFAULT 0,
        sha256 TEXT NOT NULL,
        title TEXT,
        category TEXT NOT NULL DEFAULT 'geral',
        status TEXT NOT NULL DEFAULT 'indexed',
        extracted_text TEXT NOT NULL DEFAULT '',
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        indexed_at TEXT,
        deleted_at TEXT,
        UNIQUE(organization_id, sha256)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS business_document_chunks(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        document_id BIGINT NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        embedding_json TEXT NOT NULL DEFAULT '[]',
        UNIQUE(organization_id, document_id, chunk_index)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS business_supplier_quote_imports(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        supplier_id BIGINT,
        supplier_code TEXT,
        supplier_name TEXT,
        file_name TEXT NOT NULL,
        file_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'review',
        total_rows INTEGER NOT NULL DEFAULT 0,
        matched_rows INTEGER NOT NULL DEFAULT 0,
        unresolved_rows INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        approved_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS business_supplier_quote_import_items(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        import_id BIGINT NOT NULL,
        row_number INTEGER NOT NULL,
        supplier_reference TEXT NOT NULL DEFAULT '',
        description TEXT NOT NULL DEFAULT '',
        unit TEXT NOT NULL DEFAULT '',
        quantity DOUBLE PRECISION,
        unit_price DOUBLE PRECISION NOT NULL,
        matched_material_code TEXT,
        match_method TEXT NOT NULL DEFAULT '',
        confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
        previous_price DOUBLE PRECISION,
        status TEXT NOT NULL DEFAULT 'review',
        raw_data TEXT NOT NULL DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS business_supplier_material_aliases(
        id BIGSERIAL PRIMARY KEY,
        organization_id BIGINT NOT NULL,
        supplier_id BIGINT NOT NULL,
        supplier_reference TEXT NOT NULL,
        material_code TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(organization_id, supplier_id, supplier_reference)
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
        PostgreSQLMigration(
            version="0055_0001",
            description="tenant scoped business product integration schema",
            statements=tuple(
                statement.strip()
                for statement in BUSINESS_INTEGRATION_STATEMENTS
            ),
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
