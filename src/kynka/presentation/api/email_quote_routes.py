from fastapi import APIRouter, HTTPException, Request

from kynka.application.email_quotes import EmailQuoteConfig, EmailQuoteError, EmailQuoteService
from kynka.infrastructure.email_quotes import SQLiteEmailQuoteRepository


def build_email_quote_router(database_path):
    router = APIRouter(prefix="/api/v1/email-quotes", tags=["email-quotes"])
    repo = SQLiteEmailQuoteRepository(database_path)

    def service(request: Request):
        return EmailQuoteService(
            repo,
            database_path,
            request.app.state.supplier_service,
            request.app.state.inventory_service,
            EmailQuoteConfig(),
        )

    @router.get("/status")
    def status(request: Request):
        return service(request).status()

    @router.get("/messages")
    def messages(request: Request, limit: int = 50):
        return service(request).list_messages(limit)

    @router.post("/scan")
    def scan(request: Request):
        try:
            return service(request).scan()
        except EmailQuoteError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
