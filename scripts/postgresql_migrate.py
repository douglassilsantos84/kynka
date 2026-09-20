from __future__ import annotations
import argparse
from kynka.production_data import PostgreSQLMigrationManager, PostgreSQLTarget

def main() -> int:
    parser = argparse.ArgumentParser(description="Kynka PostgreSQL migration operator")
    parser.add_argument("command", choices=("status", "apply"))
    args = parser.parse_args()

    target = PostgreSQLTarget.from_env()
    if not target.configured:
        raise SystemExit("PostgreSQL target nao configurado.")

    manager = PostgreSQLMigrationManager(target)
    if args.command == "status":
        rows = manager.status()
        print("Migrations:", len(rows))
        for row in rows:
            print(row["version"], row["description"], row["applied_at"])
    else:
        applied = manager.apply()
        print("Aplicadas agora:", ", ".join(applied) if applied else "nenhuma")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
