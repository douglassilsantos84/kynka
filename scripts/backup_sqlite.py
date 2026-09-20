from __future__ import annotations
import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "kynka.db"
DEFAULT_DIR = ROOT / "backups"

def main() -> int:
    parser = argparse.ArgumentParser(description="Online SQLite backup for Kynka")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()

    source = args.source.resolve()
    if not source.exists():
        raise SystemExit(f"Banco nao encontrado: {source}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = (args.output_dir / f"kynka-{stamp}.db").resolve()

    with sqlite3.connect(str(source)) as src, sqlite3.connect(str(destination)) as dst:
        src.backup(dst)
        result = dst.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            destination.unlink(missing_ok=True)
            raise SystemExit(f"Backup invalido: {result}")

    print(destination)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
