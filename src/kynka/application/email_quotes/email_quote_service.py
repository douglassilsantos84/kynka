from __future__ import annotations

import hashlib
import imaplib
import os
import re
import time
from email import policy
from email.header import decode_header
from email.parser import BytesParser
from email.utils import parseaddr, parsedate_to_datetime

from kynka.application.quote_imports import QuoteImportService
from kynka.infrastructure.quote_imports import SQLiteQuoteImportRepository


SUPPORTED_EXTENSIONS = {".xlsx", ".csv", ".pdf"}
QUOTE_WORDS = (
    "cotacao", "cotação", "orcamento", "orçamento", "proposta",
    "quote", "quotation", "budget", "price", "preco", "preço",
)

class EmailQuoteError(Exception):
    pass

class EmailQuoteConfig:
    def __init__(self):
        self.enabled = os.getenv("KYNKA_EMAIL_ENABLED", "false").lower() in {"1","true","yes","on"}
        self.host = os.getenv("KYNKA_EMAIL_IMAP_HOST", "").strip()
        self.port = int(os.getenv("KYNKA_EMAIL_IMAP_PORT", "993"))
        self.username = os.getenv("KYNKA_EMAIL_USERNAME", "").strip()
        self.password = os.getenv("KYNKA_EMAIL_PASSWORD", "")
        self.mailbox = os.getenv("KYNKA_EMAIL_MAILBOX", "INBOX").strip() or "INBOX"
        self.use_ssl = os.getenv("KYNKA_EMAIL_IMAP_SSL", "true").lower() in {"1","true","yes","on"}
        self.max_messages = int(os.getenv("KYNKA_EMAIL_MAX_MESSAGES", "50"))
        self.poll_minutes = max(1, int(os.getenv("KYNKA_EMAIL_POLL_MINUTES", "5")))

    @property
    def configured(self):
        return bool(self.host and self.username and self.password)

    def public_dict(self):
        return {
            "enabled": self.enabled,
            "configured": self.configured,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "mailbox": self.mailbox,
            "use_ssl": self.use_ssl,
            "max_messages": self.max_messages,
            "poll_minutes": self.poll_minutes,
        }

class EmailQuoteService:
    def __init__(self, repository, database_path, supplier_service, inventory_service, config=None):
        self.repo = repository
        self.database_path = database_path
        self.suppliers = supplier_service
        self.inventory = inventory_service
        self.config = config or EmailQuoteConfig()
        self.quote_imports = QuoteImportService(
            SQLiteQuoteImportRepository(database_path),
            supplier_service,
            inventory_service,
        )

    def status(self):
        return self.config.public_dict()

    def list_messages(self, limit=50):
        rows = self.repo.list_messages(limit)
        for row in rows:
            row["attachments"] = self.repo.get_attachments(row["id"])
        return rows

    def _decode(self, value):
        if not value:
            return ""
        parts = []
        for chunk, enc in decode_header(value):
            if isinstance(chunk, bytes):
                parts.append(chunk.decode(enc or "utf-8", errors="replace"))
            else:
                parts.append(chunk)
        return "".join(parts)

    def _connect(self):
        if not self.config.configured:
            raise EmailQuoteError("E-mail não configurado. Preencha as variáveis KYNKA_EMAIL_* no .env.")
        if self.config.use_ssl:
            client = imaplib.IMAP4_SSL(self.config.host, self.config.port)
        else:
            client = imaplib.IMAP4(self.config.host, self.config.port)
        client.login(self.config.username, self.config.password)
        status, _ = client.select(self.config.mailbox)
        if status != "OK":
            client.logout()
            raise EmailQuoteError(f"Não foi possível abrir a caixa {self.config.mailbox}.")
        return client

    def _supplier_by_sender(self, sender_email):
        target = (sender_email or "").strip().lower()
        if not target:
            return None
        for supplier in self.suppliers.list_suppliers(active_only=True):
            email = (getattr(supplier, "email", "") or "").strip().lower()
            if email and email == target:
                return supplier
        return None

    def _is_quote_subject(self, subject):
        text = (subject or "").lower()
        return any(word in text for word in QUOTE_WORDS)

    def _attachments(self, message):
        for part in message.walk():
            filename = part.get_filename()
            if not filename:
                continue
            filename = self._decode(filename)
            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            payload = part.get_payload(decode=True) or b""
            if not payload:
                continue
            yield filename, part.get_content_type(), payload

    def scan(self):
        if not self.config.enabled:
            raise EmailQuoteError("Automação de e-mail está desativada. Defina KYNKA_EMAIL_ENABLED=true.")
        client = self._connect()
        summary = {
            "checked": 0,
            "new_messages": 0,
            "imported_attachments": 0,
            "unknown_supplier": 0,
            "ignored": 0,
            "errors": 0,
        }
        try:
            status, data = client.uid("search", None, "ALL")
            if status != "OK":
                raise EmailQuoteError("Falha ao pesquisar mensagens.")
            uids = (data[0] or b"").split()
            for uid_b in uids[-self.config.max_messages:]:
                uid = uid_b.decode()
                summary["checked"] += 1
                if self.repo.has_message("imap", self.config.mailbox, uid):
                    continue

                status, fetched = client.uid("fetch", uid, "(RFC822)")
                if status != "OK" or not fetched or not fetched[0]:
                    summary["errors"] += 1
                    continue
                raw = fetched[0][1]
                msg = BytesParser(policy=policy.default).parsebytes(raw)

                sender_name, sender_email = parseaddr(msg.get("From", ""))
                sender_name = self._decode(sender_name)
                sender_email = sender_email.lower()
                subject = self._decode(msg.get("Subject", ""))
                message_id = msg.get("Message-ID", "")
                received = ""
                try:
                    received = parsedate_to_datetime(msg.get("Date")).isoformat() if msg.get("Date") else ""
                except Exception:
                    received = ""

                db_id = self.repo.create_message(
                    "imap", self.config.mailbox, uid, message_id,
                    sender_email, sender_name, subject, received,
                )
                summary["new_messages"] += 1

                supplier = self._supplier_by_sender(sender_email)
                attachments = list(self._attachments(msg))
                if not attachments:
                    self.repo.update_message(db_id, "ignored_no_supported_attachment")
                    summary["ignored"] += 1
                    continue

                if supplier is None:
                    self.repo.update_message(
                        db_id, "pending_supplier",
                        f"Remetente não corresponde a fornecedor ativo: {sender_email}",
                    )
                    for filename, content_type, payload in attachments:
                        sha = hashlib.sha256(payload).hexdigest()
                        att_id = self.repo.create_attachment(db_id, filename, content_type, len(payload), sha)
                        self.repo.update_attachment(att_id, "pending_supplier")
                    summary["unknown_supplier"] += 1
                    continue

                imported = 0
                for filename, content_type, payload in attachments:
                    sha = hashlib.sha256(payload).hexdigest()
                    att_id = self.repo.create_attachment(db_id, filename, content_type, len(payload), sha)
                    try:
                        quote = self.quote_imports.import_file(filename, payload, supplier.id)
                        self.repo.update_attachment(att_id, "imported_review", quote["id"], None)
                        imported += 1
                        summary["imported_attachments"] += 1
                    except Exception as exc:
                        self.repo.update_attachment(att_id, "error", None, str(exc))
                        summary["errors"] += 1

                if imported:
                    self.repo.update_message(db_id, "imported_review")
                else:
                    self.repo.update_message(db_id, "error", "Nenhum anexo pôde ser importado.")
        finally:
            try:
                client.close()
            except Exception:
                pass
            try:
                client.logout()
            except Exception:
                pass
        return summary

class EmailQuoteMonitor:
    def __init__(self, service):
        self.service = service

    def run_forever(self):
        print("Kynka Email Quote Monitor iniciado.")
        print(f"Intervalo: {self.service.config.poll_minutes} minuto(s)")
        while True:
            try:
                if self.service.config.enabled and self.service.config.configured:
                    result = self.service.scan()
                    print("Scan:", result)
                else:
                    print("E-mail desativado ou não configurado.")
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                print("Erro no monitor:", exc)
            time.sleep(self.service.config.poll_minutes * 60)
