from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from pydantic import BaseModel, Field

from kynka.application.documents import (
    DocumentExtractionError,
    DocumentService,
    DocumentUnsupportedError,
)
from kynka.infrastructure.documents import (
    DocumentDuplicateError,
    DocumentNotFoundError,
    SQLiteDocumentRepository,
)


class DocumentAskRequest(BaseModel):
    question: str = Field(min_length=2)
    document_ids: list[int] | None = None
    limit: int = Field(default=6, ge=1, le=12)


class DocumentSearchRequest(BaseModel):
    query: str = Field(min_length=2)
    document_ids: list[int] | None = None
    limit: int = Field(default=8, ge=1, le=30)


def build_document_router(
    database_path,
    storage_directory,
):
    router = APIRouter(
        prefix="/api/v1/documents",
        tags=["documents"],
    )

    repository = SQLiteDocumentRepository(
        database_path
    )
    service = DocumentService(
        repository,
        storage_directory,
    )

    @router.get("")
    def list_documents(
        category: str | None = None,
        search: str | None = None,
        limit: int = Query(default=100, ge=1, le=500),
    ):
        return service.list(
            category=category,
            search=search,
            limit=limit,
        )

    @router.get("/stats")
    def document_stats():
        return service.stats()

    @router.post("/upload")
    async def upload_document(
        file: Annotated[UploadFile, File(...)],
        title: Annotated[str | None, Form()] = None,
        category: Annotated[str | None, Form()] = None,
    ):
        try:
            content = await file.read()
            if not content:
                raise HTTPException(
                    status_code=400,
                    detail="Arquivo vazio.",
                )
            return service.upload(
                file_name=file.filename or "documento",
                content=content,
                mime_type=file.content_type,
                title=title,
                category=category,
            )
        except DocumentDuplicateError as exc:
            raise HTTPException(
                status_code=409,
                detail=str(exc),
            ) from exc
        except (
            DocumentUnsupportedError,
            DocumentExtractionError,
        ) as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

    @router.post("/search")
    def search_documents(
        request: DocumentSearchRequest,
    ):
        return service.search(
            request.query,
            document_ids=request.document_ids,
            limit=request.limit,
        )

    @router.post("/ask")
    def ask_documents(
        request: DocumentAskRequest,
    ):
        return service.ask(
            request.question,
            document_ids=request.document_ids,
            limit=request.limit,
        )

    @router.get("/{document_id}")
    def get_document(document_id: int):
        try:
            return service.get(document_id)
        except DocumentNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail=str(exc),
            ) from exc

    @router.post("/{document_id}/reindex")
    def reindex_document(document_id: int):
        try:
            return service.reindex(document_id)
        except DocumentNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail=str(exc),
            ) from exc
        except DocumentExtractionError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

    @router.delete("/{document_id}")
    def delete_document(document_id: int):
        try:
            return service.delete(document_id)
        except DocumentNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail=str(exc),
            ) from exc

    return router
