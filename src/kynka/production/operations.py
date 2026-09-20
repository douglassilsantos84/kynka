from __future__ import annotations
import os
from dataclasses import dataclass

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}

def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    value = raw.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ValueError(f"{name} deve ser booleano (true/false).")

def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"{name} deve ser inteiro positivo.") from error
    if value <= 0:
        raise ValueError(f"{name} deve ser inteiro positivo.")
    return value

@dataclass(frozen=True, slots=True)
class OperationsSettings:
    environment: str = "development"
    strict_startup: bool = False
    require_postgresql_target: bool = False
    backup_retention_days: int = 14

    @classmethod
    def from_env(cls) -> "OperationsSettings":
        environment = os.getenv("KYNKA_ENVIRONMENT", "development").strip().lower()
        if environment not in {"development", "test", "staging", "production"}:
            raise ValueError(
                "KYNKA_ENVIRONMENT deve ser development, test, staging ou production."
            )
        return cls(
            environment=environment,
            strict_startup=_bool("KYNKA_STRICT_STARTUP", False),
            require_postgresql_target=_bool("KYNKA_REQUIRE_POSTGRESQL_TARGET", False),
            backup_retention_days=_positive_int("KYNKA_BACKUP_RETENTION_DAYS", 14),
        )

    @property
    def production_like(self) -> bool:
        return self.environment in {"staging", "production"}

    def validate(self, postgresql_target) -> list[str]:
        errors: list[str] = []
        if self.require_postgresql_target and not postgresql_target.configured:
            errors.append("PostgreSQL target obrigatorio, mas nao configurado.")
        if self.production_like and not self.strict_startup:
            errors.append("staging/production exige KYNKA_STRICT_STARTUP=true.")
        return errors
