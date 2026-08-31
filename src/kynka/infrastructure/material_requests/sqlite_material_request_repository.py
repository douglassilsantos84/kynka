from pathlib import Path
import sqlite3
from datetime import datetime, timezone

class SQLiteMaterialRequestRepository:
    def __init__(self, database_path):
        self.database_path=Path(database_path); self.database_path.parent.mkdir(parents=True,exist_ok=True); self._init()
    def _db(self):
        c=sqlite3.connect(self.database_path); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
    def now(self): return datetime.now(timezone.utc).isoformat()
    def _init(self):
        with self._db() as d:
            d.executescript('''
CREATE TABLE IF NOT EXISTS material_requests(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT UNIQUE,demand_id INTEGER NOT NULL,requester_name TEXT NOT NULL,priority TEXT NOT NULL DEFAULT 'normal',notes TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'requested',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,approved_at TEXT,ready_at TEXT,delivered_at TEXT,cancelled_at TEXT);
CREATE TABLE IF NOT EXISTS material_request_items(id INTEGER PRIMARY KEY AUTOINCREMENT,request_id INTEGER NOT NULL,material_code TEXT NOT NULL,material_name TEXT NOT NULL,unit TEXT NOT NULL,quantity_requested REAL NOT NULL,quantity_available REAL NOT NULL DEFAULT 0,quantity_separated REAL NOT NULL DEFAULT 0,shortage_quantity REAL NOT NULL DEFAULT 0,FOREIGN KEY(request_id) REFERENCES material_requests(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS material_request_events(id INTEGER PRIMARY KEY AUTOINCREMENT,request_id INTEGER NOT NULL,event_type TEXT NOT NULL,from_status TEXT,to_status TEXT,actor TEXT NOT NULL DEFAULT '',notes TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,FOREIGN KEY(request_id) REFERENCES material_requests(id) ON DELETE CASCADE);
CREATE INDEX IF NOT EXISTS idx_mr_status ON material_requests(status); CREATE INDEX IF NOT EXISTS idx_mr_demand ON material_requests(demand_id);
'''); d.commit()
    def event(self,d,rid,kind,old,new,actor='',notes=''):
        d.execute('INSERT INTO material_request_events(request_id,event_type,from_status,to_status,actor,notes,created_at) VALUES(?,?,?,?,?,?,?)',(rid,kind,old,new,actor,notes,self.now()))
    def create(self,demand_id,requester,priority,notes,items):
        now=self.now()
        with self._db() as d:
            cur=d.execute("INSERT INTO material_requests(demand_id,requester_name,priority,notes,status,created_at,updated_at) VALUES(?,?,?,?, 'requested',?,?)",(demand_id,requester,priority,notes,now,now)); rid=cur.lastrowid; code=f'REQ-{rid:06d}'; d.execute('UPDATE material_requests SET code=? WHERE id=?',(code,rid))
            for x in items: d.execute('INSERT INTO material_request_items(request_id,material_code,material_name,unit,quantity_requested,quantity_available,shortage_quantity) VALUES(?,?,?,?,?,?,?)',(rid,x['material_code'],x['material_name'],x['unit'],x['quantity_requested'],x['quantity_available'],x['shortage_quantity']))
            self.event(d,rid,'created',None,'requested',requester,notes); d.commit(); return rid
    def get(self,rid):
        with self._db() as d:
            r=d.execute('SELECT * FROM material_requests WHERE id=?',(rid,)).fetchone(); return dict(r) if r else None
    def list(self,status=None,demand_id=None):
        q='SELECT * FROM material_requests WHERE 1=1'; a=[]
        if status: q+=' AND status=?'; a.append(status)
        if demand_id is not None: q+=' AND demand_id=?'; a.append(demand_id)
        q+=' ORDER BY id DESC'
        with self._db() as d: return [dict(r) for r in d.execute(q,a)]
    def items(self,rid):
        with self._db() as d: return [dict(r) for r in d.execute('SELECT * FROM material_request_items WHERE request_id=? ORDER BY id',(rid,))]
    def events(self,rid):
        with self._db() as d: return [dict(r) for r in d.execute('SELECT * FROM material_request_events WHERE request_id=? ORDER BY id DESC',(rid,))]
    def transition(self,rid,status,actor='',notes=''):
        old=self.get(rid); now=self.now(); col={'approved':'approved_at','ready':'ready_at','delivered':'delivered_at','cancelled':'cancelled_at'}.get(status)
        with self._db() as d:
            if col: d.execute(f'UPDATE material_requests SET status=?,updated_at=?,{col}=? WHERE id=?',(status,now,now,rid))
            else: d.execute('UPDATE material_requests SET status=?,updated_at=? WHERE id=?',(status,now,rid))
            self.event(d,rid,'status_changed',old['status'],status,actor,notes); d.commit()
    def separation(self,rid,values):
        with self._db() as d:
            for code,qty in values.items(): d.execute('UPDATE material_request_items SET quantity_separated=? WHERE request_id=? AND material_code=?',(qty,rid,code))
            d.commit()
    def summary(self):
        with self._db() as d: rows=d.execute('SELECT status,COUNT(*) n FROM material_requests GROUP BY status').fetchall()
        x={r['status']:r['n'] for r in rows}; return {'total':sum(x.values()),**{k:x.get(k,0) for k in ['requested','approved','separating','shortage','ready','delivered','cancelled']}}
