"""
Implementação SQLite do repositório de inventário.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from kynka.domain.inventory import (
    InventoryRepository,
    Material,
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

            connection.commit()

    def save(
        self,
        material: Material,
    ) -> None:

        with self._connect() as connection:

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

            connection.commit()

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

    @staticmethod
    def _to_material(
        row: sqlite3.Row,
    ) -> Material:

        return Material(
            code=row["code"],
            name=row["name"],
            quantity=row["quantity"],
            unit=row["unit"],
            minimum_quantity=(
                row["minimum_quantity"]
            ),
        )