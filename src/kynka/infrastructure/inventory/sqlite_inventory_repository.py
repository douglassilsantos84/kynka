"""
Implementação SQLite do repositório de inventário.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from kynka.domain.inventory import (
    InventoryMovement,
    InventoryRepository,
    Material,
    MovementType,
)


class SQLiteInventoryRepository(
    InventoryRepository
):
    """
    Repositório de inventário persistido em SQLite.
    """

    def __init__(
        self,
        database_path: str | Path,
    ) -> None:
        self._database_path = Path(
            database_path
        )

        self._database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize_database()

    def _connect(
        self,
    ) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._database_path
        )

        connection.row_factory = sqlite3.Row
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        return connection

    def _initialize_database(
        self,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS materials (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    quantity REAL NOT NULL DEFAULT 0,
                    unit TEXT NOT NULL DEFAULT 'un',
                    minimum_quantity REAL NOT NULL DEFAULT 0
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS inventory_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    material_code TEXT NOT NULL,
                    movement_type TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    previous_quantity REAL NOT NULL,
                    new_quantity REAL NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (material_code)
                        REFERENCES materials(code)
                        ON DELETE CASCADE
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_inventory_movements_material
                ON inventory_movements(material_code)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_inventory_movements_created_at
                ON inventory_movements(created_at)
                """
            )

            connection.commit()

    # ========================================================
    # Materials
    # ========================================================

    def save(
        self,
        material: Material,
    ) -> None:
        with self._connect() as connection:
            self._save_material(
                connection,
                material,
            )

            connection.commit()

    def delete(
        self,
        code: str,
    ) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM materials
                WHERE code = ?
                """,
                (code,),
            )

            connection.commit()

            return cursor.rowcount > 0

    def get_by_code(
        self,
        code: str,
    ) -> Material | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    code,
                    name,
                    quantity,
                    unit,
                    minimum_quantity
                FROM materials
                WHERE code = ?
                """,
                (code,),
            ).fetchone()

        if row is None:
            return None

        return self._to_material(row)

    def search(
        self,
        query: str,
    ) -> list[Material]:
        pattern = f"%{query.strip()}%"

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    code,
                    name,
                    quantity,
                    unit,
                    minimum_quantity
                FROM materials
                WHERE code LIKE ? COLLATE NOCASE
                   OR name LIKE ? COLLATE NOCASE
                ORDER BY name
                """,
                (
                    pattern,
                    pattern,
                ),
            ).fetchall()

        return [
            self._to_material(row)
            for row in rows
        ]

    def list_all(
        self,
    ) -> list[Material]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    code,
                    name,
                    quantity,
                    unit,
                    minimum_quantity
                FROM materials
                ORDER BY name
                """
            ).fetchall()

        return [
            self._to_material(row)
            for row in rows
        ]

    # ========================================================
    # Movements
    # ========================================================

    def save_movement(
        self,
        movement: InventoryMovement,
    ) -> InventoryMovement:
        with self._connect() as connection:
            saved = self._insert_movement(
                connection,
                movement,
            )

            connection.commit()

        return saved

    def apply_movement(
        self,
        material: Material,
        movement: InventoryMovement,
    ) -> InventoryMovement:
        """
        Atualiza o material e grava o histórico atomicamente.
        """

        with self._connect() as connection:
            try:
                self._save_material(
                    connection,
                    material,
                )

                saved = self._insert_movement(
                    connection,
                    movement,
                )

                connection.commit()

                return saved

            except Exception:
                connection.rollback()
                raise

    def list_movements(
        self,
        material_code: str | None = None,
        limit: int = 100,
    ) -> list[InventoryMovement]:
        with self._connect() as connection:
            if material_code:
                rows = connection.execute(
                    """
                    SELECT
                        id,
                        material_code,
                        movement_type,
                        quantity,
                        previous_quantity,
                        new_quantity,
                        reason,
                        created_at
                    FROM inventory_movements
                    WHERE material_code = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (
                        material_code,
                        limit,
                    ),
                ).fetchall()

            else:
                rows = connection.execute(
                    """
                    SELECT
                        id,
                        material_code,
                        movement_type,
                        quantity,
                        previous_quantity,
                        new_quantity,
                        reason,
                        created_at
                    FROM inventory_movements
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

        return [
            self._to_movement(row)
            for row in rows
        ]

    # ========================================================
    # Internal persistence
    # ========================================================

    @staticmethod
    def _save_material(
        connection: sqlite3.Connection,
        material: Material,
    ) -> None:
        connection.execute(
            """
            INSERT INTO materials (
                code,
                name,
                quantity,
                unit,
                minimum_quantity
            )
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(code)
            DO UPDATE SET
                name = excluded.name,
                quantity = excluded.quantity,
                unit = excluded.unit,
                minimum_quantity =
                    excluded.minimum_quantity
            """,
            (
                material.code,
                material.name,
                material.quantity,
                material.unit,
                material.minimum_quantity,
            ),
        )

    @staticmethod
    def _insert_movement(
        connection: sqlite3.Connection,
        movement: InventoryMovement,
    ) -> InventoryMovement:
        created_at = (
            movement.created_at
            or datetime.now()
        )

        cursor = connection.execute(
            """
            INSERT INTO inventory_movements (
                material_code,
                movement_type,
                quantity,
                previous_quantity,
                new_quantity,
                reason,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                movement.material_code,
                movement.movement_type.value,
                movement.quantity,
                movement.previous_quantity,
                movement.new_quantity,
                movement.reason,
                created_at.isoformat(
                    timespec="seconds"
                ),
            ),
        )

        return InventoryMovement(
            id=cursor.lastrowid,
            material_code=movement.material_code,
            movement_type=movement.movement_type,
            quantity=movement.quantity,
            previous_quantity=movement.previous_quantity,
            new_quantity=movement.new_quantity,
            reason=movement.reason,
            created_at=created_at,
        )

    # ========================================================
    # Mapping
    # ========================================================

    @staticmethod
    def _to_material(
        row: sqlite3.Row,
    ) -> Material:
        return Material(
            code=row["code"],
            name=row["name"],
            quantity=row["quantity"],
            unit=row["unit"],
            minimum_quantity=row[
                "minimum_quantity"
            ],
        )

    @staticmethod
    def _to_movement(
        row: sqlite3.Row,
    ) -> InventoryMovement:
        return InventoryMovement(
            id=row["id"],
            material_code=row[
                "material_code"
            ],
            movement_type=MovementType(
                row["movement_type"]
            ),
            quantity=row["quantity"],
            previous_quantity=row[
                "previous_quantity"
            ],
            new_quantity=row[
                "new_quantity"
            ],
            reason=row["reason"],
            created_at=datetime.fromisoformat(
                row["created_at"]
            ),
        )