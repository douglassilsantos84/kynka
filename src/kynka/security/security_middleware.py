from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
PUBLIC={("GET","/api/v1/health"),("GET","/api/v1/status"),("GET","/api/v1/platform/health"),("GET","/api/v1/platform/ready"),("GET","/api/v1/auth/bootstrap-status"),("POST","/api/v1/auth/bootstrap"),("POST","/api/v1/auth/login")}
class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self,app,security_service):super().__init__(app);self.security=security_service
    async def dispatch(self,request,call_next):
        path=request.url.path;method=request.method.upper()
        if method=="OPTIONS" or not path.startswith("/api/v1") or (method,path) in PUBLIC:return await call_next(request)
        h=request.headers.get("Authorization","");raw=h.split(" ",1)[1].strip() if h.lower().startswith("bearer ") else ""
        try:i=self.security.authenticate(raw)
        except ValueError as e:return JSONResponse({"detail":str(e)},status_code=401)
        if not self.allowed(i["role"],method,path):return JSONResponse({"detail":"Permissao insuficiente."},status_code=403)
        request.state.identity=i;response=await call_next(request)
        if method in {"POST","PUT","PATCH","DELETE"}:
            try:self.security.store.event(i["organization_id"],i["id"],"api.mutation","http",path,f"{method} {response.status_code}")
            except Exception:pass
        return response
    @staticmethod
    def allowed(role,method,path):
        if role=="admin":return True
        if path.startswith("/api/v1/auth/") or path.startswith("/api/v1/notifications") or path.startswith("/api/v1/agentic") or path.startswith("/api/v1/platform"):return True
        if role=="stock_manager":
            if path.startswith("/api/v1/security") or path.startswith("/api/v1/events"):return False
            if any(path.startswith(x) for x in ["/api/v1/suppliers","/api/v1/procurement","/api/v1/quote-imports","/api/v1/email-quotes"]):return method=="GET"
            return True
        if role=="buyer":
            if path.startswith("/api/v1/security") or path.startswith("/api/v1/events"):return False
            if any(path.startswith(x) for x in ["/api/v1/inventory","/api/v1/demands","/api/v1/material-requests"]):return method=="GET"
            return True
        if role=="worker":
            if method=="GET" and any(path.startswith(x) for x in ["/api/v1/inventory","/api/v1/demands","/api/v1/documents","/api/v1/material-requests","/api/v1/capabilities","/api/v1/sessions"]):return True
            if method=="POST" and path in {"/api/v1/chat","/api/v1/sessions","/api/v1/material-requests","/api/v1/documents/search","/api/v1/documents/ask"}:return True
        return False
