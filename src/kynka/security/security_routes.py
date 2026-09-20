from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field


class BootstrapIn(BaseModel):
    organization_name: str = Field(min_length=2)
    name: str = Field(min_length=2)
    email: str
    password: str = Field(min_length=12)


class LoginIn(BaseModel):
    email: str
    password: str


class UserIn(BaseModel):
    name: str = Field(min_length=2)
    email: str
    password: str = Field(min_length=12)
    role: str = "worker"


class UserPatch(BaseModel):
    active: bool | None = None
    role: str | None = None


def bearer(value):
    return value.split(" ", 1)[1].strip() if value and value.lower().startswith("bearer ") else ""


def build_security_router(service):
    router = APIRouter(prefix="/api/v1", tags=["security"])

    def ident(authorization):
        try:
            return service.authenticate(bearer(authorization))
        except ValueError as error:
            raise HTTPException(401, str(error)) from error

    def run(function):
        try:
            return function()
        except PermissionError as error:
            raise HTTPException(429 if "tentativas" in str(error) else 403, str(error)) from error
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @router.get("/auth/bootstrap-status")
    def bootstrap_status():
        return {"required": service.bootstrap_required()}

    @router.post("/auth/bootstrap", status_code=201)
    def bootstrap(payload: BootstrapIn):
        return run(lambda: service.bootstrap(
            payload.organization_name, payload.name, payload.email, payload.password
        ))

    @router.post("/auth/login")
    def login(payload: LoginIn, request: Request):
        client = request.client.host if request.client else "unknown"
        try:
            return service.login(payload.email, payload.password, client)
        except PermissionError as error:
            raise HTTPException(429, str(error)) from error
        except ValueError as error:
            raise HTTPException(401, str(error)) from error

    @router.get("/auth/me")
    def me(authorization: str | None = Header(default=None)):
        return ident(authorization)

    @router.post("/auth/logout")
    def logout(authorization: str | None = Header(default=None)):
        raw = bearer(authorization)
        identity = ident(authorization)
        service.store.revoke(service.token_hash(raw))
        service.store.event(
            identity["organization_id"], identity["id"],
            "security.logout", "user", str(identity["id"]), "success"
        )
        return {"logged_out": True}

    @router.get("/security/users")
    def users(authorization: str | None = Header(default=None)):
        identity = ident(authorization)
        if identity["role"] != "admin":
            raise HTTPException(403, "Permissao insuficiente.")
        return service.store.users(identity["organization_id"])

    @router.post("/security/users", status_code=201)
    def create(payload: UserIn, authorization: str | None = Header(default=None)):
        identity = ident(authorization)
        return run(lambda: service.create_user(
            identity, payload.name, payload.email, payload.password, payload.role
        ))

    @router.patch("/security/users/{user_id}")
    def patch(user_id: int, payload: UserPatch, authorization: str | None = Header(default=None)):
        identity = ident(authorization)
        if identity["role"] != "admin":
            raise HTTPException(403, "Permissao insuficiente.")
        if payload.role is not None and payload.role not in {
            "admin", "stock_manager", "buyer", "worker"
        }:
            raise HTTPException(400, "Perfil invalido.")
        if user_id == identity["id"] and payload.active is False:
            raise HTTPException(400, "Nao desative a propria conta administrativa.")
        if user_id == identity["id"] and payload.role is not None and payload.role != "admin":
            raise HTTPException(400, "Nao altere o proprio perfil administrativo.")
        run(lambda: service.store.set_user(
            user_id, identity["organization_id"], payload.active, payload.role
        ))
        return service.identity(user_id, identity["organization_id"])

    @router.get("/events")
    def events(limit: int = 100, authorization: str | None = Header(default=None)):
        identity = ident(authorization)
        if identity["role"] != "admin":
            raise HTTPException(403, "Permissao insuficiente.")
        return service.store.events(identity["organization_id"], min(max(limit, 1), 500))

    @router.get("/notifications")
    def notifications(limit: int = 100, authorization: str | None = Header(default=None)):
        identity = ident(authorization)
        return service.store.notifications(
            identity["organization_id"], identity["id"], min(max(limit, 1), 500)
        )

    return router
