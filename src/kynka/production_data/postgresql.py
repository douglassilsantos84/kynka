from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import psycopg


@dataclass(frozen=True)
class PostgreSQLTarget:
    """PostgreSQL migration target for Kynka Production 1.0.

    This object deliberately does not replace the active repository backend.
    During Etapa 40A PostgreSQL can be configured, connected and probed while
    the existing application repositories continue to use SQLite.
    """

    host: str | None = None
    port: int = 5432
    database: str | None = None
    user: str | None = None
    password: str | None = None
    database_url: str | None = None
    connect_timeout: int = 5

    @classmethod
    def from_env(cls) -> "PostgreSQLTarget":
        database_url = os.getenv("KYNKA_POSTGRES_URL", "").strip() or None
        if database_url:
            return cls(
                database_url=database_url,
                connect_timeout=_positive_int(
                    os.getenv("KYNKA_POSTGRES_CONNECT_TIMEOUT", "5"),
                    "KYNKA_POSTGRES_CONNECT_TIMEOUT",
                ),
            )

        host = os.getenv("KYNKA_POSTGRES_HOST", "").strip() or None
        database = os.getenv("KYNKA_POSTGRES_DB", "").strip() or None
        user = os.getenv("KYNKA_POSTGRES_USER", "").strip() or None
        password = os.getenv("KYNKA_POSTGRES_PASSWORD") or None
        port = _positive_int(
            os.getenv("KYNKA_POSTGRES_PORT", "5432"),
            "KYNKA_POSTGRES_PORT",
        )
        timeout = _positive_int(
            os.getenv("KYNKA_POSTGRES_CONNECT_TIMEOUT", "5"),
            "KYNKA_POSTGRES_CONNECT_TIMEOUT",
        )

        return cls(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            connect_timeout=timeout,
        )

    @property
    def configured(self) -> bool:
        if self.database_url:
            return True
        return all((self.host, self.database, self.user, self.password))

    def connect(self):
        if not self.configured:
            raise RuntimeError(
                "PostgreSQL target nao configurado. Defina KYNKA_POSTGRES_URL "
                "ou KYNKA_POSTGRES_HOST/PORT/DB/USER/PASSWORD."
            )

        if self.database_url:
            return psycopg.connect(
                self.database_url,
                connect_timeout=self.connect_timeout,
            )

        return psycopg.connect(
            host=self.host,
            port=self.port,
            dbname=self.database,
            user=self.user,
            password=self.password,
            connect_timeout=self.connect_timeout,
        )

    def probe(self) -> dict[str, Any]:
        if not self.configured:
            return {
                "configured": False,
                "available": False,
                "backend": "postgresql",
            }

        try:
            with self.connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT current_database(), current_user, "
                        "current_setting('server_version')"
                    )
                    database, user, version = cursor.fetchone()

            return {
                "configured": True,
                "available": True,
                "backend": "postgresql",
                "database": database,
                "user": user,
                "server_version": version,
            }
        except Exception as error:
            return {
                "configured": True,
                "available": False,
                "backend": "postgresql",
                "error_type": type(error).__name__,
            }


def _positive_int(raw: str, name: str) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} deve ser inteiro positivo.") from error
    if value <= 0:
        raise ValueError(f"{name} deve ser inteiro positivo.")
    return value
