"""Persistência SQLite de fornecedores, catálogos e histórico de preços."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class SupplierRecord:
    id: int
    code: str
    name: str
    nif: str
    email: str
    phone: str
    notes: str
    active: bool
    created_at: str
    updated_at: str


@dataclass(slots=True)
class SupplierMaterialRecord:
    id: int
    supplier_id: int
    material_code: str
    unit_price: float
    lead_time_days: int
    minimum_order_quantity: float
    updated_at: str


@dataclass(slots=True)
class SupplierPriceHistoryRecord:
    id: int
    supplier_id: int
    material_code: str
    unit_price: float
    recorded_at: str


class SQLiteSupplierRepository:
    def __init__(self, database_path: str | Path) -> None:
        self._database_path = Path(database_path)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS suppliers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    nif TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    phone TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS supplier_materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supplier_id INTEGER NOT NULL,
                    material_code TEXT NOT NULL,
                    unit_price REAL NOT NULL,
                    lead_time_days INTEGER NOT NULL DEFAULT 0,
                    minimum_order_quantity REAL NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    UNIQUE(supplier_id, material_code),
                    FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
                        ON DELETE CASCADE,
                    FOREIGN KEY(material_code) REFERENCES materials(code)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS supplier_price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supplier_id INTEGER NOT NULL,
                    material_code TEXT NOT NULL,
                    unit_price REAL NOT NULL,
                    recorded_at TEXT NOT NULL,
                    FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
                        ON DELETE CASCADE,
                    FOREIGN KEY(material_code) REFERENCES materials(code)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_supplier_materials_material
                    ON supplier_materials(material_code);

                CREATE INDEX IF NOT EXISTS idx_supplier_price_history_lookup
                    ON supplier_price_history(supplier_id, material_code, id DESC);
                """
            )

    def create_supplier(
        self,
        code: str,
        name: str,
        nif: str,
        email: str,
        phone: str,
        notes: str,
    ) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO suppliers(
                    code, name, nif, email, phone, notes,
                    active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (code, name, nif, email, phone, notes, now, now),
            )
            return int(cursor.lastrowid)

    def update_supplier(
        self,
        supplier_id: int,
        name: str,
        nif: str,
        email: str,
        phone: str,
        notes: str,
    ) -> bool:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE suppliers
                SET name = ?, nif = ?, email = ?, phone = ?, notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (name, nif, email, phone, notes, now, int(supplier_id)),
            )
            return cursor.rowcount > 0

    def set_active(self, supplier_id: int, active: bool) -> bool:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE suppliers SET active = ?, updated_at = ? WHERE id = ?",
                (1 if active else 0, now, int(supplier_id)),
            )
            return cursor.rowcount > 0

    def get_supplier(self, supplier_id: int) -> SupplierRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM suppliers WHERE id = ?",
                (int(supplier_id),),
            ).fetchone()
        return self._to_supplier(row) if row else None

    def get_supplier_by_code(self, code: str) -> SupplierRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM suppliers WHERE code = ? COLLATE NOCASE",
                (code,),
            ).fetchone()
        return self._to_supplier(row) if row else None

    def list_suppliers(self, active_only: bool = False) -> list[SupplierRecord]:
        sql = "SELECT * FROM suppliers"
        params: tuple = ()
        if active_only:
            sql += " WHERE active = 1"
        sql += " ORDER BY name COLLATE NOCASE, code COLLATE NOCASE"
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._to_supplier(row) for row in rows]

    def upsert_material(
        self,
        supplier_id: int,
        material_code: str,
        unit_price: float,
        lead_time_days: int,
        minimum_order_quantity: float,
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as connection:
            previous = connection.execute(
                """
                SELECT unit_price FROM supplier_materials
                WHERE supplier_id = ? AND material_code = ?
                """,
                (int(supplier_id), material_code),
            ).fetchone()

            connection.execute(
                """
                INSERT INTO supplier_materials(
                    supplier_id, material_code, unit_price,
                    lead_time_days, minimum_order_quantity, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(supplier_id, material_code)
                DO UPDATE SET
                    unit_price = excluded.unit_price,
                    lead_time_days = excluded.lead_time_days,
                    minimum_order_quantity = excluded.minimum_order_quantity,
                    updated_at = excluded.updated_at
                """,
                (
                    int(supplier_id), material_code, float(unit_price),
                    int(lead_time_days), float(minimum_order_quantity), now,
                ),
            )

            if previous is None or float(previous["unit_price"]) != float(unit_price):
                connection.execute(
                    """
                    INSERT INTO supplier_price_history(
                        supplier_id, material_code, unit_price, recorded_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (int(supplier_id), material_code, float(unit_price), now),
                )

    def remove_material(self, supplier_id: int, material_code: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM supplier_materials
                WHERE supplier_id = ? AND material_code = ?
                """,
                (int(supplier_id), material_code),
            )
            return cursor.rowcount > 0

    def get_supplier_material(
        self,
        supplier_id: int,
        material_code: str,
    ) -> SupplierMaterialRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM supplier_materials
                WHERE supplier_id = ? AND material_code = ?
                """,
                (int(supplier_id), material_code),
            ).fetchone()
        return self._to_supplier_material(row) if row else None

    def list_supplier_materials(self, supplier_id: int) -> list[SupplierMaterialRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM supplier_materials
                WHERE supplier_id = ?
                ORDER BY material_code COLLATE NOCASE
                """,
                (int(supplier_id),),
            ).fetchall()
        return [self._to_supplier_material(row) for row in rows]

    def list_material_suppliers(self, material_code: str) -> list[tuple[SupplierRecord, SupplierMaterialRecord]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    s.id AS s_id, s.code AS s_code, s.name AS s_name,
                    s.nif AS s_nif, s.email AS s_email, s.phone AS s_phone,
                    s.notes AS s_notes, s.active AS s_active,
                    s.created_at AS s_created_at, s.updated_at AS s_updated_at,
                    sm.id AS sm_id, sm.supplier_id AS sm_supplier_id,
                    sm.material_code AS sm_material_code,
                    sm.unit_price AS sm_unit_price,
                    sm.lead_time_days AS sm_lead_time_days,
                    sm.minimum_order_quantity AS sm_minimum_order_quantity,
                    sm.updated_at AS sm_updated_at
                FROM supplier_materials sm
                JOIN suppliers s ON s.id = sm.supplier_id
                WHERE sm.material_code = ? AND s.active = 1
                ORDER BY sm.unit_price ASC, sm.lead_time_days ASC, s.name COLLATE NOCASE
                """,
                (material_code,),
            ).fetchall()

        result = []
        for row in rows:
            supplier = SupplierRecord(
                id=row["s_id"], code=row["s_code"], name=row["s_name"],
                nif=row["s_nif"], email=row["s_email"], phone=row["s_phone"],
                notes=row["s_notes"], active=bool(row["s_active"]),
                created_at=row["s_created_at"], updated_at=row["s_updated_at"],
            )
            material = SupplierMaterialRecord(
                id=row["sm_id"], supplier_id=row["sm_supplier_id"],
                material_code=row["sm_material_code"],
                unit_price=row["sm_unit_price"],
                lead_time_days=row["sm_lead_time_days"],
                minimum_order_quantity=row["sm_minimum_order_quantity"],
                updated_at=row["sm_updated_at"],
            )
            result.append((supplier, material))
        return result

    def price_history(
        self,
        supplier_id: int,
        material_code: str,
        limit: int = 50,
    ) -> list[SupplierPriceHistoryRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM supplier_price_history
                WHERE supplier_id = ? AND material_code = ?
                ORDER BY id DESC LIMIT ?
                """,
                (int(supplier_id), material_code, int(limit)),
            ).fetchall()
        return [
            SupplierPriceHistoryRecord(
                id=row["id"], supplier_id=row["supplier_id"],
                material_code=row["material_code"], unit_price=row["unit_price"],
                recorded_at=row["recorded_at"],
            )
            for row in rows
        ]

    @staticmethod
    def _to_supplier(row: sqlite3.Row) -> SupplierRecord:
        return SupplierRecord(
            id=row["id"], code=row["code"], name=row["name"],
            nif=row["nif"], email=row["email"], phone=row["phone"],
            notes=row["notes"], active=bool(row["active"]),
            created_at=row["created_at"], updated_at=row["updated_at"],
        )

    @staticmethod
    def _to_supplier_material(row: sqlite3.Row) -> SupplierMaterialRecord:
        return SupplierMaterialRecord(
            id=row["id"], supplier_id=row["supplier_id"],
            material_code=row["material_code"], unit_price=row["unit_price"],
            lead_time_days=row["lead_time_days"],
            minimum_order_quantity=row["minimum_order_quantity"],
            updated_at=row["updated_at"],
        )
