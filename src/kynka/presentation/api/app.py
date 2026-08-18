from __future__ import annotations

import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware

from kynka import __version__
from kynka.application.inventory import InventoryService
from kynka.infrastructure.importers import (
    InventoryImportError,
    InventoryImporter,
)
from kynka.infrastructure.inventory import (
    SQLiteInventoryRepository,
)

from .config import APISettings
from .schemas import (
    CapabilityResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    InventoryImportResponse,
    InventorySummaryResponse,
    MaterialResponse,
    MemoryRecordResponse,
    MemoryResponse,
    SessionCreateResponse,
    StatusResponse,
    VariablesResponse,
)
from .serializers import (
    json_safe,
    serialize_execution,
)
from .session_manager import SessionManager


DATABASE_PATH = Path("data/kynka.db")


def create_app(
    settings: APISettings | None = None,
) -> FastAPI:
    """
    Cria a aplicação HTTP da plataforma Kynka.
    """

    settings = settings or APISettings.from_env()

    manager = SessionManager(
        settings
    )

    inventory_repository = (
        SQLiteInventoryRepository(
            DATABASE_PATH
        )
    )

    inventory_service = InventoryService(
        inventory_repository
    )

    inventory_importer = InventoryImporter(
        inventory_service
    )

    @asynccontextmanager
    async def lifespan(
        _: FastAPI,
    ):
        yield
        manager.shutdown()

    api = FastAPI(
        title=settings.app_name,
        version=settings.version,
        lifespan=lifespan,
    )

    api.state.settings = settings
    api.state.sessions = manager
    api.state.inventory_service = (
        inventory_service
    )

    api.add_middleware(
        CORSMiddleware,
        allow_origins=list(
            settings.cors_origins
        ),
        allow_credentials=False,
        allow_methods=[
            "GET",
            "POST",
            "DELETE",
            "OPTIONS",
        ],
        allow_headers=[
            "Content-Type",
            "Authorization",
        ],
    )

    # ========================================================
    # System
    # ========================================================

    @api.get(
        "/api/v1/health",
        response_model=HealthResponse,
        tags=["system"],
    )
    def health():
        return HealthResponse(
            status="ok"
        )

    @api.get(
        "/api/v1/status",
        response_model=StatusResponse,
        tags=["system"],
    )
    def status():
        return StatusResponse(
            status="ok",
            version=__version__,
            model=settings.model,
            sessions=manager.count,
        )

    # ========================================================
    # Sessions
    # ========================================================

    @api.post(
        "/api/v1/sessions",
        response_model=SessionCreateResponse,
        tags=["sessions"],
    )
    def create_session():
        session = manager.create()

        return SessionCreateResponse(
            session_id=session.id
        )

    @api.delete(
        "/api/v1/sessions/{session_id}",
        tags=["sessions"],
    )
    def delete_session(
        session_id: str,
    ):
        if not manager.delete(
            session_id
        ):
            raise HTTPException(
                status_code=404,
                detail="Sessão não encontrada.",
            )

        return {
            "deleted": True
        }

    # ========================================================
    # Chat
    # ========================================================

    @api.post(
        "/api/v1/chat",
        response_model=ChatResponse,
        tags=["agent"],
    )
    def chat(
        request: ChatRequest,
    ):
        session = manager.get_or_create(
            request.session_id
        )

        try:
            result = session.kynka.run(
                request.message
            )

            return ChatResponse(
                **serialize_execution(
                    session.id,
                    result,
                )
            )

        except Exception as error:
            return ChatResponse(
                session_id=session.id,
                success=False,
                mode="simple",
                error=str(error),
            )

    # ========================================================
    # Memory
    # ========================================================

    @api.get(
        "/api/v1/sessions/{session_id}/memory",
        response_model=MemoryResponse,
        tags=["sessions"],
    )
    def memory(
        session_id: str,
    ):
        session = manager.get(
            session_id
        )

        if not session:
            raise HTTPException(
                status_code=404,
                detail="Sessão não encontrada.",
            )

        records = [
            MemoryRecordResponse(
                text=record.text,
                success=record.success,
                capability=record.capability,
                arguments=json_safe(
                    record.arguments
                ),
                result=json_safe(
                    record.result
                ),
                error=record.error,
                operational=getattr(
                    record,
                    "operational",
                    True,
                ),
            )
            for record
            in session.kynka.memory.records
        ]

        return MemoryResponse(
            session_id=session.id,
            records=records,
        )

    @api.delete(
        "/api/v1/sessions/{session_id}/memory",
        tags=["sessions"],
    )
    def clear_memory(
        session_id: str,
    ):
        session = manager.get(
            session_id
        )

        if not session:
            raise HTTPException(
                status_code=404,
                detail="Sessão não encontrada.",
            )

        session.kynka.memory.clear()

        return {
            "cleared": True
        }

    @api.get(
        "/api/v1/sessions/{session_id}/variables",
        response_model=VariablesResponse,
        tags=["sessions"],
    )
    def variables(
        session_id: str,
    ):
        session = manager.get(
            session_id
        )

        if not session:
            raise HTTPException(
                status_code=404,
                detail="Sessão não encontrada.",
            )

        return VariablesResponse(
            session_id=session.id,
            variables=json_safe(
                session.kynka.context.variables
            ),
        )

    # ========================================================
    # Capabilities
    # ========================================================

    @api.get(
        "/api/v1/capabilities",
        response_model=list[
            CapabilityResponse
        ],
        tags=["agent"],
    )
    def capabilities():
        session = manager.create()

        try:
            return [
                CapabilityResponse(
                    name=name,
                    description=(
                        capability
                        .metadata
                        .description
                    ),
                    version=getattr(
                        capability.metadata,
                        "version",
                        None,
                    ),
                )
                for name, capability
                in (
                    session
                    .kynka
                    .runtime
                    .registry
                    .capabilities
                    .items()
                )
            ]

        finally:
            manager.delete(
                session.id
            )

    # ========================================================
    # Inventory helpers
    # ========================================================

    def material_response(
        material,
    ) -> MaterialResponse:
        return MaterialResponse(
            code=material.code,
            name=material.name,
            quantity=material.quantity,
            unit=material.unit,
            minimum_quantity=(
                material.minimum_quantity
            ),
            below_minimum=(
                material.is_below_minimum
            ),
        )

    def summary_response():
        summary = (
            inventory_service.summary()
        )

        return InventorySummaryResponse(
            total_materials=(
                summary.total_materials
            ),
            below_minimum=(
                summary.below_minimum
            ),
            zero_stock=(
                summary.zero_stock
            ),
        )

    # ========================================================
    # Inventory
    # ========================================================

    @api.get(
        "/api/v1/inventory",
        response_model=list[
            MaterialResponse
        ],
        tags=["inventory"],
    )
    def inventory_list():
        """
        Lista todos os materiais do estoque.
        """

        return [
            material_response(material)
            for material
            in inventory_service.list_materials()
        ]

    @api.get(
        "/api/v1/inventory/search",
        response_model=list[
            MaterialResponse
        ],
        tags=["inventory"],
    )
    def inventory_search(
        query: str = Query(
            ...,
            min_length=1,
        ),
    ):
        """
        Pesquisa materiais por código ou nome.
        """

        return [
            material_response(material)
            for material
            in inventory_service.search_materials(
                query
            )
        ]

    @api.get(
        "/api/v1/inventory/low-stock",
        response_model=list[
            MaterialResponse
        ],
        tags=["inventory"],
    )
    def inventory_low_stock():
        """
        Lista materiais abaixo do estoque mínimo.
        """

        return [
            material_response(material)
            for material
            in (
                inventory_service
                .list_below_minimum()
            )
        ]

    @api.get(
        "/api/v1/inventory/summary",
        response_model=(
            InventorySummaryResponse
        ),
        tags=["inventory"],
    )
    def inventory_summary():
        """
        Retorna indicadores gerais do estoque.
        """

        return summary_response()

    @api.post(
        "/api/v1/inventory/import",
        response_model=(
            InventoryImportResponse
        ),
        tags=["inventory"],
    )
    async def inventory_import(
        file: UploadFile = File(...),
    ):
        """
        Importa estoque a partir de CSV ou XLSX.
        """

        filename = (
            file.filename
            or "inventory"
        )

        extension = (
            Path(filename)
            .suffix
            .lower()
        )

        if extension not in {
            ".csv",
            ".xlsx",
        }:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Formato não suportado. "
                    "Utilize .csv ou .xlsx."
                ),
            )

        temporary_path: (
            Path | None
        ) = None

        try:
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=extension,
            ) as temporary_file:

                temporary_path = Path(
                    temporary_file.name
                )

                shutil.copyfileobj(
                    file.file,
                    temporary_file,
                )

            result = (
                inventory_importer
                .import_file(
                    temporary_path
                )
            )

            return InventoryImportResponse(
                filename=filename,
                imported=result.imported,
                skipped=result.skipped,
                errors=(
                    result.errors or []
                ),
                summary=summary_response(),
            )

        except InventoryImportError as error:
            raise HTTPException(
                status_code=400,
                detail=str(error),
            ) from error

        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Erro durante a importação "
                    f"do inventário: {error}"
                ),
            ) from error

        finally:
            await file.close()

            if (
                temporary_path
                and temporary_path.exists()
            ):
                temporary_path.unlink(
                    missing_ok=True
                )

    return api


app = create_app()