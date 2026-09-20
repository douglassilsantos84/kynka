from __future__ import annotations
import argparse
import sqlite3
from pathlib import Path
from kynka.production import OperationsSettings
from kynka.production_data import PostgreSQLTarget

ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=ROOT/"data"/"kynka.db")
    args = parser.parse_args()

    print("===== KYNKA PRODUCTION PREFLIGHT =====")
    ops = OperationsSettings.from_env()
    pg = PostgreSQLTarget.from_env()
    errors = ops.validate(pg)

    print("environment:", ops.environment)
    print("strict_startup:", ops.strict_startup)
    print("postgresql_target_configured:", pg.configured)

    db = args.database
    if not db.exists():
        errors.append(f"SQLite operacional nao encontrado: {db}")
    else:
        with sqlite3.connect(str(db)) as c:
            result = c.execute("PRAGMA integrity_check").fetchone()[0]
        print("sqlite_integrity:", result)
        if result != "ok":
            errors.append("SQLite integrity_check falhou.")

    if ops.require_postgresql_target:
        probe = pg.probe()
        print("postgresql_available:", probe.get("available", False))
        if not probe.get("available"):
            errors.append("PostgreSQL target indisponivel.")

    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    print("PREFLIGHT: PASSED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
