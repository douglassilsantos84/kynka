from __future__ import annotations
import sqlite3
from datetime import datetime, timezone

VERSION="0035_multimodal_spatial_foundation"
SQL=r"""
CREATE TABLE IF NOT EXISTS multimodal_sessions(
 id TEXT PRIMARY KEY,organization_id INTEGER NOT NULL,user_id INTEGER NOT NULL,
 device_id TEXT,locale TEXT NOT NULL DEFAULT 'pt-PT',status TEXT NOT NULL,
 created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS multimodal_events(
 id INTEGER PRIMARY KEY AUTOINCREMENT,organization_id INTEGER NOT NULL,user_id INTEGER NOT NULL,
 session_id TEXT NOT NULL,event_type TEXT NOT NULL,payload_json TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_multimodal_events_session ON multimodal_events(organization_id,session_id,id);
CREATE TABLE IF NOT EXISTS avatar_states(
 organization_id INTEGER NOT NULL,user_id INTEGER NOT NULL,avatar_id TEXT NOT NULL,
 state TEXT NOT NULL,expression TEXT NOT NULL,speaking_text TEXT,visemes_json TEXT NOT NULL DEFAULT '[]',
 updated_at TEXT NOT NULL,PRIMARY KEY(organization_id,user_id,avatar_id));
CREATE TABLE IF NOT EXISTS spatial_sessions(
 id TEXT PRIMARY KEY,organization_id INTEGER NOT NULL,user_id INTEGER NOT NULL,
 device_id TEXT,client TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS spatial_anchors(
 organization_id INTEGER NOT NULL,session_id TEXT NOT NULL,anchor_id TEXT NOT NULL,label TEXT,
 transform_json TEXT NOT NULL,updated_at TEXT NOT NULL,
 PRIMARY KEY(organization_id,session_id,anchor_id));
CREATE TABLE IF NOT EXISTS spatial_objects(
 organization_id INTEGER NOT NULL,session_id TEXT NOT NULL,object_id TEXT NOT NULL,kind TEXT NOT NULL,
 label TEXT,anchor_id TEXT,transform_json TEXT NOT NULL,resource_json TEXT NOT NULL DEFAULT '{}',
 updated_at TEXT NOT NULL,PRIMARY KEY(organization_id,session_id,object_id));
CREATE TABLE IF NOT EXISTS spatial_interactions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,organization_id INTEGER NOT NULL,user_id INTEGER NOT NULL,
 session_id TEXT NOT NULL,interaction_type TEXT NOT NULL,object_id TEXT,payload_json TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_spatial_interactions_session ON spatial_interactions(organization_id,session_id,id);
"""

def apply_spatial_migration(database_path):
    now=datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(str(database_path)) as c:
        c.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        if c.execute("SELECT 1 FROM schema_migrations WHERE version=?",(VERSION,)).fetchone():
            return False
        c.executescript(SQL)
        c.execute("INSERT INTO schema_migrations(version,applied_at) VALUES(?,?)",(VERSION,now))
    return True
