from __future__ import annotations
import json, sqlite3
from datetime import datetime, timezone
from pathlib import Path

class SQLiteQuoteImportRepository:
    def __init__(self, database_path):
        self.path=Path(database_path); self.path.parent.mkdir(parents=True,exist_ok=True); self.ensure()
    def connect(self):
        c=sqlite3.connect(self.path); c.row_factory=sqlite3.Row; return c
    def now(self): return datetime.now(timezone.utc).isoformat()
    def ensure(self):
        with self.connect() as c:
            c.executescript("""
CREATE TABLE IF NOT EXISTS supplier_quote_imports(
 id INTEGER PRIMARY KEY AUTOINCREMENT,supplier_id INTEGER,supplier_code TEXT,supplier_name TEXT,
 file_name TEXT NOT NULL,file_type TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'review',
 total_rows INTEGER NOT NULL DEFAULT 0,matched_rows INTEGER NOT NULL DEFAULT 0,
 unresolved_rows INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,approved_at TEXT);
CREATE TABLE IF NOT EXISTS supplier_quote_import_items(
 id INTEGER PRIMARY KEY AUTOINCREMENT,import_id INTEGER NOT NULL,row_number INTEGER NOT NULL,
 supplier_reference TEXT NOT NULL DEFAULT '',description TEXT NOT NULL DEFAULT '',unit TEXT NOT NULL DEFAULT '',
 quantity REAL,unit_price REAL NOT NULL,matched_material_code TEXT,match_method TEXT NOT NULL DEFAULT '',
 confidence REAL NOT NULL DEFAULT 0,previous_price REAL,status TEXT NOT NULL DEFAULT 'review',
 raw_data TEXT NOT NULL DEFAULT '{}',FOREIGN KEY(import_id) REFERENCES supplier_quote_imports(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS supplier_material_aliases(
 id INTEGER PRIMARY KEY AUTOINCREMENT,supplier_id INTEGER NOT NULL,supplier_reference TEXT NOT NULL,
 material_code TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
 UNIQUE(supplier_id,supplier_reference));""")
    def create(self,supplier,file_name,file_type,items):
        now=self.now(); matched=sum(bool(x.get("matched_material_code")) for x in items)
        with self.connect() as c:
            cur=c.execute("""INSERT INTO supplier_quote_imports
(supplier_id,supplier_code,supplier_name,file_name,file_type,total_rows,matched_rows,unresolved_rows,created_at)
VALUES(?,?,?,?,?,?,?,?,?)""",(supplier.id,supplier.code,supplier.name,file_name,file_type,len(items),matched,len(items)-matched,now))
            iid=cur.lastrowid
            for x in items:
                c.execute("""INSERT INTO supplier_quote_import_items
(import_id,row_number,supplier_reference,description,unit,quantity,unit_price,matched_material_code,match_method,confidence,previous_price,raw_data)
VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",(iid,x["row_number"],x.get("supplier_reference",""),x.get("description",""),x.get("unit",""),
x.get("quantity"),x["unit_price"],x.get("matched_material_code"),x.get("match_method",""),x.get("confidence",0),x.get("previous_price"),
json.dumps(x.get("raw_data",{}),ensure_ascii=False)))
        return int(iid)
    def list(self):
        with self.connect() as c: return [dict(r) for r in c.execute("SELECT * FROM supplier_quote_imports ORDER BY id DESC")]
    def get(self,iid):
        with self.connect() as c:
            r=c.execute("SELECT * FROM supplier_quote_imports WHERE id=?",(iid,)).fetchone()
            return dict(r) if r else None
    def items(self,iid):
        with self.connect() as c: return [dict(r) for r in c.execute("SELECT * FROM supplier_quote_import_items WHERE import_id=? ORDER BY row_number,id",(iid,))]
    def match(self,item_id,code):
        with self.connect() as c: c.execute("UPDATE supplier_quote_import_items SET matched_material_code=?,match_method='manual',confidence=1 WHERE id=?",(code,item_id))
    def approve(self,iid):
        with self.connect() as c:
            c.execute("UPDATE supplier_quote_imports SET status='approved',approved_at=? WHERE id=?",(self.now(),iid))
            c.execute("UPDATE supplier_quote_import_items SET status='approved' WHERE import_id=?",(iid,))
    def alias(self,sid,ref):
        if not ref.strip(): return None
        with self.connect() as c:
            r=c.execute("SELECT material_code FROM supplier_material_aliases WHERE supplier_id=? AND supplier_reference=? COLLATE NOCASE",(sid,ref.strip())).fetchone()
            return r["material_code"] if r else None
    def save_alias(self,sid,ref,code,desc=""):
        if not ref.strip(): return
        now=self.now()
        with self.connect() as c:
            c.execute("""INSERT INTO supplier_material_aliases(supplier_id,supplier_reference,material_code,description,created_at,updated_at)
VALUES(?,?,?,?,?,?) ON CONFLICT(supplier_id,supplier_reference) DO UPDATE SET material_code=excluded.material_code,
description=excluded.description,updated_at=excluded.updated_at""",(sid,ref.strip(),code,desc,now,now))
