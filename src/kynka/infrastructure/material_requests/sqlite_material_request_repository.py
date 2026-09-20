from __future__ import annotations

from pathlib import Path
import sqlite3
from contextlib import closing
from datetime import datetime, timezone


ACTIVE_COMMITMENT_STATUSES = ("separating", "shortage", "ready")


class SQLiteMaterialRequestRepository:
    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _db(self):
        c = sqlite3.connect(self.database_path, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=30000")
        return closing(c)

    def now(self):
        return datetime.now(timezone.utc).isoformat()

    def _init(self):
        with self._db() as d:
            d.executescript("""
CREATE TABLE IF NOT EXISTS material_requests(
 id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT UNIQUE,demand_id INTEGER NOT NULL,
 requester_name TEXT NOT NULL,priority TEXT NOT NULL DEFAULT 'normal',notes TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT 'requested',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
 approved_at TEXT,ready_at TEXT,delivered_at TEXT,cancelled_at TEXT);
CREATE TABLE IF NOT EXISTS material_request_items(
 id INTEGER PRIMARY KEY AUTOINCREMENT,request_id INTEGER NOT NULL,material_code TEXT NOT NULL,
 material_name TEXT NOT NULL,unit TEXT NOT NULL,quantity_requested REAL NOT NULL,
 quantity_available REAL NOT NULL DEFAULT 0,quantity_separated REAL NOT NULL DEFAULT 0,
 shortage_quantity REAL NOT NULL DEFAULT 0,
 FOREIGN KEY(request_id) REFERENCES material_requests(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS material_request_events(
 id INTEGER PRIMARY KEY AUTOINCREMENT,request_id INTEGER NOT NULL,event_type TEXT NOT NULL,
 from_status TEXT,to_status TEXT,actor TEXT NOT NULL DEFAULT '',notes TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL,
 FOREIGN KEY(request_id) REFERENCES material_requests(id) ON DELETE CASCADE);
CREATE INDEX IF NOT EXISTS idx_mr_status ON material_requests(status);
CREATE INDEX IF NOT EXISTS idx_mr_demand ON material_requests(demand_id);
CREATE INDEX IF NOT EXISTS idx_mri_material ON material_request_items(material_code);
""")
            d.commit()

    def event(self, d, rid, kind, old, new, actor="", notes=""):
        d.execute(
            """INSERT INTO material_request_events
            (request_id,event_type,from_status,to_status,actor,notes,created_at)
            VALUES(?,?,?,?,?,?,?)""",
            (rid, kind, old, new, actor, notes, self.now()),
        )

    def create(self, demand_id, requester, priority, notes, items):
        now = self.now()
        with self._db() as d:
            cur = d.execute(
                """INSERT INTO material_requests
                (demand_id,requester_name,priority,notes,status,created_at,updated_at)
                VALUES(?,?,?,?, 'requested',?,?)""",
                (demand_id, requester, priority, notes, now, now),
            )
            rid = cur.lastrowid
            code = f"REQ-{rid:06d}"
            d.execute("UPDATE material_requests SET code=? WHERE id=?", (code, rid))
            for x in items:
                d.execute(
                    """INSERT INTO material_request_items
                    (request_id,material_code,material_name,unit,quantity_requested,
                     quantity_available,shortage_quantity)
                    VALUES(?,?,?,?,?,?,?)""",
                    (
                        rid, x["material_code"], x["material_name"], x["unit"],
                        x["quantity_requested"], x["quantity_available"], x["shortage_quantity"],
                    ),
                )
            self.event(d, rid, "created", None, "requested", requester, notes)
            d.commit()
            return rid

    def get(self, rid):
        with self._db() as d:
            r = d.execute("SELECT * FROM material_requests WHERE id=?", (rid,)).fetchone()
            return dict(r) if r else None

    def list(self, status=None, demand_id=None):
        q = "SELECT * FROM material_requests WHERE 1=1"
        a = []
        if status:
            q += " AND status=?"; a.append(status)
        if demand_id is not None:
            q += " AND demand_id=?"; a.append(demand_id)
        q += " ORDER BY id DESC"
        with self._db() as d:
            return [dict(r) for r in d.execute(q, a)]

    def items(self, rid):
        with self._db() as d:
            return [dict(r) for r in d.execute(
                "SELECT * FROM material_request_items WHERE request_id=? ORDER BY id", (rid,)
            )]

    def events(self, rid):
        with self._db() as d:
            return [dict(r) for r in d.execute(
                "SELECT * FROM material_request_events WHERE request_id=? ORDER BY id DESC", (rid,)
            )]

    def transition(self, rid, status, actor="", notes=""):
        old = self.get(rid)
        now = self.now()
        col = {"approved":"approved_at","ready":"ready_at","delivered":"delivered_at","cancelled":"cancelled_at"}.get(status)
        with self._db() as d:
            if col:
                d.execute(f"UPDATE material_requests SET status=?,updated_at=?,{col}=? WHERE id=?",
                          (status, now, now, rid))
            else:
                d.execute("UPDATE material_requests SET status=?,updated_at=? WHERE id=?",
                          (status, now, rid))
            self.event(d, rid, "status_changed", old["status"], status, actor, notes)
            d.commit()

    def separation(self, rid, values):
        with self._db() as d:
            for code, qty in values.items():
                d.execute(
                    """UPDATE material_request_items SET quantity_separated=?
                    WHERE request_id=? AND material_code=?""",
                    (qty, rid, code),
                )
            d.commit()

    def total_active_separated(self, material_code, exclude_request_id=None):
        q = """
        SELECT COALESCE(SUM(i.quantity_separated),0) total
        FROM material_request_items i
        JOIN material_requests r ON r.id=i.request_id
        WHERE i.material_code=? AND r.status IN ('separating','shortage','ready')
        """
        args = [material_code]
        if exclude_request_id is not None:
            q += " AND r.id<>?"
            args.append(int(exclude_request_id))
        with self._db() as d:
            row = d.execute(q, args).fetchone()
        return float(row["total"])

    def separate_atomically(self, rid, actor="", notes=""):
        """Serialize separation with BEGIN IMMEDIATE and count active commitments."""
        with self._db() as d:
            try:
                d.execute("BEGIN IMMEDIATE")
                request = d.execute(
                    "SELECT * FROM material_requests WHERE id=?", (rid,)
                ).fetchone()
                if not request:
                    raise ValueError("Solicitacao nao encontrada.")
                if request["status"] not in ("approved", "shortage", "separating"):
                    raise ValueError("A solicitacao precisa estar aprovada para separacao.")

                items = d.execute(
                    "SELECT * FROM material_request_items WHERE request_id=? ORDER BY id", (rid,)
                ).fetchall()
                shortage = False

                for item in items:
                    material = d.execute(
                        """SELECT code,quantity,minimum_quantity FROM materials WHERE code=?""",
                        (item["material_code"],),
                    ).fetchone()
                    if not material:
                        raise ValueError(f"Material nao encontrado: {item['material_code']}.")

                    reserved_by_other_demands = d.execute(
                        """SELECT COALESCE(SUM(quantity),0) total
                        FROM stock_reservations
                        WHERE material_code=?
                          AND demand_id<>?""",
                        (
                            item["material_code"],
                            request["demand_id"],
                        ),
                    ).fetchone()

                    committed = d.execute(
                        """SELECT COALESCE(SUM(i.quantity_separated),0) total
                        FROM material_request_items i
                        JOIN material_requests r ON r.id=i.request_id
                        WHERE i.material_code=?
                          AND i.request_id<>?
                          AND r.status IN ('separating','shortage','ready')""",
                        (item["material_code"], rid),
                    ).fetchone()

                    free = max(
                        float(material["quantity"])
                        - float(material["minimum_quantity"])
                        - float(reserved_by_other_demands["total"])
                        - float(committed["total"]),
                        0.0,
                    )
                    requested = float(item["quantity_requested"])
                    separated = min(requested, free)
                    shortage_qty = max(requested - separated, 0.0)
                    shortage = shortage or shortage_qty > 0

                    d.execute(
                        """UPDATE material_request_items
                        SET quantity_available=?,quantity_separated=?,shortage_quantity=?
                        WHERE id=?""",
                        (separated, separated, shortage_qty, item["id"]),
                    )

                old_status = request["status"]
                if old_status == "approved":
                    self.event(d, rid, "status_changed", "approved", "separating", actor, notes)
                    old_status = "separating"

                target = "shortage" if shortage else "ready"
                now = self.now()
                if target == "ready":
                    d.execute(
                        "UPDATE material_requests SET status=?,updated_at=?,ready_at=? WHERE id=?",
                        (target, now, now, rid),
                    )
                else:
                    d.execute(
                        "UPDATE material_requests SET status=?,updated_at=? WHERE id=?",
                        (target, now, rid),
                    )
                self.event(d, rid, "status_changed", old_status, target, actor, notes)
                d.commit()
                return target
            except Exception:
                d.rollback()
                raise

    def deliver_atomically(self, rid, actor="", notes=""):
        """One transaction: validate all items, move all stock, mark delivered, audit."""
        with self._db() as d:
            try:
                d.execute("BEGIN IMMEDIATE")
                request = d.execute(
                    "SELECT * FROM material_requests WHERE id=?", (rid,)
                ).fetchone()
                if not request:
                    raise ValueError("Solicitacao nao encontrada.")
                if request["status"] != "ready":
                    raise ValueError("Somente uma solicitacao pronta pode ser entregue.")

                items = d.execute(
                    "SELECT * FROM material_request_items WHERE request_id=? ORDER BY id", (rid,)
                ).fetchall()
                prepared = []
                for item in items:
                    qty = float(item["quantity_separated"])
                    if qty <= 0:
                        raise ValueError(
                            f"Item sem quantidade separada: {item['material_code']}."
                        )
                    material = d.execute(
                        "SELECT * FROM materials WHERE code=?", (item["material_code"],)
                    ).fetchone()
                    if not material:
                        raise ValueError(f"Material nao encontrado: {item['material_code']}.")
                    previous = float(material["quantity"])
                    if qty > previous:
                        raise ValueError(
                            f"Estoque insuficiente para {item['material_code']}. "
                            f"Saldo atual: {previous:g} {material['unit']}."
                        )
                    prepared.append((item, material, qty, previous, previous - qty))

                reason = f"Entrega {request['code']} - demanda {request['demand_id']}"
                for item, material, qty, previous, new_qty in prepared:
                    d.execute(
                        "UPDATE materials SET quantity=? WHERE code=?",
                        (new_qty, item["material_code"]),
                    )
                    d.execute(
                        """INSERT INTO inventory_movements
                        (material_code,movement_type,quantity,previous_quantity,new_quantity,reason,created_at)
                        VALUES(?,?,?,?,?,?,?)""",
                        (
                            item["material_code"], "exit", qty, previous, new_qty,
                            reason, self.now(),
                        ),
                    )

                now = self.now()
                d.execute(
                    """UPDATE material_requests
                    SET status='delivered',updated_at=?,delivered_at=? WHERE id=?""",
                    (now, now, rid),
                )
                self.event(d, rid, "status_changed", "ready", "delivered", actor, notes)
                d.commit()
            except Exception:
                d.rollback()
                raise

    def summary(self):
        with self._db() as d:
            rows = d.execute(
                "SELECT status,COUNT(*) n FROM material_requests GROUP BY status"
            ).fetchall()
        x = {r["status"]: r["n"] for r in rows}
        return {"total":sum(x.values()), **{
            k:x.get(k,0) for k in
            ["requested","approved","separating","shortage","ready","delivered","cancelled"]
        }}
