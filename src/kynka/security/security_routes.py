from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel,Field
class BootstrapIn(BaseModel):organization_name:str=Field(min_length=2);name:str=Field(min_length=2);email:str;password:str=Field(min_length=8)
class LoginIn(BaseModel):email:str;password:str
class UserIn(BaseModel):name:str=Field(min_length=2);email:str;password:str=Field(min_length=8);role:str="worker"
class UserPatch(BaseModel):active:bool|None=None;role:str|None=None
def bearer(v):
    return v.split(" ",1)[1].strip() if v and v.lower().startswith("bearer ") else ""
def build_security_router(service):
    r=APIRouter(prefix="/api/v1",tags=["security"])
    def ident(a):
        try:return service.authenticate(bearer(a))
        except ValueError as e:raise HTTPException(401,str(e)) from e
    def run(fn):
        try:return fn()
        except PermissionError as e:raise HTTPException(403,str(e)) from e
        except ValueError as e:raise HTTPException(400,str(e)) from e
    @r.get("/auth/bootstrap-status")
    def bs():return {"required":service.bootstrap_required()}
    @r.post("/auth/bootstrap",status_code=201)
    def boot(p:BootstrapIn):return run(lambda:service.bootstrap(p.organization_name,p.name,p.email,p.password))
    @r.post("/auth/login")
    def login(p:LoginIn):return run(lambda:service.login(p.email,p.password))
    @r.get("/auth/me")
    def me(authorization:str|None=Header(default=None)):return ident(authorization)
    @r.post("/auth/logout")
    def logout(authorization:str|None=Header(default=None)):
        raw=bearer(authorization);ident(authorization);service.store.revoke(service.token_hash(raw));return {"logged_out":True}
    @r.get("/security/users")
    def users(authorization:str|None=Header(default=None)):
        me=ident(authorization)
        if me["role"]!="admin":raise HTTPException(403,"Permissao insuficiente.")
        return service.store.users(me["organization_id"])
    @r.post("/security/users",status_code=201)
    def create(p:UserIn,authorization:str|None=Header(default=None)):
        me=ident(authorization);return run(lambda:service.create_user(me,p.name,p.email,p.password,p.role))
    @r.patch("/security/users/{user_id}")
    def patch(user_id:int,p:UserPatch,authorization:str|None=Header(default=None)):
        me=ident(authorization)
        if me["role"]!="admin":raise HTTPException(403,"Permissao insuficiente.")
        if p.role is not None and p.role not in {"admin","stock_manager","buyer","worker"}:raise HTTPException(400,"Perfil invalido.")
        if user_id==me["id"] and p.active is False:raise HTTPException(400,"Nao desative a propria conta administrativa.")
        if user_id==me["id"] and p.role is not None and p.role!="admin":raise HTTPException(400,"Nao altere o proprio perfil administrativo.")
        service.store.set_user(user_id,me["organization_id"],p.active,p.role);return service.identity(user_id,me["organization_id"])
    @r.get("/events")
    def events(limit:int=100,authorization:str|None=Header(default=None)):
        me=ident(authorization)
        if me["role"]!="admin":raise HTTPException(403,"Permissao insuficiente.")
        return service.store.events(me["organization_id"],min(max(limit,1),500))
    @r.get("/notifications")
    def notifications(limit:int=100,authorization:str|None=Header(default=None)):
        me=ident(authorization);return service.store.notifications(me["organization_id"],me["id"],min(max(limit,1),500))
    return r
