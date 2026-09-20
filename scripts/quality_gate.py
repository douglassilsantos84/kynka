from __future__ import annotations
import argparse
import compileall
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(command):
    print("+", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-pytest", action="store_true")
    args = parser.parse_args()

    print("===== KYNKA QUALITY GATE =====")
    if not compileall.compile_dir(ROOT / "src", quiet=1):
        return 1
    print("OK   compileall")

    tracked = subprocess.run(
        ["git", "ls-files", "--", ".env", "data/kynka.db"],
        cwd=ROOT, capture_output=True, text=True
    )
    if tracked.returncode == 0 and tracked.stdout.strip():
        print("FAIL runtime/secret tracked:", tracked.stdout.strip())
        return 1
    print("OK   secrets/runtime database not tracked")

    diff = subprocess.run(["git", "diff", "--check"], cwd=ROOT)
    if diff.returncode != 0:
        return diff.returncode
    print("OK   git diff --check")

    if not args.skip_pytest:
        run([sys.executable, "-m", "pytest", "-q"])

    print("QUALITY GATE: PASSED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
