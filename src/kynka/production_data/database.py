from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse


class DatabaseBackend(str, Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


@dataclass(frozen=True)
class DatabaseConfiguration:
    """Central database configuration for the Production 1.0 migration path.

    SQLite remains the active repository backend in Etapas 39-42.
    PostgreSQL URLs are parsed and validated here, but legacy repositories
    are not silently switched to PostgreSQL.
    """

    backend: DatabaseBackend
    sqlite_path: Path | None = None
    database_url: str | None = None

    @classmethod
    def from_env(cls, default_sqlite_path: str | Path) -> "DatabaseConfiguration":
        raw = os.getenv("KYNKA_DATABASE_URL", "").strip()

        if not raw:
            return cls(
                backend=DatabaseBackend.SQLITE,
                sqlite_path=Path(default_sqlite_path),
            )

        parsed = urlparse(raw)
        scheme = parsed.scheme.lower()

        if scheme in {"sqlite", "sqlite3"}:
            if not parsed.path:
                raise ValueError("KYNKA_DATABASE_URL SQLite sem caminho.")
            return cls(
                backend=DatabaseBackend.SQLITE,
                sqlite_path=Path(parsed.path.lstrip("/") if os.name == "nt" else parsed.path),
                database_url=raw,
            )

        if scheme in {"postgres", "postgresql"}:
            if not parsed.hostname or not parsed.path.strip("/"):
                raise ValueError("KYNKA_DATABASE_URL PostgreSQL invalida.")
            return cls(
                backend=DatabaseBackend.POSTGRESQL,
                database_url=raw,
            )

        raise ValueError(f"Backend de banco nao suportado: {scheme or 'ausente'}.")

    @property
    def repositories_ready(self) -> bool:
        # PostgreSQL repository port is deliberately not claimed as complete.
        return self.backend == DatabaseBackend.SQLITE

    def require_active_repository_backend(self) -> Path:
        if self.backend != DatabaseBackend.SQLITE or self.sqlite_path is None:
            raise RuntimeError(
                "PostgreSQL foi configurado, mas os repositorios legados ainda "
                "nao foram migrados. Etapa 40 prepara a arquitetura; nao ativa "
                "PostgreSQL silenciosamente."
            )
        return self.sqlite_path
