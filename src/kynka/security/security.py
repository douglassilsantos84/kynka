from __future__ import annotations

import hashlib
import secrets
import sqlite3
import threading
import time
from collections import defaultdict, deque
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROLES = {"admin", "stock_manager", "buyer", "worker"}


class SecurityStore:
    def __init__(self, database_path):
        self.database_path = str(Path(database_path))
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    def initialize(self):
        with closing(self.connect()) as connection:
            connection.executescript("""
CREATE TABLE IF NOT EXISTS organizations(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    last_login_at TEXT
);
CREATE TABLE IF NOT EXISTS organization_memberships(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(organization_id,user_id)
);
CREATE TABLE IF NOT EXISTS auth_tokens(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    organization_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    revoked_at TEXT
);
CREATE TABLE IF NOT EXISTS platform_events(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER,
    actor_user_id INTEGER,
    event_type TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    payload TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notifications(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    user_id INTEGER,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'info',
    created_at TEXT NOT NULL,
    read_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_hash ON auth_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_events_org ON platform_events(organization_id,id DESC);
CREATE INDEX IF NOT EXISTS idx_memberships_user_org
    ON organization_memberships(user_id,organization_id);
""")
            connection.commit()

    def count_users(self):
        with closing(self.connect()) as c:
            return c.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def bootstrap_identity(self, organization, name, email, password_hash):
        """Create organization, first user and membership atomically."""
        with closing(self.connect()) as c:
            try:
                c.execute("BEGIN IMMEDIATE")
                if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] != 0:
                    raise ValueError("Bootstrap inicial ja concluido.")
                org = c.execute(
                    "INSERT INTO organizations(name,created_at) VALUES(?,?)",
                    (organization, self.now()),
                ).lastrowid
                user = c.execute(
                    "INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",
                    (name, email, password_hash, self.now()),
                ).lastrowid
                c.execute(
                    "INSERT INTO organization_memberships(organization_id,user_id,role,created_at) VALUES(?,?,?,?)",
                    (org, user, "admin", self.now()),
                )
                c.commit()
                return org, user
            except Exception:
                c.rollback()
                raise

    def create_user_with_membership(self, org, name, email, password_hash, role):
        """Create user and tenant membership atomically."""
        with closing(self.connect()) as c:
            try:
                c.execute("BEGIN IMMEDIATE")
                existing = c.execute(
                    "SELECT id FROM users WHERE email=? COLLATE NOCASE", (email,)
                ).fetchone()
                if existing:
                    raise ValueError("Email ja cadastrado.")
                user = c.execute(
                    "INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",
                    (name, email, password_hash, self.now()),
                ).lastrowid
                c.execute(
                    "INSERT INTO organization_memberships(organization_id,user_id,role,created_at) VALUES(?,?,?,?)",
                    (org, user, role, self.now()),
                )
                c.commit()
                return user
            except Exception:
                c.rollback()
                raise

    def user_by_email(self, email):
        with closing(self.connect()) as c:
            row = c.execute(
                "SELECT * FROM users WHERE email=? COLLATE NOCASE", (email,)
            ).fetchone()
            return dict(row) if row else None

    def user(self, user_id):
        with closing(self.connect()) as c:
            row = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            return dict(row) if row else None

    def membership(self, user_id, org=None):
        with closing(self.connect()) as c:
            sql = """SELECT m.organization_id,o.name organization_name,m.role
                     FROM organization_memberships m
                     JOIN organizations o ON o.id=m.organization_id
                     WHERE m.user_id=? AND o.active=1"""
            args = [user_id]
            if org is not None:
                sql += " AND m.organization_id=?"
                args.append(org)
            row = c.execute(sql + " ORDER BY m.id LIMIT 1", args).fetchone()
            return dict(row) if row else None

    def users(self, org):
        with closing(self.connect()) as c:
            return [dict(r) for r in c.execute(
                """SELECT u.id,u.name,u.email,u.active,u.last_login_at,m.role
                   FROM users u JOIN organization_memberships m ON m.user_id=u.id
                   WHERE m.organization_id=? ORDER BY u.name""",
                (org,),
            ).fetchall()]

    def save_token(self, token_hash, user, org, expires):
        with closing(self.connect()) as c:
            c.execute(
                """INSERT INTO auth_tokens(
                       token_hash,user_id,organization_id,expires_at,created_at
                   ) VALUES(?,?,?,?,?)""",
                (token_hash, user, org, expires, self.now()),
            )
            c.commit()

    def token(self, token_hash):
        with closing(self.connect()) as c:
            row = c.execute(
                "SELECT * FROM auth_tokens WHERE token_hash=?", (token_hash,)
            ).fetchone()
            return dict(row) if row else None

    def revoke(self, token_hash):
        with closing(self.connect()) as c:
            c.execute(
                "UPDATE auth_tokens SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL",
                (self.now(), token_hash),
            )
            c.commit()

    def revoke_user_tokens(self, user, org):
        with closing(self.connect()) as c:
            c.execute(
                """UPDATE auth_tokens SET revoked_at=?
                   WHERE user_id=? AND organization_id=? AND revoked_at IS NULL""",
                (self.now(), user, org),
            )
            c.commit()

    def touch_login(self, user):
        with closing(self.connect()) as c:
            c.execute(
                "UPDATE users SET last_login_at=? WHERE id=?", (self.now(), user)
            )
            c.commit()

    def set_user(self, user, org, active=None, role=None):
        with closing(self.connect()) as c:
            try:
                c.execute("BEGIN IMMEDIATE")
                membership = c.execute(
                    """SELECT 1 FROM organization_memberships
                       WHERE user_id=? AND organization_id=?""",
                    (user, org),
                ).fetchone()
                if not membership:
                    raise ValueError("Usuario nao pertence a esta organizacao.")
                if active is not None:
                    c.execute(
                        "UPDATE users SET active=? WHERE id=?",
                        (1 if active else 0, user),
                    )
                if role is not None:
                    c.execute(
                        """UPDATE organization_memberships SET role=?
                           WHERE user_id=? AND organization_id=?""",
                        (role, user, org),
                    )
                c.commit()
            except Exception:
                c.rollback()
                raise
        if active is False or role is not None:
            self.revoke_user_tokens(user, org)

    def event(self, org, actor, event_type, entity_type, entity_id, payload):
        with closing(self.connect()) as c:
            c.execute(
                """INSERT INTO platform_events(
                       organization_id,actor_user_id,event_type,entity_type,
                       entity_id,payload,created_at
                   ) VALUES(?,?,?,?,?,?,?)""",
                (org, actor, event_type, entity_type, entity_id, payload, self.now()),
            )
            c.commit()

    def events(self, org, limit=100):
        with closing(self.connect()) as c:
            return [dict(r) for r in c.execute(
                """SELECT * FROM platform_events
                   WHERE organization_id=? ORDER BY id DESC LIMIT ?""",
                (org, int(limit)),
            ).fetchall()]

    def notifications(self, org, user, limit=100):
        with closing(self.connect()) as c:
            return [dict(r) for r in c.execute(
                """SELECT * FROM notifications
                   WHERE organization_id=? AND (user_id IS NULL OR user_id=?)
                   ORDER BY id DESC LIMIT ?""",
                (org, user, int(limit)),
            ).fetchall()]


class LoginRateLimiter:
    """In-process login throttling. Production multi-instance deployments
    should replace this with a shared Redis-backed limiter."""

    def __init__(self, max_attempts=8, window_seconds=300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts = defaultdict(deque)
        self._lock = threading.Lock()

    def _key(self, email, client_key):
        return f"{email.strip().lower()}|{client_key or 'unknown'}"

    def check(self, email, client_key):
        key = self._key(email, client_key)
        now = time.monotonic()
        with self._lock:
            q = self._attempts[key]
            while q and now - q[0] > self.window_seconds:
                q.popleft()
            if len(q) >= self.max_attempts:
                raise PermissionError(
                    "Muitas tentativas de login. Aguarde alguns minutos."
                )

    def failure(self, email, client_key):
        key = self._key(email, client_key)
        with self._lock:
            self._attempts[key].append(time.monotonic())

    def success(self, email, client_key):
        key = self._key(email, client_key)
        with self._lock:
            self._attempts.pop(key, None)


class SecurityService:
    def __init__(self, store, rate_limiter=None):
        self.store = store
        self.rate_limiter = rate_limiter or LoginRateLimiter()

    @staticmethod
    def hash_password(password):
        if len(password) < 12:
            raise ValueError("A senha deve ter pelo menos 12 caracteres.")
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt, 310000
        )
        return f"pbkdf2_sha256$310000${salt.hex()}${digest.hex()}"

    @staticmethod
    def verify_password(password, encoded):
        try:
            _, rounds, salt, expected = encoded.split("$", 3)
            got = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), bytes.fromhex(salt), int(rounds)
            ).hex()
            return secrets.compare_digest(got, expected)
        except Exception:
            return False

    @staticmethod
    def token_hash(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def bootstrap_required(self):
        return self.store.count_users() == 0

    def bootstrap(self, organization, name, email, password):
        organization = organization.strip()
        name = name.strip()
        email = email.strip().lower()
        if not organization or not name or "@" not in email:
            raise ValueError("Dados de bootstrap invalidos.")
        password_hash = self.hash_password(password)
        self.store.bootstrap_identity(
            organization, name, email, password_hash
        )
        self.store.event(None, None, "security.bootstrap", "organization", None, organization)
        return self.login(email, password, "bootstrap")

    def login(self, email, password, client_key=None):
        email = email.strip().lower()
        self.rate_limiter.check(email, client_key)
        user = self.store.user_by_email(email)
        if not user or not user["active"] or not self.verify_password(
            password, user["password_hash"]
        ):
            self.rate_limiter.failure(email, client_key)
            raise ValueError("Email ou senha invalidos.")
        membership = self.store.membership(user["id"])
        if not membership:
            self.rate_limiter.failure(email, client_key)
            raise ValueError("Usuario sem organizacao.")
        self.rate_limiter.success(email, client_key)
        raw = secrets.token_urlsafe(48)
        expires = datetime.now(timezone.utc) + timedelta(hours=12)
        self.store.save_token(
            self.token_hash(raw), user["id"], membership["organization_id"],
            expires.isoformat()
        )
        self.store.touch_login(user["id"])
        self.store.event(
            membership["organization_id"], user["id"],
            "security.login", "user", str(user["id"]), "success"
        )
        return {
            "access_token": raw,
            "token_type": "bearer",
            "expires_at": expires.isoformat(),
            "user": self.identity(user["id"], membership["organization_id"]),
        }

    def authenticate(self, raw):
        if not raw:
            raise ValueError("Token de acesso ausente.")
        token = self.store.token(self.token_hash(raw))
        if not token or token["revoked_at"]:
            raise ValueError("Sessao invalida.")
        if datetime.fromisoformat(token["expires_at"]) <= datetime.now(timezone.utc):
            raise ValueError("Sessao expirada.")
        user = self.store.user(token["user_id"])
        if not user or not user["active"]:
            raise ValueError("Usuario inativo.")
        return self.identity(user["id"], token["organization_id"])

    def identity(self, user_id, org):
        user = self.store.user(user_id)
        membership = self.store.membership(user_id, org)
        if not user or not membership:
            raise ValueError("Identidade invalida.")
        return {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "active": bool(user["active"]),
            "role": membership["role"],
            "organization_id": membership["organization_id"],
            "organization_name": membership["organization_name"],
        }

    def create_user(self, identity, name, email, password, role):
        if identity["role"] != "admin":
            raise PermissionError("Permissao insuficiente.")
        role = role.strip().lower()
        email = email.strip().lower()
        name = name.strip()
        if role not in ROLES:
            raise ValueError("Perfil invalido.")
        if not name or "@" not in email:
            raise ValueError("Dados do usuario invalidos.")
        user = self.store.create_user_with_membership(
            identity["organization_id"],
            name,
            email,
            self.hash_password(password),
            role,
        )
        self.store.event(
            identity["organization_id"], identity["id"],
            "security.user_created", "user", str(user), role
        )
        return self.identity(user, identity["organization_id"])
