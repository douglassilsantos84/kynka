from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from kynka import __version__
from .config import APISettings
from .schemas import *
from .serializers import json_safe, serialize_execution
from .session_manager import SessionManager

def create_app(settings: APISettings | None = None) -> FastAPI:
    settings = settings or APISettings.from_env()
    manager = SessionManager(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        manager.shutdown()

    api = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)
    api.state.settings = settings
    api.state.sessions = manager
    api.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @api.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
    def health():
        return HealthResponse(status="ok")

    @api.get("/api/v1/status", response_model=StatusResponse, tags=["system"])
    def status():
        return StatusResponse(status="ok", version=__version__, model=settings.model, sessions=manager.count)

    @api.post("/api/v1/sessions", response_model=SessionCreateResponse, tags=["sessions"])
    def create_session():
        s = manager.create()
        return SessionCreateResponse(session_id=s.id)

    @api.delete("/api/v1/sessions/{session_id}", tags=["sessions"])
    def delete_session(session_id: str):
        if not manager.delete(session_id):
            raise HTTPException(404, "Sessão não encontrada.")
        return {"deleted": True}

    @api.post("/api/v1/chat", response_model=ChatResponse, tags=["agent"])
    def chat(request: ChatRequest):
        s = manager.get_or_create(request.session_id)
        try:
            result = s.kynka.run(request.message)
            return ChatResponse(**serialize_execution(s.id, result))
        except Exception as error:
            return ChatResponse(session_id=s.id, success=False, mode="simple", error=str(error))

    @api.get("/api/v1/sessions/{session_id}/memory", response_model=MemoryResponse, tags=["sessions"])
    def memory(session_id: str):
        s = manager.get(session_id)
        if not s:
            raise HTTPException(404, "Sessão não encontrada.")
        records = [
            MemoryRecordResponse(
                text=r.text, success=r.success, capability=r.capability,
                arguments=json_safe(r.arguments), result=json_safe(r.result),
                error=r.error, operational=getattr(r, "operational", True),
            ) for r in s.kynka.memory.records
        ]
        return MemoryResponse(session_id=s.id, records=records)

    @api.delete("/api/v1/sessions/{session_id}/memory", tags=["sessions"])
    def clear_memory(session_id: str):
        s = manager.get(session_id)
        if not s:
            raise HTTPException(404, "Sessão não encontrada.")
        s.kynka.memory.clear()
        return {"cleared": True}

    @api.get("/api/v1/sessions/{session_id}/variables", response_model=VariablesResponse, tags=["sessions"])
    def variables(session_id: str):
        s = manager.get(session_id)
        if not s:
            raise HTTPException(404, "Sessão não encontrada.")
        return VariablesResponse(session_id=s.id, variables=json_safe(s.kynka.context.variables))

    @api.get("/api/v1/capabilities", response_model=list[CapabilityResponse], tags=["agent"])
    def capabilities():
        s = manager.create()
        try:
            return [
                CapabilityResponse(
                    name=name,
                    description=cap.metadata.description,
                    version=getattr(cap.metadata, "version", None),
                )
                for name, cap in s.kynka.runtime.registry.capabilities.items()
            ]
        finally:
            manager.delete(s.id)

    return api

app = create_app()
