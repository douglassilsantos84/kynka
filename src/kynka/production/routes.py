from __future__ import annotations
import json, sqlite3, os
from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from .migrations import MigrationManager
from .events import RealtimeEventStore

class DeviceIn(BaseModel):
    device_id: str=Field(min_length=2,max_length=200)
    platform: str="unknown"
    app_version: str|None=None
    push_token: str|None=None

class SyncIn(BaseModel):
    client_operation_id: str=Field(min_length=4,max_length=200)
    operation_type: str=Field(min_length=2,max_length=100)
    payload: dict={}

def _bearer(v):
    return v.split(" ",1)[1].strip() if v and v.lower().startswith("bearer ") else ""

def build_production_router(database_path, security_service, postgresql_target=None):
    r=APIRouter(prefix="/api/v1/platform",tags=["platform"])
    migrations=MigrationManager(database_path)
    events=RealtimeEventStore(database_path)

    def identity(auth):
        try:return security_service.authenticate(_bearer(auth))
        except ValueError as e:raise HTTPException(401,str(e)) from e

    @r.get("/health")
    def health():
        return {"status":"ok","service":"kynka-api","utc":datetime.now(timezone.utc).isoformat()}

    @r.get("/ready")
    def ready():
        checks={"database":False,"migrations":False}
        try:
            with sqlite3.connect(str(database_path)) as c:c.execute("SELECT 1").fetchone()
            checks["database"]=True
            checks["migrations"]=len(migrations.status())>=1
        except Exception:pass
        ok=all(checks.values())
        if not ok:raise HTTPException(503,detail={"status":"not_ready","checks":checks})
        return {"status":"ready","checks":checks}

    @r.get("/info")
    def info(authorization: str|None=Header(default=None)):
        i=identity(authorization)
        db_url=os.getenv("KYNKA_DATABASE_URL","sqlite:///data/kynka.db")
        return {"api":"v1","organization_id":i["organization_id"],"role":i["role"],
                "database_backend":"postgresql" if db_url.startswith("postgres") else "sqlite",
                "postgresql_target_configured":bool(postgresql_target and postgresql_target.configured),
                "realtime":"sse","mobile_sync":"idempotent-envelope"}

    @r.get("/database-target")
    def database_target(authorization: str|None=Header(default=None)):
        i=identity(authorization)
        if i["role"]!="admin":raise HTTPException(403,"Permissao insuficiente.")
        if postgresql_target is None:
            return {"configured":False,"available":False,"backend":"postgresql"}
        return postgresql_target.probe()

    @r.get("/migrations")
    def migration_status(authorization: str|None=Header(default=None)):
        i=identity(authorization)
        if i["role"]!="admin":raise HTTPException(403,"Permissao insuficiente.")
        return migrations.status()

    @r.post("/devices",status_code=201)
    def device(p:DeviceIn,authorization: str|None=Header(default=None)):
        i=identity(authorization);now=datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(str(database_path)) as c:
            c.execute("""INSERT INTO mobile_devices
                (organization_id,user_id,device_id,platform,app_version,push_token,last_seen_at,created_at)
                VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(organization_id,user_id,device_id) DO UPDATE SET
                platform=excluded.platform,app_version=excluded.app_version,
                push_token=excluded.push_token,last_seen_at=excluded.last_seen_at""",
                (i["organization_id"],i["id"],p.device_id,p.platform,p.app_version,p.push_token,now,now))
        events.publish(i["organization_id"],"mobile.device.registered","user",str(i["id"]),
                       {"device_id":p.device_id,"platform":p.platform})
        return {"registered":True,"device_id":p.device_id}

    @r.post("/sync",status_code=202)
    def sync(p:SyncIn,authorization: str|None=Header(default=None)):
        i=identity(authorization);now=datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(str(database_path)) as c:
            c.row_factory=sqlite3.Row
            existing=c.execute("""SELECT * FROM mobile_sync_operations
                WHERE organization_id=? AND user_id=? AND client_operation_id=?""",
                (i["organization_id"],i["id"],p.client_operation_id)).fetchone()
            if existing:
                d=dict(existing);d["duplicate"]=True;return d
            c.execute("""INSERT INTO mobile_sync_operations
                (organization_id,user_id,client_operation_id,operation_type,payload_json,status,created_at,updated_at)
                VALUES(?,?,?,?,?,'accepted',?,?)""",
                (i["organization_id"],i["id"],p.client_operation_id,p.operation_type,
                 json.dumps(p.payload,ensure_ascii=False),now,now))
        eid=events.publish(i["organization_id"],"mobile.sync.accepted","operation",p.client_operation_id,
                           {"operation_type":p.operation_type})
        return {"accepted":True,"duplicate":False,"client_operation_id":p.client_operation_id,"event_id":eid}

    @r.get("/events")
    def event_list(after:int=0,limit:int=100,authorization: str|None=Header(default=None)):
        i=identity(authorization)
        return events.since(i["organization_id"],after,min(max(limit,1),500))

    @r.get("/events/stream")
    def event_stream(after:int=Query(default=0,ge=0),access_token:str|None=None,
                     authorization: str|None=Header(default=None)):
        raw=_bearer(authorization) or (access_token or "")
        try:i=security_service.authenticate(raw)
        except ValueError as e:raise HTTPException(401,str(e)) from e
        return StreamingResponse(events.stream(i["organization_id"],after),
            media_type="text/event-stream",headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

    return r
