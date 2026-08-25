"""
Persistência SQLite para planejamento de demandas.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

from kynka.domain.demand import (
    Demand,
    DemandRepository,
    DemandRequirement,
    DemandStatus,
    StockReservation,
)


class SQLiteDemandRepository(
    DemandRepository
):
    """
    Persistência SQLite de demandas e reservas.
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
                CREATE TABLE IF NOT EXISTS demands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL DEFAULT 'project',
                    client TEXT NOT NULL DEFAULT '',
                    location TEXT NOT NULL DEFAULT '',
                    start_date TEXT,
                    status TEXT NOT NULL DEFAULT 'draft',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                demand_requirements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    demand_id INTEGER NOT NULL,

                    material_code TEXT NOT NULL,

                    required_quantity REAL NOT NULL,

                    FOREIGN KEY (demand_id)
                        REFERENCES demands(id)
                        ON DELETE CASCADE,

                    FOREIGN KEY (material_code)
                        REFERENCES materials(code)
                        ON DELETE RESTRICT,

                    UNIQUE (
                        demand_id,
                        material_code
                    )
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                stock_reservations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    demand_id INTEGER NOT NULL,

                    material_code TEXT NOT NULL,

                    quantity REAL NOT NULL DEFAULT 0,

                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,

                    FOREIGN KEY (demand_id)
                        REFERENCES demands(id)
                        ON DELETE CASCADE,

                    FOREIGN KEY (material_code)
                        REFERENCES materials(code)
                        ON DELETE RESTRICT,

                    UNIQUE (
                        demand_id,
                        material_code
                    )
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_demand_requirements_demand
                ON demand_requirements(demand_id)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_stock_reservations_material
                ON stock_reservations(material_code)
                """
            )

            connection.commit()

    # ========================================================
    # Demand
    # ========================================================

    def save_demand(
        self,
        demand: Demand,
    ) -> Demand:

        now = (
            demand.created_at
            or datetime.now()
        )

        with self._connect() as connection:

            if demand.id is None:

                cursor = connection.execute(
                    """
                    INSERT INTO demands (
                        code,
                        name,
                        kind,
                        client,
                        location,
                        start_date,
                        status,
                        notes,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        demand.code,
                        demand.name,
                        demand.kind,
                        demand.client,
                        demand.location,
                        (
                            demand.start_date.isoformat()
                            if demand.start_date
                            else None
                        ),
                        demand.status.value,
                        demand.notes,
                        now.isoformat(
                            timespec="seconds"
                        ),
                    ),
                )

                demand.id = cursor.lastrowid
                demand.created_at = now

            else:

                connection.execute(
                    """
                    UPDATE demands
                    SET
                        code = ?,
                        name = ?,
                        kind = ?,
                        client = ?,
                        location = ?,
                        start_date = ?,
                        status = ?,
                        notes = ?
                    WHERE id = ?
                    """,
                    (
                        demand.code,
                        demand.name,
                        demand.kind,
                        demand.client,
                        demand.location,
                        (
                            demand.start_date.isoformat()
                            if demand.start_date
                            else None
                        ),
                        demand.status.value,
                        demand.notes,
                        demand.id,
                    ),
                )

            connection.commit()

        return demand

    def get_demand(
        self,
        demand_id: int,
    ) -> Demand | None:

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT *
                FROM demands
                WHERE id = ?
                """,
                (demand_id,),
            ).fetchone()

        if row is None:
            return None

        return self._to_demand(
            row
        )

    def get_demand_by_code(
        self,
        code: str,
    ) -> Demand | None:

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT *
                FROM demands
                WHERE code = ?
                """,
                (code,),
            ).fetchone()

        if row is None:
            return None

        return self._to_demand(
            row
        )

    def list_demands(
        self,
    ) -> list[Demand]:

        with self._connect() as connection:

            rows = connection.execute(
                """
                SELECT *
                FROM demands
                ORDER BY created_at DESC
                """
            ).fetchall()

        return [
            self._to_demand(row)
            for row in rows
        ]

    def delete_demand(
        self,
        demand_id: int,
    ) -> bool:

        with self._connect() as connection:

            cursor = connection.execute(
                """
                DELETE FROM demands
                WHERE id = ?
                """,
                (demand_id,),
            )

            connection.commit()

            return cursor.rowcount > 0

    # ========================================================
    # Requirements
    # ========================================================

    def save_requirement(
        self,
        requirement: DemandRequirement,
    ) -> DemandRequirement:

        with self._connect() as connection:

            connection.execute(
                """
                INSERT INTO demand_requirements (
                    demand_id,
                    material_code,
                    required_quantity
                )
                VALUES (?, ?, ?)

                ON CONFLICT(
                    demand_id,
                    material_code
                )
                DO UPDATE SET
                    required_quantity =
                        excluded.required_quantity
                """,
                (
                    requirement.demand_id,
                    requirement.material_code,
                    requirement.required_quantity,
                ),
            )

            row = connection.execute(
                """
                SELECT *
                FROM demand_requirements
                WHERE demand_id = ?
                  AND material_code = ?
                """,
                (
                    requirement.demand_id,
                    requirement.material_code,
                ),
            ).fetchone()

            connection.commit()

        return self._to_requirement(
            row
        )

    def list_requirements(
        self,
        demand_id: int,
    ) -> list[DemandRequirement]:

        with self._connect() as connection:

            rows = connection.execute(
                """
                SELECT *
                FROM demand_requirements
                WHERE demand_id = ?
                ORDER BY material_code
                """,
                (demand_id,),
            ).fetchall()

        return [
            self._to_requirement(row)
            for row in rows
        ]

    def delete_requirement(
        self,
        demand_id: int,
        material_code: str,
    ) -> bool:

        with self._connect() as connection:

            cursor = connection.execute(
                """
                DELETE FROM demand_requirements
                WHERE demand_id = ?
                  AND material_code = ?
                """,
                (
                    demand_id,
                    material_code,
                ),
            )

            connection.commit()

            return cursor.rowcount > 0

    # ========================================================
    # Reservations
    # ========================================================

    def set_reservation(
        self,
        reservation: StockReservation,
    ) -> StockReservation:

        now = datetime.now()

        with self._connect() as connection:

            connection.execute(
                """
                INSERT INTO stock_reservations (
                    demand_id,
                    material_code,
                    quantity,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)

                ON CONFLICT(
                    demand_id,
                    material_code
                )
                DO UPDATE SET
                    quantity = excluded.quantity,
                    updated_at = excluded.updated_at
                """,
                (
                    reservation.demand_id,
                    reservation.material_code,
                    reservation.quantity,
                    now.isoformat(
                        timespec="seconds"
                    ),
                    now.isoformat(
                        timespec="seconds"
                    ),
                ),
            )

            row = connection.execute(
                """
                SELECT *
                FROM stock_reservations
                WHERE demand_id = ?
                  AND material_code = ?
                """,
                (
                    reservation.demand_id,
                    reservation.material_code,
                ),
            ).fetchone()

            connection.commit()

        return self._to_reservation(
            row
        )

    def get_reservation(
        self,
        demand_id: int,
        material_code: str,
    ) -> StockReservation | None:

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT *
                FROM stock_reservations
                WHERE demand_id = ?
                  AND material_code = ?
                """,
                (
                    demand_id,
                    material_code,
                ),
            ).fetchone()

        if row is None:
            return None

        return self._to_reservation(
            row
        )

    def list_reservations(
        self,
        demand_id: int,
    ) -> list[StockReservation]:

        with self._connect() as connection:

            rows = connection.execute(
                """
                SELECT *
                FROM stock_reservations
                WHERE demand_id = ?
                ORDER BY material_code
                """,
                (demand_id,),
            ).fetchall()

        return [
            self._to_reservation(row)
            for row in rows
        ]

    def total_reserved(
        self,
        material_code: str,
    ) -> float:

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT
                    COALESCE(
                        SUM(quantity),
                        0
                    ) AS total
                FROM stock_reservations
                WHERE material_code = ?
                """,
                (material_code,),
            ).fetchone()

        return float(
            row["total"]
        )

    def clear_reservations(
        self,
        demand_id: int,
    ) -> None:

        with self._connect() as connection:

            connection.execute(
                """
                DELETE FROM stock_reservations
                WHERE demand_id = ?
                """,
                (demand_id,),
            )

            connection.commit()

    # ========================================================
    # Mapping
    # ========================================================

    @staticmethod
    def _to_demand(
        row: sqlite3.Row,
    ) -> Demand:

        start_date = (
            date.fromisoformat(
                row["start_date"]
            )
            if row["start_date"]
            else None
        )

        return Demand(
            id=row["id"],
            code=row["code"],
            name=row["name"],
            kind=row["kind"],
            client=row["client"],
            location=row["location"],
            start_date=start_date,
            status=DemandStatus(
                row["status"]
            ),
            notes=row["notes"],
            created_at=datetime.fromisoformat(
                row["created_at"]
            ),
        )

    @staticmethod
    def _to_requirement(
        row: sqlite3.Row,
    ) -> DemandRequirement:

        return DemandRequirement(
            id=row["id"],
            demand_id=row["demand_id"],
            material_code=row[
                "material_code"
            ],
            required_quantity=row[
                "required_quantity"
            ],
        )

    @staticmethod
    def _to_reservation(
        row: sqlite3.Row,
    ) -> StockReservation:

        return StockReservation(
            id=row["id"],
            demand_id=row["demand_id"],
            material_code=row[
                "material_code"
            ],
            quantity=row["quantity"],
            created_at=datetime.fromisoformat(
                row["created_at"]
            ),
            updated_at=datetime.fromisoformat(
                row["updated_at"]
            ),
        )