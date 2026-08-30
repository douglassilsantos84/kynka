"""Persistência SQLite dos pedidos de compra da Kynka."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class PurchaseOrderRecord:
    id: int
    status: str
    demand_ids: list[int]
    demand_codes: list[str]
    supplier_id: int | None
    supplier_code: str | None
    supplier_name: str | None
    total_estimated: float
    notes: str
    created_at: str
    ordered_at: str | None
    completed_at: str | None


@dataclass(slots=True)
class PurchaseOrderItemRecord:
    id: int
    order_id: int
    material_code: str
    material_name: str
    unit: str
    quantity_ordered: float
    quantity_received: float
    unit_price: float
    total_price: float

    @property
    def quantity_pending(self) -> float:
        return max(self.quantity_ordered - self.quantity_received, 0.0)


class SQLitePurchaseOrderRepository:
    def __init__(self, database_path: str | Path) -> None:
        self._database_path = str(database_path)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _has_column(connection, table: str, column: str) -> bool:
        rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
        return any(row["name"] == column for row in rows)

    @classmethod
    def _ensure_column(cls, connection, table: str, column: str, definition: str) -> None:
        if not cls._has_column(connection, table, column):
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS purchase_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL DEFAULT 'draft',
                    demand_ids TEXT NOT NULL DEFAULT '[]',
                    demand_codes TEXT NOT NULL DEFAULT '[]',
                    supplier_id INTEGER,
                    supplier_code TEXT,
                    supplier_name TEXT,
                    total_estimated REAL NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    ordered_at TEXT,
                    completed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS purchase_order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    material_code TEXT NOT NULL,
                    material_name TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    quantity_ordered REAL NOT NULL,
                    quantity_received REAL NOT NULL DEFAULT 0,
                    unit_price REAL NOT NULL DEFAULT 0,
                    total_price REAL NOT NULL DEFAULT 0,
                    FOREIGN KEY(order_id) REFERENCES purchase_orders(id)
                        ON DELETE CASCADE
                );
                """
            )

            self._ensure_column(connection, "purchase_orders", "supplier_id", "INTEGER")
            self._ensure_column(connection, "purchase_orders", "supplier_code", "TEXT")
            self._ensure_column(connection, "purchase_orders", "supplier_name", "TEXT")
            self._ensure_column(connection, "purchase_orders", "total_estimated", "REAL NOT NULL DEFAULT 0")
            self._ensure_column(connection, "purchase_order_items", "unit_price", "REAL NOT NULL DEFAULT 0")
            self._ensure_column(connection, "purchase_order_items", "total_price", "REAL NOT NULL DEFAULT 0")

    def create_order(
        self,
        demand_ids,
        demand_codes,
        notes,
        items,
        supplier=None,
        pricing=None,
    ) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        pricing = pricing or {}
        supplier_id = supplier.id if supplier else None
        supplier_code = supplier.code if supplier else None
        supplier_name = supplier.name if supplier else None
        total_estimated = sum(
            float(pricing.get(item.material_code, {}).get("total_price", 0))
            for item in items
        )

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO purchase_orders(
                    status, demand_ids, demand_codes,
                    supplier_id, supplier_code, supplier_name, total_estimated,
                    notes, created_at
                ) VALUES ('draft', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    json.dumps(demand_ids), json.dumps(demand_codes),
                    supplier_id, supplier_code, supplier_name, total_estimated,
                    notes.strip(), now,
                ),
            )
            order_id = int(cursor.lastrowid)

            rows = []
            for item in items:
                price = pricing.get(item.material_code, {})
                order_quantity = float(price.get("order_quantity", item.quantity_to_buy))
                unit_price = float(price.get("unit_price", 0))
                total_price = float(price.get("total_price", order_quantity * unit_price))
                rows.append(
                    (
                        order_id,
                        item.material_code,
                        item.material_name,
                        item.unit,
                        order_quantity,
                        unit_price,
                        total_price,
                    )
                )

            connection.executemany(
                """
                INSERT INTO purchase_order_items(
                    order_id, material_code, material_name, unit,
                    quantity_ordered, quantity_received,
                    unit_price, total_price
                ) VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                """,
                rows,
            )
            return order_id

    def list_orders(self) -> list[PurchaseOrderRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM purchase_orders ORDER BY id DESC"
            ).fetchall()
        return [self._to_order(row) for row in rows]

    def get_order(self, order_id: int) -> PurchaseOrderRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM purchase_orders WHERE id = ?", (int(order_id),)
            ).fetchone()
        return self._to_order(row) if row else None

    def get_items(self, order_id: int) -> list[PurchaseOrderItemRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM purchase_order_items WHERE order_id = ? ORDER BY id",
                (int(order_id),),
            ).fetchall()
        return [self._to_item(row) for row in rows]

    def get_item(self, item_id: int) -> PurchaseOrderItemRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM purchase_order_items WHERE id = ?", (int(item_id),)
            ).fetchone()
        return self._to_item(row) if row else None

    def set_status(self, order_id: int, status: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        fields = {"status": status}
        if status == "ordered":
            fields["ordered_at"] = now
        if status == "received":
            fields["completed_at"] = now
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [int(order_id)]
        with self._connect() as connection:
            connection.execute(
                f"UPDATE purchase_orders SET {assignments} WHERE id = ?", values
            )

    def add_received(self, item_id: int, quantity: float) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE purchase_order_items
                SET quantity_received = quantity_received + ?
                WHERE id = ?
                """,
                (float(quantity), int(item_id)),
            )

    @staticmethod
    def _to_order(row) -> PurchaseOrderRecord:
        return PurchaseOrderRecord(
            id=row["id"],
            status=row["status"],
            demand_ids=json.loads(row["demand_ids"]),
            demand_codes=json.loads(row["demand_codes"]),
            supplier_id=row["supplier_id"],
            supplier_code=row["supplier_code"],
            supplier_name=row["supplier_name"],
            total_estimated=float(row["total_estimated"] or 0),
            notes=row["notes"],
            created_at=row["created_at"],
            ordered_at=row["ordered_at"],
            completed_at=row["completed_at"],
        )

    @staticmethod
    def _to_item(row) -> PurchaseOrderItemRecord:
        return PurchaseOrderItemRecord(
            id=row["id"],
            order_id=row["order_id"],
            material_code=row["material_code"],
            material_name=row["material_name"],
            unit=row["unit"],
            quantity_ordered=row["quantity_ordered"],
            quantity_received=row["quantity_received"],
            unit_price=float(row["unit_price"] or 0),
            total_price=float(row["total_price"] or 0),
        )
