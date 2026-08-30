from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

class SQLiteEmailQuoteRepository:
    def __init__(self, database_path):
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ensure()

    def connect(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        return c

    def now(self):
        return datetime.now(timezone.utc).isoformat()

    def ensure(self):
        with self.connect() as c:
            c.executescript("""
CREATE TABLE IF NOT EXISTS email_quote_messages(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 provider TEXT NOT NULL DEFAULT 'imap',
 mailbox TEXT NOT NULL,
 message_uid TEXT NOT NULL,
 message_id TEXT,
 sender_email TEXT,
 sender_name TEXT,
 subject TEXT,
 received_at TEXT,
 status TEXT NOT NULL DEFAULT 'detected',
 error TEXT,
 created_at TEXT NOT NULL,
 processed_at TEXT,
 UNIQUE(provider, mailbox, message_uid)
);
CREATE TABLE IF NOT EXISTS email_quote_attachments(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 email_message_id INTEGER NOT NULL,
 file_name TEXT NOT NULL,
 content_type TEXT,
 size_bytes INTEGER NOT NULL DEFAULT 0,
 sha256 TEXT NOT NULL,
 quote_import_id INTEGER,
 status TEXT NOT NULL DEFAULT 'detected',
 error TEXT,
 created_at TEXT NOT NULL,
 FOREIGN KEY(email_message_id) REFERENCES email_quote_messages(id) ON DELETE CASCADE,
 UNIQUE(email_message_id, sha256)
);
""")

    def has_message(self, provider, mailbox, uid):
        with self.connect() as c:
            return c.execute("SELECT 1 FROM email_quote_messages WHERE provider=? AND mailbox=? AND message_uid=?",
                             (provider, mailbox, str(uid))).fetchone() is not None

    def create_message(self, provider, mailbox, uid, message_id, sender_email, sender_name, subject, received_at):
        with self.connect() as c:
            cur = c.execute("""INSERT OR IGNORE INTO email_quote_messages
(provider,mailbox,message_uid,message_id,sender_email,sender_name,subject,received_at,status,created_at)
VALUES(?,?,?,?,?,?,?,?,?,?)""",
(provider, mailbox, str(uid), message_id, sender_email, sender_name, subject, received_at, "detected", self.now()))
            if cur.lastrowid:
                return int(cur.lastrowid)
            row = c.execute("SELECT id FROM email_quote_messages WHERE provider=? AND mailbox=? AND message_uid=?",
                            (provider, mailbox, str(uid))).fetchone()
            return int(row["id"])

    def update_message(self, message_db_id, status, error=None):
        with self.connect() as c:
            c.execute("UPDATE email_quote_messages SET status=?,error=?,processed_at=? WHERE id=?",
                      (status, error, self.now(), int(message_db_id)))

    def create_attachment(self, email_message_id, file_name, content_type, size_bytes, sha256):
        with self.connect() as c:
            cur = c.execute("""INSERT OR IGNORE INTO email_quote_attachments
(email_message_id,file_name,content_type,size_bytes,sha256,status,created_at)
VALUES(?,?,?,?,?,'detected',?)""",
(email_message_id, file_name, content_type, int(size_bytes), sha256, self.now()))
            if cur.lastrowid:
                return int(cur.lastrowid)
            row = c.execute("SELECT id FROM email_quote_attachments WHERE email_message_id=? AND sha256=?",
                            (email_message_id, sha256)).fetchone()
            return int(row["id"])

    def update_attachment(self, attachment_id, status, quote_import_id=None, error=None):
        with self.connect() as c:
            c.execute("""UPDATE email_quote_attachments
SET status=?,quote_import_id=?,error=? WHERE id=?""",
(status, quote_import_id, error, int(attachment_id)))

    def list_messages(self, limit=50):
        with self.connect() as c:
            rows = c.execute("""SELECT * FROM email_quote_messages
ORDER BY id DESC LIMIT ?""", (int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def get_attachments(self, email_message_id):
        with self.connect() as c:
            rows = c.execute("""SELECT * FROM email_quote_attachments
WHERE email_message_id=? ORDER BY id""", (int(email_message_id),)).fetchall()
        return [dict(r) for r in rows]
