from __future__ import annotations
import json, logging, time
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger("kynka.http")

class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        started = time.perf_counter()
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            status = 500
            log.exception(json.dumps({"event":"http.error","request_id":request_id,
                "method":request.method,"path":request.url.path}, ensure_ascii=False))
            raise
        elapsed = round((time.perf_counter()-started)*1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(elapsed)
        log.info(json.dumps({"event":"http.request","timestamp":datetime.now(timezone.utc).isoformat(),
            "request_id":request_id,"method":request.method,"path":request.url.path,
            "status":status,"duration_ms":elapsed}, ensure_ascii=False))
        return response
