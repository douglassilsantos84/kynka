from __future__ import annotations
import hashlib, secrets, sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROLES={"admin","stock_manager","buyer","worker"}

class SecurityStore:
    def __init__(self,database_path):
        self.database_path=str(Path(database_path)); self.initialize()
    def connect(self):
        c=sqlite3.connect(self.database_path); c.row_factory=sqlite3.Row; return c
    @staticmethod
    def now(): return datetime.now(timezone.utc).isoformat()
    def initialize(self):
        with self.connect() as c:
            c.executescript("""
CREATE TABLE IF NOT EXISTS organizations(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,email TEXT NOT NULL UNIQUE COLLATE NOCASE,password_hash TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,last_login_at TEXT);
CREATE TABLE IF NOT EXISTS organization_memberships(id INTEGER PRIMARY KEY AUTOINCREMENT,organization_id INTEGER NOT NULL,user_id INTEGER NOT NULL,role TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(organization_id,user_id));
CREATE TABLE IF NOT EXISTS auth_tokens(id INTEGER PRIMARY KEY AUTOINCREMENT,token_hash TEXT NOT NULL UNIQUE,user_id INTEGER NOT NULL,organization_id INTEGER NOT NULL,expires_at TEXT NOT NULL,created_at TEXT NOT NULL,revoked_at TEXT);
CREATE TABLE IF NOT EXISTS platform_events(id INTEGER PRIMARY KEY AUTOINCREMENT,organization_id INTEGER,actor_user_id INTEGER,event_type TEXT NOT NULL,entity_type TEXT,entity_id TEXT,payload TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY AUTOINCREMENT,organization_id INTEGER NOT NULL,user_id INTEGER,title TEXT NOT NULL,message TEXT NOT NULL,kind TEXT NOT NULL DEFAULT 'info',created_at TEXT NOT NULL,read_at TEXT);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_hash ON auth_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_events_org ON platform_events(organization_id,id DESC);
""")
    def count_users(self):
        with self.connect() as c:return c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    def create_organization(self,name):
        with self.connect() as c:return c.execute("INSERT INTO organizations(name,created_at) VALUES(?,?)",(name,self.now())).lastrowid
    def create_user(self,name,email,password_hash):
        with self.connect() as c:return c.execute("INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",(name,email,password_hash,self.now())).lastrowid
    def add_membership(self,org,user,role):
        with self.connect() as c:c.execute("INSERT INTO organization_memberships(organization_id,user_id,role,created_at) VALUES(?,?,?,?)",(org,user,role,self.now()))
    def user_by_email(self,email):
        with self.connect() as c:
            r=c.execute("SELECT * FROM users WHERE email=? COLLATE NOCASE",(email,)).fetchone();return dict(r) if r else None
    def user(self,user_id):
        with self.connect() as c:
            r=c.execute("SELECT * FROM users WHERE id=?",(user_id,)).fetchone();return dict(r) if r else None
    def membership(self,user_id,org=None):
        with self.connect() as c:
            sql="SELECT m.organization_id,o.name organization_name,m.role FROM organization_memberships m JOIN organizations o ON o.id=m.organization_id WHERE m.user_id=? AND o.active=1";args=[user_id]
            if org is not None:sql+=" AND m.organization_id=?";args.append(org)
            r=c.execute(sql+" ORDER BY m.id LIMIT 1",args).fetchone();return dict(r) if r else None
    def users(self,org):
        with self.connect() as c:return [dict(r) for r in c.execute("SELECT u.id,u.name,u.email,u.active,u.last_login_at,m.role FROM users u JOIN organization_memberships m ON m.user_id=u.id WHERE m.organization_id=? ORDER BY u.name",(org,)).fetchall()]
    def save_token(self,h,user,org,expires):
        with self.connect() as c:c.execute("INSERT INTO auth_tokens(token_hash,user_id,organization_id,expires_at,created_at) VALUES(?,?,?,?,?)",(h,user,org,expires,self.now()))
    def token(self,h):
        with self.connect() as c:
            r=c.execute("SELECT * FROM auth_tokens WHERE token_hash=?",(h,)).fetchone();return dict(r) if r else None
    def revoke(self,h):
        with self.connect() as c:c.execute("UPDATE auth_tokens SET revoked_at=? WHERE token_hash=?",(self.now(),h))
    def touch_login(self,user):
        with self.connect() as c:c.execute("UPDATE users SET last_login_at=? WHERE id=?",(self.now(),user))
    def set_user(self,user,org,active=None,role=None):
        with self.connect() as c:
            if active is not None:c.execute("UPDATE users SET active=? WHERE id=?",(1 if active else 0,user))
            if role is not None:
                cur=c.execute("UPDATE organization_memberships SET role=? WHERE user_id=? AND organization_id=?",(role,user,org))
                if cur.rowcount==0:raise ValueError("Usuario nao pertence a esta organizacao.")
    def event(self,org,actor,event_type,entity_type,entity_id,payload):
        with self.connect() as c:c.execute("INSERT INTO platform_events(organization_id,actor_user_id,event_type,entity_type,entity_id,payload,created_at) VALUES(?,?,?,?,?,?,?)",(org,actor,event_type,entity_type,entity_id,payload,self.now()))
    def events(self,org,limit=100):
        with self.connect() as c:return [dict(r) for r in c.execute("SELECT * FROM platform_events WHERE organization_id=? ORDER BY id DESC LIMIT ?",(org,int(limit))).fetchall()]
    def notifications(self,org,user,limit=100):
        with self.connect() as c:return [dict(r) for r in c.execute("SELECT * FROM notifications WHERE organization_id=? AND (user_id IS NULL OR user_id=?) ORDER BY id DESC LIMIT ?",(org,user,int(limit))).fetchall()]

class SecurityService:
    def __init__(self,store):self.store=store
    @staticmethod
    def hash_password(password):
        if len(password)<8:raise ValueError("A senha deve ter pelo menos 8 caracteres.")
        salt=secrets.token_bytes(16);digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,310000)
        return f"pbkdf2_sha256$310000${salt.hex()}${digest.hex()}"
    @staticmethod
    def verify_password(password,encoded):
        try:
            _,rounds,salt,expected=encoded.split("$",3)
            got=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),int(rounds)).hex()
            return secrets.compare_digest(got,expected)
        except Exception:return False
    @staticmethod
    def token_hash(token):return hashlib.sha256(token.encode()).hexdigest()
    def bootstrap_required(self):return self.store.count_users()==0
    def bootstrap(self,organization,name,email,password):
        if not self.bootstrap_required():raise ValueError("Bootstrap inicial ja concluido.")
        organization,name,email=organization.strip(),name.strip(),email.strip().lower()
        if not organization or not name or "@" not in email:raise ValueError("Dados de bootstrap invalidos.")
        org=self.store.create_organization(organization);user=self.store.create_user(name,email,self.hash_password(password));self.store.add_membership(org,user,"admin")
        return self.login(email,password)
    def login(self,email,password):
        user=self.store.user_by_email(email.strip().lower())
        if not user or not user["active"] or not self.verify_password(password,user["password_hash"]):raise ValueError("Email ou senha invalidos.")
        m=self.store.membership(user["id"])
        if not m:raise ValueError("Usuario sem organizacao.")
        raw=secrets.token_urlsafe(48);expires=datetime.now(timezone.utc)+timedelta(hours=12)
        self.store.save_token(self.token_hash(raw),user["id"],m["organization_id"],expires.isoformat());self.store.touch_login(user["id"])
        return {"access_token":raw,"token_type":"bearer","expires_at":expires.isoformat(),"user":self.identity(user["id"],m["organization_id"])}
    def authenticate(self,raw):
        if not raw:raise ValueError("Token de acesso ausente.")
        token=self.store.token(self.token_hash(raw))
        if not token or token["revoked_at"]:raise ValueError("Sessao invalida.")
        if datetime.fromisoformat(token["expires_at"])<=datetime.now(timezone.utc):raise ValueError("Sessao expirada.")
        user=self.store.user(token["user_id"])
        if not user or not user["active"]:raise ValueError("Usuario inativo.")
        return self.identity(user["id"],token["organization_id"])
    def identity(self,user_id,org):
        user=self.store.user(user_id);m=self.store.membership(user_id,org)
        if not user or not m:raise ValueError("Identidade invalida.")
        return {"id":user["id"],"name":user["name"],"email":user["email"],"active":bool(user["active"]),"role":m["role"],"organization_id":m["organization_id"],"organization_name":m["organization_name"]}
    def create_user(self,identity,name,email,password,role):
        if identity["role"]!="admin":raise PermissionError("Permissao insuficiente.")
        role=role.strip().lower();email=email.strip().lower()
        if role not in ROLES:raise ValueError("Perfil invalido.")
        if self.store.user_by_email(email):raise ValueError("Email ja cadastrado.")
        uid=self.store.create_user(name.strip(),email,self.hash_password(password));self.store.add_membership(identity["organization_id"],uid,role)
        return self.identity(uid,identity["organization_id"])
