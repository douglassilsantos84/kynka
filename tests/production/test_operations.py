import sqlite3
from pathlib import Path
import pytest
from kynka.production.operations import OperationsSettings

class Target:
    def __init__(self, configured=False):
        self.configured=configured

def test_default_operations(monkeypatch):
    for name in ("KYNKA_ENVIRONMENT","KYNKA_STRICT_STARTUP","KYNKA_REQUIRE_POSTGRESQL_TARGET","KYNKA_BACKUP_RETENTION_DAYS"):
        monkeypatch.delenv(name, raising=False)
    s=OperationsSettings.from_env()
    assert s.environment=="development"
    assert s.validate(Target())==[]

def test_production_requires_strict(monkeypatch):
    monkeypatch.setenv("KYNKA_ENVIRONMENT","production")
    monkeypatch.setenv("KYNKA_STRICT_STARTUP","false")
    s=OperationsSettings.from_env()
    assert any("STRICT_STARTUP" in x for x in s.validate(Target(True)))

def test_required_postgres_target(monkeypatch):
    monkeypatch.setenv("KYNKA_REQUIRE_POSTGRESQL_TARGET","true")
    s=OperationsSettings.from_env()
    assert any("PostgreSQL" in x for x in s.validate(Target(False)))

def test_invalid_boolean(monkeypatch):
    monkeypatch.setenv("KYNKA_STRICT_STARTUP","talvez")
    with pytest.raises(ValueError):
        OperationsSettings.from_env()
