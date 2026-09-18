from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MIGRATIONS = [
    ("0031_production_foundation", """
CREATE TABLE IF NOT EXISTS schema_migrations(
 version TEXT PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS mobile_devices(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 organization_id INTEGER NOT NULL,user_id INTEGER NOT NULL,
 device_id TEXT NOT NULL,platform TEXT NOT NULL DEFAULT 'unknown',
 app_version TEXT,push_token TEXT,last_seen_at TEXT NOT NULL,
 created_at TEXT NOT NULL, UNIQUE(organization_id,user_id,device_id));
CREATE TABLE IF NOT EXISTS realtime_events(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 organization_id INTEGER NOT NULL,event_type TEXT NOT NULL,
 entity_type TEXT,entity_id TEXT,payload_json TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_realtime_events_org
 ON realtime_events(organization_id,id DESC);
CREATE TABLE IF NOT EXISTS mobile_sync_operations(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 organization_id INTEGER NOT NULL,user_id INTEGER NOT NULL,
 client_operation_id TEXT NOT NULL,operation_type TEXT NOT NULL,
 payload_json TEXT NOT NULL DEFAULT '{}',status TEXT NOT NULL DEFAULT 'accepted',
 result_json TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
 UNIQUE(organization_id,user_id,client_operation_id));
"""),
]

class MigrationManager:
    def __init__(self, database_path):
        self.database_path = str(Path(database_path))

    def apply(self):
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.database_path) as c:
            c.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
            applied = {r[0] for r in c.execute("SELECT version FROM schema_migrations")}
            done=[]
            for version, sql in MIGRATIONS:
                if version in applied: continue
                c.executescript(sql)
                c.execute("INSERT INTO schema_migrations(version,applied_at) VALUES(?,?)",(version,now))
                done.append(version)
        return done

    def status(self):
        with sqlite3.connect(self.database_path) as c:
            c.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
            return [{"version":r[0],"applied_at":r[1]} for r in c.execute(
                "SELECT version,applied_at FROM schema_migrations ORDER BY applied_at,version")]
