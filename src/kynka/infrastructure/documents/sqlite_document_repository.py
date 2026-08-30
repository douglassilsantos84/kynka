from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class DocumentDuplicateError(Exception):
    pass


class DocumentNotFoundError(Exception):
    pass


class SQLiteDocumentRepository:
    def __init__(self, database_path):
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ensure_schema()

    @contextmanager
    def _connect(self):
        """
        Abre uma conexão SQLite por operação e garante fechamento explícito.

        Importante no Windows: o context manager nativo de sqlite3.Connection
        faz commit/rollback, mas não fecha a conexão. Sem close(), arquivos
        temporários podem permanecer bloqueados (WinError 32).
        """
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def ensure_schema(self):
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_name TEXT NOT NULL,
                    stored_name TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    mime_type TEXT,
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    sha256 TEXT NOT NULL UNIQUE,
                    title TEXT,
                    category TEXT NOT NULL DEFAULT 'geral',
                    status TEXT NOT NULL DEFAULT 'indexed',
                    extracted_text TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    indexed_at TEXT,
                    deleted_at TEXT
                );

                CREATE TABLE IF NOT EXISTS document_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding_json TEXT NOT NULL DEFAULT '[]',
                    embedding_provider TEXT NOT NULL DEFAULT 'local-hash',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
                    UNIQUE(document_id, chunk_index)
                );

                CREATE INDEX IF NOT EXISTS idx_documents_category
                    ON documents(category);

                CREATE INDEX IF NOT EXISTS idx_documents_status
                    ON documents(status);

                CREATE INDEX IF NOT EXISTS idx_document_chunks_document
                    ON document_chunks(document_id);
                """
            )

    def create_document(
        self,
        *,
        original_name,
        stored_name,
        file_type,
        mime_type,
        size_bytes,
        sha256,
        title,
        category,
        extracted_text,
        metadata,
    ):
        now = self._now()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM documents WHERE sha256=? AND deleted_at IS NULL",
                (sha256,),
            ).fetchone()
            if existing:
                raise DocumentDuplicateError(
                    f"Este arquivo já existe na biblioteca como documento #{existing['id']}."
                )

            cur = conn.execute(
                """
                INSERT INTO documents (
                    original_name, stored_name, file_type, mime_type,
                    size_bytes, sha256, title, category, status,
                    extracted_text, metadata_json, created_at, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'indexed', ?, ?, ?, ?)
                """,
                (
                    original_name,
                    stored_name,
                    file_type,
                    mime_type,
                    int(size_bytes),
                    sha256,
                    title,
                    category,
                    extracted_text,
                    json.dumps(metadata, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            return int(cur.lastrowid)

    def replace_chunks(self, document_id, chunks):
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM document_chunks WHERE document_id=?",
                (int(document_id),),
            )
            conn.executemany(
                """
                INSERT INTO document_chunks (
                    document_id, chunk_index, content,
                    embedding_json, embedding_provider, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        int(document_id),
                        int(item["chunk_index"]),
                        item["content"],
                        json.dumps(item["embedding"]),
                        item["embedding_provider"],
                        now,
                    )
                    for item in chunks
                ],
            )

    def list_documents(self, category=None, search=None, limit=100):
        where = ["deleted_at IS NULL"]
        args = []

        if category:
            where.append("category=?")
            args.append(category)

        if search:
            where.append(
                "(LOWER(original_name) LIKE ? OR LOWER(title) LIKE ? "
                "OR LOWER(extracted_text) LIKE ?)"
            )
            q = f"%{search.lower()}%"
            args.extend([q, q, q])

        args.append(int(limit))

        sql = f"""
            SELECT id, original_name, file_type, mime_type, size_bytes,
                   sha256, title, category, status, metadata_json,
                   created_at, indexed_at
            FROM documents
            WHERE {' AND '.join(where)}
            ORDER BY id DESC
            LIMIT ?
        """

        with self._connect() as conn:
            rows = conn.execute(sql, args).fetchall()

        return [self._document_dict(row) for row in rows]

    def get_document(self, document_id):
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM documents
                WHERE id=? AND deleted_at IS NULL
                """,
                (int(document_id),),
            ).fetchone()

        if not row:
            raise DocumentNotFoundError(
                f"Documento #{document_id} não encontrado."
            )

        return self._document_dict(row, include_text=True)

    def get_document_by_sha(self, sha256):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE sha256=? AND deleted_at IS NULL",
                (sha256,),
            ).fetchone()

        return self._document_dict(row, include_text=True) if row else None

    def get_chunks(self, document_id):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, document_id, chunk_index, content,
                       embedding_json, embedding_provider
                FROM document_chunks
                WHERE document_id=?
                ORDER BY chunk_index
                """,
                (int(document_id),),
            ).fetchall()

        return [self._chunk_dict(row) for row in rows]

    def all_chunks(self, document_ids=None):
        args = []
        where = ["d.deleted_at IS NULL"]

        if document_ids:
            marks = ",".join("?" for _ in document_ids)
            where.append(f"d.id IN ({marks})")
            args.extend(int(x) for x in document_ids)

        sql = f"""
            SELECT c.id, c.document_id, c.chunk_index, c.content,
                   c.embedding_json, c.embedding_provider,
                   d.original_name, d.title, d.category
            FROM document_chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE {' AND '.join(where)}
            ORDER BY d.id, c.chunk_index
        """

        with self._connect() as conn:
            rows = conn.execute(sql, args).fetchall()

        result = []
        for row in rows:
            item = self._chunk_dict(row)
            item.update(
                {
                    "original_name": row["original_name"],
                    "title": row["title"],
                    "category": row["category"],
                }
            )
            result.append(item)

        return result

    def update_index(
        self,
        document_id,
        *,
        extracted_text,
        category,
        metadata,
    ):
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE documents
                SET extracted_text=?, category=?, metadata_json=?,
                    status='indexed', indexed_at=?
                WHERE id=? AND deleted_at IS NULL
                """,
                (
                    extracted_text,
                    category,
                    json.dumps(metadata, ensure_ascii=False),
                    self._now(),
                    int(document_id),
                ),
            )

            if cur.rowcount == 0:
                raise DocumentNotFoundError(
                    f"Documento #{document_id} não encontrado."
                )

    def delete_document(self, document_id):
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE documents
                SET deleted_at=?, status='deleted'
                WHERE id=? AND deleted_at IS NULL
                """,
                (self._now(), int(document_id)),
            )

            if cur.rowcount == 0:
                raise DocumentNotFoundError(
                    f"Documento #{document_id} não encontrado."
                )

            conn.execute(
                "DELETE FROM document_chunks WHERE document_id=?",
                (int(document_id),),
            )

    def stats(self):
        with self._connect() as conn:
            doc = conn.execute(
                "SELECT COUNT(*) AS n FROM documents WHERE deleted_at IS NULL"
            ).fetchone()["n"]

            chunks = conn.execute(
                """
                SELECT COUNT(*) AS n
                FROM document_chunks c
                JOIN documents d ON d.id=c.document_id
                WHERE d.deleted_at IS NULL
                """
            ).fetchone()["n"]

            cats = conn.execute(
                """
                SELECT category, COUNT(*) AS n
                FROM documents
                WHERE deleted_at IS NULL
                GROUP BY category
                ORDER BY n DESC, category
                """
            ).fetchall()

        return {
            "documents": int(doc),
            "chunks": int(chunks),
            "categories": {
                row["category"]: int(row["n"])
                for row in cats
            },
        }

    @staticmethod
    def _document_dict(row, include_text=False):
        if row is None:
            return None

        keys = row.keys()

        item = {
            "id": int(row["id"]),
            "original_name": row["original_name"],
            "file_type": row["file_type"],
            "mime_type": row["mime_type"],
            "size_bytes": int(row["size_bytes"]),
            "sha256": row["sha256"],
            "title": row["title"],
            "category": row["category"],
            "status": row["status"],
            "metadata": json.loads(row["metadata_json"] or "{}"),
            "created_at": row["created_at"],
            "indexed_at": row["indexed_at"],
        }

        if "stored_name" in keys:
            item["stored_name"] = row["stored_name"]

        if include_text and "extracted_text" in keys:
            item["extracted_text"] = row["extracted_text"]

        return item

    @staticmethod
    def _chunk_dict(row):
        return {
            "id": int(row["id"]),
            "document_id": int(row["document_id"]),
            "chunk_index": int(row["chunk_index"]),
            "content": row["content"],
            "embedding": json.loads(row["embedding_json"] or "[]"),
            "embedding_provider": row["embedding_provider"],
        }
