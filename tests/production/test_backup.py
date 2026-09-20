import sqlite3, subprocess, sys
from pathlib import Path

def test_online_backup(tmp_path: Path):
    source=tmp_path/"source.db"
    output=tmp_path/"backup"
    with sqlite3.connect(source) as c:
        c.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY, value TEXT)")
        c.execute("INSERT INTO sample(value) VALUES('ok')")
    root=Path(__file__).resolve().parents[2]
    r=subprocess.run(
        [sys.executable,str(root/"scripts"/"backup_sqlite.py"),
         "--source",str(source),"--output-dir",str(output)],
        cwd=root,capture_output=True,text=True
    )
    assert r.returncode==0, r.stderr
    backups=list(output.glob("kynka-*.db"))
    assert len(backups)==1
    with sqlite3.connect(backups[0]) as c:
        assert c.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
        assert c.execute("SELECT value FROM sample").fetchone()[0]=="ok"
