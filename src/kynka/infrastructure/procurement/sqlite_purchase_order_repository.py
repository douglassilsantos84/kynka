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

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS purchase_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL DEFAULT 'draft',
                    demand_ids TEXT NOT NULL DEFAULT '[]',
                    demand_codes TEXT NOT NULL DEFAULT '[]',
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
                    FOREIGN KEY(order_id) REFERENCES purchase_orders(id)
                        ON DELETE CASCADE
                );
                """
            )

    def create_order(self, demand_ids, demand_codes, notes, items) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO purchase_orders(
                    status, demand_ids, demand_codes, notes, created_at
                ) VALUES ('draft', ?, ?, ?, ?)
                """,
                (json.dumps(demand_ids), json.dumps(demand_codes), notes.strip(), now),
            )
            order_id = int(cursor.lastrowid)
            connection.executemany(
                """
                INSERT INTO purchase_order_items(
                    order_id, material_code, material_name, unit,
                    quantity_ordered, quantity_received
                ) VALUES (?, ?, ?, ?, ?, 0)
                """,
                [
                    (order_id, i.material_code, i.material_name, i.unit, i.quantity_to_buy)
                    for i in items
                ],
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
            id=row["id"], status=row["status"],
            demand_ids=json.loads(row["demand_ids"]),
            demand_codes=json.loads(row["demand_codes"]),
            notes=row["notes"], created_at=row["created_at"],
            ordered_at=row["ordered_at"], completed_at=row["completed_at"],
        )

    @staticmethod
    def _to_item(row) -> PurchaseOrderItemRecord:
        return PurchaseOrderItemRecord(
            id=row["id"], order_id=row["order_id"],
            material_code=row["material_code"], material_name=row["material_name"],
            unit=row["unit"], quantity_ordered=row["quantity_ordered"],
            quantity_received=row["quantity_received"],
        )
