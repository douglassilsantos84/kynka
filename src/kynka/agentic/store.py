from __future__ import annotations
import json, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

class AgenticStore:
    def __init__(self, database_path):
        self.database_path = str(Path(database_path))
        self.initialize()

    def connect(self):
        c = sqlite3.connect(self.database_path)
        c.row_factory = sqlite3.Row
        return c

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    def initialize(self):
        with self.connect() as c:
            c.executescript("""
CREATE TABLE IF NOT EXISTS agent_memories(
 id INTEGER PRIMARY KEY AUTOINCREMENT, organization_id INTEGER NOT NULL,
 user_id INTEGER, scope TEXT NOT NULL DEFAULT 'user', kind TEXT NOT NULL DEFAULT 'fact',
 content TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}',
 importance REAL NOT NULL DEFAULT 0.5, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_agent_memories_scope ON agent_memories(organization_id,user_id,id DESC);
CREATE TABLE IF NOT EXISTS agent_runs(
 id TEXT PRIMARY KEY, organization_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
 agent_name TEXT NOT NULL, objective TEXT NOT NULL, status TEXT NOT NULL,
 result_json TEXT, error TEXT, created_at TEXT NOT NULL, finished_at TEXT);
CREATE TABLE IF NOT EXISTS agent_workflows(
 id TEXT PRIMARY KEY, organization_id INTEGER NOT NULL, created_by INTEGER NOT NULL,
 title TEXT NOT NULL, objective TEXT NOT NULL, status TEXT NOT NULL,
 requires_approval INTEGER NOT NULL DEFAULT 0, approved_by INTEGER,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agent_workflow_steps(
 id INTEGER PRIMARY KEY AUTOINCREMENT, workflow_id TEXT NOT NULL, position INTEGER NOT NULL,
 agent_name TEXT NOT NULL, tool_name TEXT NOT NULL, arguments_json TEXT NOT NULL DEFAULT '{}',
 status TEXT NOT NULL DEFAULT 'pending', requires_approval INTEGER NOT NULL DEFAULT 0,
 result_json TEXT, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(workflow_id,position));
CREATE INDEX IF NOT EXISTS idx_agent_workflows_org ON agent_workflows(organization_id,created_at DESC);
""")

    def add_memory(self, org, user, content, kind="fact", scope="user", importance=.5, metadata=None):
        now = self.now()
        with self.connect() as c:
            return c.execute(
                """INSERT INTO agent_memories
                (organization_id,user_id,scope,kind,content,metadata_json,importance,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (org, user if scope == "user" else None, scope, kind, content.strip(),
                 json.dumps(metadata or {}, ensure_ascii=False), float(importance), now, now)
            ).lastrowid

    def memories(self, org, user, limit=100):
        with self.connect() as c:
            rows = c.execute(
                """SELECT * FROM agent_memories
                WHERE organization_id=? AND (scope='organization' OR user_id=?)
                ORDER BY importance DESC,id DESC LIMIT ?""",
                (org, user, int(limit))
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["metadata"] = json.loads(d.pop("metadata_json") or "{}")
            result.append(d)
        return result

    def delete_memory(self, mid, org, user, admin=False):
        with self.connect() as c:
            if admin:
                cur = c.execute("DELETE FROM agent_memories WHERE id=? AND organization_id=?", (mid, org))
            else:
                cur = c.execute("DELETE FROM agent_memories WHERE id=? AND organization_id=? AND user_id=?", (mid, org, user))
            return cur.rowcount > 0

    def create_run(self, org, user, agent, objective):
        rid = str(uuid4())
        with self.connect() as c:
            c.execute("""INSERT INTO agent_runs
                (id,organization_id,user_id,agent_name,objective,status,created_at)
                VALUES(?,?,?,?,?,'running',?)""", (rid, org, user, agent, objective, self.now()))
        return rid

    def finish_run(self, rid, status, result=None, error=None):
        with self.connect() as c:
            c.execute("""UPDATE agent_runs SET status=?,result_json=?,error=?,finished_at=? WHERE id=?""",
                      (status, json.dumps(result, ensure_ascii=False, default=str) if result is not None else None,
                       error, self.now(), rid))

    def create_workflow(self, org, user, title, objective, steps):
        wid, now = str(uuid4()), self.now()
        approval = any(bool(s.get("requires_approval")) for s in steps)
        status = "awaiting_approval" if approval else "ready"
        with self.connect() as c:
            c.execute("""INSERT INTO agent_workflows
                (id,organization_id,created_by,title,objective,status,requires_approval,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (wid, org, user, title, objective, status, int(approval), now, now))
            for pos, s in enumerate(steps, 1):
                c.execute("""INSERT INTO agent_workflow_steps
                    (workflow_id,position,agent_name,tool_name,arguments_json,status,requires_approval,created_at,updated_at)
                    VALUES(?,?,?,?,?,'pending',?,?,?)""",
                    (wid, pos, s["agent_name"], s["tool_name"],
                     json.dumps(s.get("arguments") or {}, ensure_ascii=False),
                     int(bool(s.get("requires_approval"))), now, now))
        return self.workflow(wid, org)

    def workflow(self, wid, org):
        with self.connect() as c:
            w = c.execute("SELECT * FROM agent_workflows WHERE id=? AND organization_id=?", (wid, org)).fetchone()
            if not w:
                return None
            rows = c.execute("SELECT * FROM agent_workflow_steps WHERE workflow_id=? ORDER BY position", (wid,)).fetchall()
        d = dict(w)
        d["requires_approval"] = bool(d["requires_approval"])
        d["steps"] = []
        for r in rows:
            x = dict(r)
            x["arguments"] = json.loads(x.pop("arguments_json") or "{}")
            x["requires_approval"] = bool(x["requires_approval"])
            raw = x.pop("result_json")
            x["result"] = json.loads(raw) if raw else None
            d["steps"].append(x)
        return d

    def workflows(self, org, limit=100):
        with self.connect() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM agent_workflows WHERE organization_id=? ORDER BY created_at DESC LIMIT ?",
                (org, int(limit))).fetchall()]

    def approve(self, wid, org, user):
        with self.connect() as c:
            return c.execute("""UPDATE agent_workflows
                SET status='ready',approved_by=?,updated_at=?
                WHERE id=? AND organization_id=? AND status='awaiting_approval'""",
                (user, self.now(), wid, org)).rowcount > 0

    def set_workflow_status(self, wid, org, status):
        with self.connect() as c:
            c.execute("UPDATE agent_workflows SET status=?,updated_at=? WHERE id=? AND organization_id=?",
                      (status, self.now(), wid, org))

    def set_step(self, sid, status, result=None, error=None):
        with self.connect() as c:
            c.execute("""UPDATE agent_workflow_steps
                SET status=?,result_json=?,error=?,updated_at=? WHERE id=?""",
                (status, json.dumps(result, ensure_ascii=False, default=str) if result is not None else None,
                 error, self.now(), sid))
