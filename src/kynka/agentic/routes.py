from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from kynka.application.documents import DocumentService
from kynka.infrastructure.documents import SQLiteDocumentRepository
from .store import AgenticStore
from .service import AgenticService

class RunIn(BaseModel):
    objective: str = Field(min_length=2)
    document_ids: list[int] | None = None

class MemoryIn(BaseModel):
    content: str = Field(min_length=2)
    kind: str = "fact"
    scope: str = "user"
    importance: float = Field(default=.5, ge=0, le=1)
    metadata: dict = {}

class WorkflowIn(BaseModel):
    title: str = Field(min_length=2)
    objective: str = Field(min_length=2)

def bearer(v):
    return v.split(" ",1)[1].strip() if v and v.lower().startswith("bearer ") else ""

def build_agentic_router(db, storage, security, inventory, suppliers):
    router = APIRouter(prefix="/api/v1/agentic", tags=["agentic"])
    store = AgenticStore(db)
    service = AgenticService(store, inventory, suppliers,
                             DocumentService(SQLiteDocumentRepository(db), storage))

    def identity(auth):
        try: return security.authenticate(bearer(auth))
        except ValueError as e: raise HTTPException(401, str(e)) from e

    def call(fn):
        try: return fn()
        except PermissionError as e: raise HTTPException(403, str(e)) from e
        except ValueError as e: raise HTTPException(400, str(e)) from e

    @router.get("/status")
    def status(authorization: str | None = Header(default=None)):
        i = identity(authorization)
        return {"status":"ok","stages":[27,28,29,30],
                "agents":["orchestrator","operations","procurement","knowledge"],
                "identity":{"user_id":i["id"],"role":i["role"],"organization_id":i["organization_id"]}}

    @router.get("/tools")
    def tools(authorization: str | None = Header(default=None)):
        return service.catalog(identity(authorization))

    @router.post("/run")
    def run(p: RunIn, authorization: str | None = Header(default=None)):
        return call(lambda: service.run(identity(authorization), p.objective, p.document_ids))

    @router.get("/memory")
    def memory(q: str="", limit: int=20, authorization: str | None = Header(default=None)):
        return service.recall(identity(authorization), q, min(max(limit,1),100))

    @router.post("/memory", status_code=201)
    def remember(p: MemoryIn, authorization: str | None = Header(default=None)):
        return call(lambda: service.remember(identity(authorization), p.content, p.kind, p.scope, p.importance, p.metadata))

    @router.delete("/memory/{mid}")
    def forget(mid: int, authorization: str | None = Header(default=None)):
        i = identity(authorization)
        if not store.delete_memory(mid, i["organization_id"], i["id"], i["role"]=="admin"):
            raise HTTPException(404, "Memoria nao encontrada.")
        return {"deleted": True}

    @router.get("/workflows")
    def workflows(limit: int=100, authorization: str | None = Header(default=None)):
        i = identity(authorization)
        return store.workflows(i["organization_id"], min(max(limit,1),500))

    @router.post("/workflows", status_code=201)
    def create(p: WorkflowIn, authorization: str | None = Header(default=None)):
        return call(lambda: service.create_workflow(identity(authorization), p.title, p.objective))

    @router.get("/workflows/{wid}")
    def get_workflow(wid: str, authorization: str | None = Header(default=None)):
        i = identity(authorization)
        w = store.workflow(wid, i["organization_id"])
        if not w: raise HTTPException(404, "Workflow nao encontrado.")
        return w

    @router.post("/workflows/{wid}/approve")
    def approve(wid: str, authorization: str | None = Header(default=None)):
        return call(lambda: service.approve(identity(authorization), wid))

    @router.post("/workflows/{wid}/execute")
    def execute(wid: str, authorization: str | None = Header(default=None)):
        return call(lambda: service.execute(identity(authorization), wid))

    return router
