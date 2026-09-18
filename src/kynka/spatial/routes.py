from __future__ import annotations
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from .store import SpatialStore

class MultimodalSessionIn(BaseModel):
    device_id:str|None=None
    locale:str="pt-PT"

class MultimodalEventIn(BaseModel):
    event_type:str=Field(min_length=2,max_length=80)
    payload:dict=Field(default_factory=dict)

class AvatarStateIn(BaseModel):
    state:str=Field(pattern="^(idle|listening|thinking|speaking|error)$")
    expression:str="neutral"
    speaking_text:str|None=None
    visemes:list[dict]=Field(default_factory=list)

class SpatialSessionIn(BaseModel):
    device_id:str|None=None
    client:str="generic-ar"

class Transform(BaseModel):
    position:list[float]=Field(default_factory=lambda:[0.0,0.0,0.0],min_length=3,max_length=3)
    rotation:list[float]=Field(default_factory=lambda:[0.0,0.0,0.0,1.0],min_length=4,max_length=4)
    scale:list[float]=Field(default_factory=lambda:[1.0,1.0,1.0],min_length=3,max_length=3)

class AnchorIn(BaseModel):
    anchor_id:str=Field(min_length=1,max_length=200)
    label:str|None=None
    transform:Transform=Field(default_factory=Transform)

class ObjectIn(BaseModel):
    object_id:str=Field(min_length=1,max_length=200)
    kind:str="generic"
    label:str|None=None
    anchor_id:str|None=None
    transform:Transform=Field(default_factory=Transform)
    resource:dict=Field(default_factory=dict)

class InteractionIn(BaseModel):
    interaction_type:str=Field(pattern="^(gaze|select|voice|gesture|context_query)$")
    object_id:str|None=None
    payload:dict=Field(default_factory=dict)

def _bearer(v):
    return v.split(" ",1)[1].strip() if v and v.lower().startswith("bearer ") else ""

def build_spatial_router(database_path, security_service):
    r=APIRouter(prefix="/api/v1",tags=["multimodal-spatial"])
    store=SpatialStore(database_path)

    def identity(auth):
        try:return security_service.authenticate(_bearer(auth))
        except ValueError as e:raise HTTPException(401,str(e)) from e

    def ensure_mm(i,sid):
        s=store.get_multimodal_session(i["organization_id"],sid)
        if not s:raise HTTPException(404,"Sessao multimodal nao encontrada.")
        if s["user_id"]!=i["id"] and i["role"]!="admin":raise HTTPException(403,"Permissao insuficiente.")
        return s

    def ensure_spatial(i,sid):
        s=store.get_spatial_session(i["organization_id"],sid)
        if not s:raise HTTPException(404,"Sessao espacial nao encontrada.")
        if s["user_id"]!=i["id"] and i["role"]!="admin":raise HTTPException(403,"Permissao insuficiente.")
        return s

    @r.get("/multimodal/status")
    def multimodal_status(authorization:str|None=Header(default=None)):
        identity(authorization)
        return {"status":"ready","protocol":"kynka-multimodal/1.0",
          "input":["text","stt-transcript","device-event"],"output":["text","tts-request","avatar-event"],
          "stt_provider":"adapter-required","tts_provider":"adapter-required","binary_audio_transport":"not-enabled"}

    @r.post("/multimodal/sessions",status_code=201)
    def create_mm(p:MultimodalSessionIn,authorization:str|None=Header(default=None)):
        i=identity(authorization)
        return store.create_multimodal_session(i["organization_id"],i["id"],p.device_id,p.locale)

    @r.post("/multimodal/sessions/{session_id}/events",status_code=201)
    def mm_event(session_id:str,p:MultimodalEventIn,authorization:str|None=Header(default=None)):
        i=identity(authorization);ensure_mm(i,session_id)
        eid=store.add_multimodal_event(i["organization_id"],i["id"],session_id,p.event_type,p.payload)
        return {"accepted":True,"event_id":eid}

    @r.get("/multimodal/sessions/{session_id}/events")
    def mm_events(session_id:str,authorization:str|None=Header(default=None)):
        i=identity(authorization);ensure_mm(i,session_id)
        return store.events(i["organization_id"],session_id)

    @r.put("/multimodal/avatar/{avatar_id}/state")
    def avatar(avatar_id:str,p:AvatarStateIn,authorization:str|None=Header(default=None)):
        i=identity(authorization)
        return store.set_avatar_state(i["organization_id"],i["id"],avatar_id,p.state,p.expression,p.speaking_text,p.visemes)

    @r.get("/multimodal/avatar/{avatar_id}/state")
    def avatar_get(avatar_id:str,authorization:str|None=Header(default=None)):
        i=identity(authorization)
        return store.avatar_state(i["organization_id"],i["id"],avatar_id) or {
          "avatar_id":avatar_id,"state":"idle","expression":"neutral","speaking_text":None,"visemes":[]}

    @r.get("/spatial/status")
    def spatial_status(authorization:str|None=Header(default=None)):
        identity(authorization)
        return {"status":"ready","protocol":"kynka-spatial/1.0",
          "coordinate_system":"right-handed-y-up","units":"meters",
          "clients":["Unity","ARCore","ARKit","OpenXR"],"interaction_types":["gaze","select","voice","gesture","context_query"]}

    @r.post("/spatial/sessions",status_code=201)
    def create_spatial(p:SpatialSessionIn,authorization:str|None=Header(default=None)):
        i=identity(authorization)
        return store.create_spatial_session(i["organization_id"],i["id"],p.device_id,p.client)

    @r.put("/spatial/sessions/{session_id}/anchors/{anchor_id}")
    def anchor(session_id:str,anchor_id:str,p:AnchorIn,authorization:str|None=Header(default=None)):
        i=identity(authorization);ensure_spatial(i,session_id)
        if p.anchor_id!=anchor_id:raise HTTPException(400,"anchor_id divergente.")
        return store.upsert_anchor(i["organization_id"],session_id,anchor_id,p.label,p.transform.model_dump())

    @r.put("/spatial/sessions/{session_id}/objects/{object_id}")
    def obj(session_id:str,object_id:str,p:ObjectIn,authorization:str|None=Header(default=None)):
        i=identity(authorization);ensure_spatial(i,session_id)
        if p.object_id!=object_id:raise HTTPException(400,"object_id divergente.")
        return store.upsert_object(i["organization_id"],session_id,object_id,p.kind,p.label,p.anchor_id,
                                   p.transform.model_dump(),p.resource)

    @r.get("/spatial/sessions/{session_id}/scene")
    def scene(session_id:str,authorization:str|None=Header(default=None)):
        i=identity(authorization);ensure_spatial(i,session_id)
        return store.scene(i["organization_id"],session_id)

    @r.post("/spatial/sessions/{session_id}/interactions",status_code=201)
    def interaction(session_id:str,p:InteractionIn,authorization:str|None=Header(default=None)):
        i=identity(authorization);ensure_spatial(i,session_id)
        # Foundation only: records intent/context. It never executes ERP mutations.
        return store.interaction(i["organization_id"],i["id"],session_id,p.interaction_type,p.object_id,p.payload)

    return r
