from __future__ import annotations

import shutil
import tempfile
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware

from kynka import __version__

from kynka.application.demand import (
    DemandAlreadyExistsError,
    DemandMaterialNotFoundError,
    DemandNotFoundError,
    DemandService,
    MissingMaterialResolutionError,
    MissingMaterialService,
)

from kynka.application.demand.importers import (
    QuantityMapImporter,
)

from kynka.application.procurement import (
    ProcurementService,
    PurchaseOrderDuplicateError,
    PurchaseOrderNotFoundError,
    PurchaseOrderService,
    PurchaseOrderStateError,
)

from kynka.application.inventory import (
    InsufficientStockError,
    InventoryService,
    MaterialAlreadyExistsError,
    MaterialNotFoundError,
)

from kynka.application.suppliers import (
    SupplierAlreadyExistsError,
    SupplierCatalogError,
    SupplierNotFoundError,
    SupplierService,
)

from kynka.infrastructure.importers import (
    InventoryImporter,
)

from kynka.infrastructure.demand import (
    SQLiteDemandRepository,
)

from kynka.infrastructure.inventory import (
    SQLiteInventoryRepository,
)

from kynka.infrastructure.procurement import (
    SQLitePurchaseOrderRepository,
)

from kynka.infrastructure.suppliers import (
    SQLiteSupplierRepository,
)

from .quote_import_routes import build_quote_import_router
from .email_quote_routes import build_email_quote_router
from .document_routes import build_document_router

from .config import APISettings

from .schemas import (
    CapabilityResponse,
    ChatRequest,
    ChatResponse,
    DemandCreateRequest,
    DemandPlanItemResponse,
    DemandPlanResponse,
    DemandRequirementRequest,
    DemandRequirementResponse,
    DemandResponse,
    HealthResponse,
    InventoryImportResponse,
    InventorySummaryResponse,
    MaterialCreateRequest,
    MaterialResponse,
    MaterialUpdateRequest,
    MissingMaterialResolveRequest,
    MissingMaterialResolveResponse,
    MemoryRecordResponse,
    MemoryResponse,
    InventoryMovementRequest,
    InventoryMovementResponse,
    QuantityMapImportResponse,
    QuantityMapMissingMaterialResponse,
    ConsolidatedPurchaseListRequest,
    PurchaseDemandShareResponse,
    PurchaseListItemResponse,
    PurchaseListResponse,
    PurchaseOrderCreateRequest,
    PurchaseOrderItemResponse,
    PurchaseOrderReceiveRequest,
    PurchaseOrderResponse,
    MaterialQuoteResponse,
    PurchaseQuoteRequest,
    PurchaseQuoteResponse,
    PurchaseSupplierOptionResponse,
    SupplierCreateRequest,
    SupplierMaterialResponse,
    SupplierMaterialUpsertRequest,
    SupplierPriceHistoryResponse,
    SupplierResponse,
    SupplierStatusRequest,
    SupplierUpdateRequest,
    StatusResponse,
    StockReservationResponse,
    VariablesResponse,
)

from .serializers import (
    json_safe,
    serialize_execution,
)

from .session_manager import (
    SessionManager,
)

from .material_request_routes import create_material_request_router
from kynka.security import SecurityMiddleware, SecurityService, SecurityStore, build_security_router
from kynka.production import MigrationManager, ObservabilityMiddleware, build_production_router
from kynka.production_data import PostgreSQLTarget
from kynka.spatial import build_spatial_router
from kynka.spatial.migrations import apply_spatial_migration
from kynka.agentic import build_agentic_router


# ============================================================
# Paths
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATA_DIRECTORY = (
    PROJECT_ROOT / "data"
)

DATABASE_PATH = (
    DATA_DIRECTORY / "kynka.db"
)


# ============================================================
# Application
# ============================================================


def create_app(
    settings: APISettings | None = None,
) -> FastAPI:

    settings = (
        settings
        or APISettings.from_env()
    )

    # Production 1.0 / Etapa 40A.3
    # PostgreSQL is an independently probed migration target.
    # Legacy repositories remain on SQLite until Etapa 40C.
    postgresql_target = PostgreSQLTarget.from_env()

    DATA_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Etapa 32 - additive schema migrations
    MigrationManager(DATABASE_PATH).apply()
    apply_spatial_migration(DATABASE_PATH)

    manager = SessionManager(
        settings
    )

    # ========================================================
    # Inventory
    # ========================================================

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

    # ========================================================
    # Demands / Projects
    # ========================================================

    demand_repository = (
        SQLiteDemandRepository(
            DATABASE_PATH
        )
    )

    demand_service = DemandService(
        demand_repository,
        inventory_repository,
    )

    missing_material_service = MissingMaterialService(
        inventory_service,
        demand_service,
    )

    procurement_service = ProcurementService(
        demand_repository,
        inventory_repository,
    )

    supplier_repository = SQLiteSupplierRepository(
        DATABASE_PATH
    )

    supplier_service = SupplierService(
        supplier_repository,
        inventory_service,
        procurement_service,
        demand_repository,
    )

    purchase_order_repository = SQLitePurchaseOrderRepository(
        DATABASE_PATH
    )

    purchase_order_service = PurchaseOrderService(
        purchase_order_repository,
        procurement_service,
        inventory_service,
        supplier_service,
    )

    # ========================================================
    # Quantity Map Importer
    # ========================================================

    quantity_map_importer = QuantityMapImporter(
        demand_service,
        inventory_repository,
    )

    # ========================================================
    # Lifespan
    # ========================================================

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
    api.state.postgresql_target = postgresql_target

    api.state.inventory_service = (
        inventory_service
    )

    api.state.demand_service = (
        demand_service
    )

    api.state.missing_material_service = (
        missing_material_service
    )

    api.state.procurement_service = (
        procurement_service
    )

    api.state.supplier_service = (
        supplier_service
    )

    api.state.purchase_order_service = (
        purchase_order_service
    )

    api.state.quantity_map_importer = (
        quantity_map_importer
    )

    # Etapas 24-26 - Security / Organization / Events
    security_store = SecurityStore(DATABASE_PATH)
    security_service = SecurityService(security_store)
    api.state.security_store = security_store
    api.state.security_service = security_service
    api.include_router(build_security_router(security_service))
    api.add_middleware(SecurityMiddleware, security_service=security_service)
    api.add_middleware(ObservabilityMiddleware)

    # ========================================================
    # CORS
    # ========================================================

    api.include_router(build_quote_import_router(DATABASE_PATH))
    api.include_router(build_email_quote_router(DATABASE_PATH))
    api.include_router(build_document_router(DATABASE_PATH, DATA_DIRECTORY / "documents"))
    api.include_router(build_agentic_router(DATABASE_PATH, DATA_DIRECTORY / "documents", security_service, inventory_service, supplier_service))
    api.include_router(
        build_production_router(
            DATABASE_PATH,
            security_service,
            postgresql_target=postgresql_target,
        )
    )
    api.include_router(build_spatial_router(DATABASE_PATH, security_service))

    api.add_middleware(
        CORSMiddleware,
        allow_origins=list(
            settings.cors_origins
        ),
        allow_credentials=False,
        allow_methods=[
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "OPTIONS",
        ],
        allow_headers=[
            "Content-Type",
            "Authorization",
        ],
    )

    # ========================================================
    # Serialization helpers
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
                material.quantity
                < material.minimum_quantity
            ),
        )

    def movement_response(
        movement,
    ) -> InventoryMovementResponse:

        return InventoryMovementResponse(
            id=movement.id,
            material_code=movement.material_code,
            type=movement.movement_type.value,
            quantity=movement.quantity,
            previous_quantity=movement.previous_quantity,
            new_quantity=movement.new_quantity,
            reason=movement.reason,
            created_at=movement.created_at,
        )

    def demand_response(
        demand,
    ) -> DemandResponse:

        return DemandResponse(
            id=demand.id,
            code=demand.code,
            name=demand.name,
            kind=demand.kind,
            client=demand.client,
            location=demand.location,
            start_date=(
                demand.start_date.isoformat()
                if demand.start_date
                else None
            ),
            status=demand.status.value,
            notes=demand.notes,
            created_at=demand.created_at,
        )

    def requirement_response(
        requirement,
    ) -> DemandRequirementResponse:

        return DemandRequirementResponse(
            id=requirement.id,
            demand_id=(
                requirement.demand_id
            ),
            material_code=(
                requirement.material_code
            ),
            required_quantity=(
                requirement.required_quantity
            ),
        )

    def reservation_response(
        reservation,
    ) -> StockReservationResponse:

        return StockReservationResponse(
            id=reservation.id,
            demand_id=(
                reservation.demand_id
            ),
            material_code=(
                reservation.material_code
            ),
            quantity=(
                reservation.quantity
            ),
            created_at=(
                reservation.created_at
            ),
            updated_at=(
                reservation.updated_at
            ),
        )

    def demand_plan_response(
        plan,
    ) -> DemandPlanResponse:

        return DemandPlanResponse(
            demand_id=plan.demand_id,
            demand_code=plan.demand_code,
            demand_name=plan.demand_name,
            total_items=plan.total_items,
            available_items=(
                plan.available_items
            ),
            shortage_items=(
                plan.shortage_items
            ),
            items=[
                DemandPlanItemResponse(
                    material_code=(
                        item.material_code
                    ),
                    material_name=(
                        item.material_name
                    ),
                    unit=item.unit,
                    required_quantity=(
                        item.required_quantity
                    ),
                    physical_quantity=(
                        item.physical_quantity
                    ),
                    minimum_quantity=(
                        item.minimum_quantity
                    ),
                    reserved_total=(
                        item.reserved_total
                    ),
                    reserved_for_this_demand=(
                        item
                        .reserved_for_this_demand
                    ),
                    reserved_for_other_demands=(
                        item
                        .reserved_for_other_demands
                    ),
                    free_quantity=(
                        item.free_quantity
                    ),
                    quantity_still_required=(
                        item
                        .quantity_still_required
                    ),
                    quantity_available_to_reserve=(
                        item
                        .quantity_available_to_reserve
                    ),
                    shortage_quantity=(
                        item.shortage_quantity
                    ),
                    fully_available=(
                        item.fully_available
                    ),
                )
                for item in plan.items
            ],
        )

    def purchase_list_response(purchase_list) -> PurchaseListResponse:
        return PurchaseListResponse(
            demand_ids=purchase_list.demand_ids, demand_codes=purchase_list.demand_codes,
            total_materials=purchase_list.total_materials, materials_to_buy=purchase_list.materials_to_buy,
            items=[PurchaseListItemResponse(
                material_code=i.material_code, material_name=i.material_name, unit=i.unit,
                required_quantity=i.required_quantity, reserved_quantity=i.reserved_quantity,
                physical_quantity=i.physical_quantity, minimum_quantity=i.minimum_quantity,
                reserved_total=i.reserved_total, free_quantity=i.free_quantity, quantity_to_buy=i.quantity_to_buy,
                demands=[PurchaseDemandShareResponse(
                    demand_id=d.demand_id,demand_code=d.demand_code,demand_name=d.demand_name,
                    required_quantity=d.required_quantity,reserved_quantity=d.reserved_quantity,remaining_quantity=d.remaining_quantity
                ) for d in i.demands]
            ) for i in purchase_list.items], analysis=purchase_list.analysis
        )

    def purchase_order_response(order) -> PurchaseOrderResponse:
        return PurchaseOrderResponse(
            id=order.id,
            status=order.status,
            demand_ids=order.demand_ids,
            demand_codes=order.demand_codes,
            supplier_id=order.supplier_id,
            supplier_code=order.supplier_code,
            supplier_name=order.supplier_name,
            total_estimated=order.total_estimated,
            notes=order.notes,
            created_at=order.created_at,
            ordered_at=order.ordered_at,
            completed_at=order.completed_at,
            items=[
                PurchaseOrderItemResponse(
                    id=item.id,
                    material_code=item.material_code,
                    material_name=item.material_name,
                    unit=item.unit,
                    quantity_ordered=item.quantity_ordered,
                    quantity_received=item.quantity_received,
                    quantity_pending=item.quantity_pending,
                    unit_price=item.unit_price,
                    total_price=item.total_price,
                )
                for item in order.items
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
        tags=["sessions"],
    )
    def create_session():

        session = manager.create()

        return {
            "session_id": session.id
        }

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
                detail=(
                    "SessÃƒÂ£o nÃƒÂ£o encontrada."
                ),
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

        session = (
            manager.get_or_create(
                request.session_id
            )
        )

        try:
            supplier_answer = supplier_service.try_answer(request.message)
            if supplier_answer is not None:
                return ChatResponse(
                    session_id=session.id,
                    success=True,
                    mode="simple",
                    result=supplier_answer,
                    capability="procurement.supplier_intelligence",
                    arguments={},
                )

            procurement_answer = procurement_service.try_answer(request.message)
            if procurement_answer is not None:
                answer, purchase_list = procurement_answer
                return ChatResponse(session_id=session.id, success=True, mode="simple", result=answer, capability="procurement.purchase_list", arguments={"demand_ids": purchase_list.demand_ids})

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
                detail=(
                    "SessÃƒÂ£o nÃƒÂ£o encontrada."
                ),
            )

        records = [
            MemoryRecordResponse(
                text=record.text,
                success=record.success,
                capability=(
                    record.capability
                ),
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
                detail=(
                    "SessÃƒÂ£o nÃƒÂ£o encontrada."
                ),
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
                detail=(
                    "SessÃƒÂ£o nÃƒÂ£o encontrada."
                ),
            )

        return VariablesResponse(
            session_id=session.id,
            variables=json_safe(
                session.kynka
                .context.variables
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
                        .metadata.description
                    ),
                    version=getattr(
                        capability.metadata,
                        "version",
                        None,
                    ),
                )
                for name, capability
                in session.kynka.runtime
                .registry.capabilities.items()
            ]

        finally:
            manager.delete(
                session.id
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

        materials = (
            inventory_service
            .list_materials()
        )

        return [
            material_response(material)
            for material in materials
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
            min_length=1
        ),
    ):

        materials = (
            inventory_service.search(
                query
            )
        )

        return [
            material_response(material)
            for material in materials
        ]

    @api.get(
        "/api/v1/inventory/low-stock",
        response_model=list[
            MaterialResponse
        ],
        tags=["inventory"],
    )
    def inventory_low_stock():

        materials = (
            inventory_service.low_stock()
        )

        return [
            material_response(material)
            for material in materials
        ]

    @api.get(
        "/api/v1/inventory/summary",
        response_model=(
            InventorySummaryResponse
        ),
        tags=["inventory"],
    )
    def inventory_summary():

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
    # Inventory import
    # ========================================================

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

        filename = (
            file.filename
            or "inventory.xlsx"
        )

        suffix = (
            Path(filename)
            .suffix
            .lower()
        )

        if suffix not in {
            ".xlsx",
            ".xlsm",
        }:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Arquivo invÃƒÂ¡lido. "
                    "Utilize .xlsx ou .xlsm."
                ),
            )

        temporary_path = None

        try:
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
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

            summary = (
                inventory_service
                .summary()
            )

            return InventoryImportResponse(
                filename=filename,
                imported=result.imported,
                skipped=result.skipped,
                errors=result.errors,
                summary=(
                    InventorySummaryResponse(
                        total_materials=(
                            summary
                            .total_materials
                        ),
                        below_minimum=(
                            summary
                            .below_minimum
                        ),
                        zero_stock=(
                            summary
                            .zero_stock
                        ),
                    )
                ),
            )

        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail=str(error),
            ) from error

        finally:
            await file.close()

            if (
                temporary_path
                is not None
                and temporary_path.exists()
            ):
                temporary_path.unlink(
                    missing_ok=True
                )

    # ========================================================
    # Inventory CRUD
    # ========================================================

    @api.post(
        "/api/v1/inventory",
        response_model=MaterialResponse,
        status_code=201,
        tags=["inventory"],
    )
    def inventory_create(
        request: MaterialCreateRequest,
    ):

        try:
            material = (
                inventory_service
                .create_material(
                    code=request.code,
                    name=request.name,
                    quantity=(
                        request.quantity
                    ),
                    unit=request.unit,
                    minimum_quantity=(
                        request
                        .minimum_quantity
                    ),
                )
            )

            return material_response(
                material
            )

        except (
            MaterialAlreadyExistsError,
            ValueError,
        ) as error:

            raise HTTPException(
                status_code=400,
                detail=str(error),
            ) from error

    @api.put(
        "/api/v1/inventory/{code}",
        response_model=MaterialResponse,
        tags=["inventory"],
    )
    def inventory_update(
        code: str,
        request: MaterialUpdateRequest,
    ):

        try:
            material = (
                inventory_service
                .update_material(
                    code=code,
                    name=request.name,
                    unit=request.unit,
                    minimum_quantity=(
                        request
                        .minimum_quantity
                    ),
                )
            )

            return material_response(
                material
            )

        except MaterialNotFoundError as error:
            raise HTTPException(
                status_code=404,
                detail=str(error),
            ) from error

        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail=str(error),
            ) from error

    @api.delete(
        "/api/v1/inventory/{code}",
        tags=["inventory"],
    )
    def inventory_delete(
        code: str,
    ):

        try:
            inventory_service.delete_material(
                code
            )

            return {
                "deleted": True,
                "code": code,
            }

        except MaterialNotFoundError as error:
            raise HTTPException(
                status_code=404,
                detail=str(error),
            ) from error

    # ========================================================
    # Inventory movements
    # ========================================================

    @api.post(
        "/api/v1/inventory/{code}/movements",
        response_model=InventoryMovementResponse,
        status_code=201,
        tags=["inventory"],
    )
    def inventory_movement(
        code: str,
        request: InventoryMovementRequest,
    ):

        try:
            movement_type = (
                request.type
                .strip()
                .lower()
            )

            if movement_type == "entry":
                movement = (
                    inventory_service
                    .add_entry(
                        code,
                        request.quantity,
                        request.reason,
                    )
                )

            elif movement_type == "exit":
                movement = (
                    inventory_service
                    .add_exit(
                        code,
                        request.quantity,
                        request.reason,
                    )
                )

            elif movement_type == "adjustment":
                movement = (
                    inventory_service
                    .adjust_stock(
                        code,
                        request.quantity,
                        request.reason,
                    )
                )

            else:
                raise ValueError(
                    "Tipo de movimentaÃƒÂ§ÃƒÂ£o invÃƒÂ¡lido."
                )

            return movement_response(
                movement
            )

        except MaterialNotFoundError as error:
            raise HTTPException(
                status_code=404,
                detail=str(error),
            ) from error

        except InsufficientStockError as error:
            raise HTTPException(
                status_code=409,
                detail=str(error),
            ) from error

        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail=str(error),
            ) from error

    @api.get(
        "/api/v1/inventory/{code}/movements",
        response_model=list[
            InventoryMovementResponse
        ],
        tags=["inventory"],
    )
    def inventory_movements(
        code: str,
    ):

        try:
            movements = (
                inventory_service
                .list_movements(
                    code
                )
            )

            return [
                movement_response(
                    movement
                )
                for movement
                in movements
            ]

        except MaterialNotFoundError as error:
            raise HTTPException(
                status_code=404,
                detail=str(error),
            ) from error

    # ========================================================
    # Demands / Projects
    # ========================================================

    @api.post(
        "/api/v1/demands",
        response_model=DemandResponse,
        status_code=201,
        tags=["demands"],
    )
    def demand_create(
        request: DemandCreateRequest,
    ):

        try:
            parsed_start_date = None

            if request.start_date:
                try:
                    parsed_start_date = (
                        date.fromisoformat(
                            request.start_date
                        )
                    )

                except ValueError as error:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Data inicial invÃƒÂ¡lida. "
                            "Utilize YYYY-MM-DD."
                        ),
                    ) from error

            demand = (
                demand_service.create_demand(
                    code=request.code,
                    name=request.name,
                    kind=request.kind,
                    client=request.client,
                    location=(
                        request.location
                    ),
                    start_date=(
                        parsed_start_date
                    ),
                    notes=request.notes,
                )
            )

            return demand_response(
                demand
            )

        except DemandAlreadyExistsError as error:
            raise HTTPException(
                status_code=409,
                detail=str(error),
            ) from error

        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail=str(error),
            ) from error

    @api.get(
        "/api/v1/demands",
        response_model=list[
            DemandResponse
        ],
        tags=["demands"],
    )
    def demand_list():

        return [
            demand_response(demand)
            for demand
            in demand_service.list_demands()
        ]

    @api.get(
        "/api/v1/demands/{demand_id}",
        response_model=DemandResponse,
        tags=["demands"],
    )
    def demand_get(
        demand_id: int,
    ):

        try:
            demand = (
                demand_service
                .get_demand(
                    demand_id
                )
            )

            return demand_response(
                demand
            )

        except DemandNotFoundError as error:
            raise HTTPException(
                status_code=404,
                detail=str(error),
            ) from error

    # ========================================================
    # Demand requirements
    # ========================================================

    @api.post(
        "/api/v1/demands/{demand_id}/requirements",
        response_model=(
            DemandRequirementResponse
        ),
        status_code=201,
        tags=["demands"],
    )
    def demand_set_requirement(
        demand_id: int,
        request: DemandRequirementRequest,
    ):

        try:
            requirement = (
                demand_service
                .set_requirement(
                    demand_id=demand_id,
                    material_code=(
                        request.material_code
                    ),
                    required_quantity=(
                        request
                        .required_quantity
                    ),
                )
            )

            return requirement_response(
                requirement
            )

        except DemandNotFoundError as error:
            raise HTTPException(
                status_code=404,
                detail=str(error),
            ) from error

        except DemandMaterialNotFoundError as error:
            raise HTTPException(
                status_code=404,
                detail=str(error),
            ) from error

        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail=str(error),
            ) from error

    @api.get(
        "/api/v1/demands/{demand_id}/requirements",
        response_model=list[
            DemandRequirementResponse
        ],
        tags=["demands"],
    )
    def demand_requirements(
        demand_id: int,
    ):

        try:
            requirements = (
                demand_service
                .list_requirements(
                    demand_id
                )
            )

            return [
                requirement_response(
                    requirement
                )
                for requirement
                in requirements
            ]

        except DemandNotFoundError as error:
            raise HTTPException(
                status_code=404,
                detail=str(error),
            ) from error

    # ========================================================
    # Demand planning
    # ========================================================

    @api.get(
        "/api/v1/demands/{demand_id}/plan",
        response_model=DemandPlanResponse,
        tags=["demands"],
    )
    def demand_plan(
        demand_id: int,
    ):

        try:
            plan = (
                demand_service
                .calculate_plan(
                    demand_id
                )
            )

            return demand_plan_response(
                plan
            )

        except DemandNotFoundError as error:
            raise HTTPException(
                status_code=404,
                detail=str(error),
            ) from error

        except DemandMaterialNotFoundError as error:
            raise HTTPException(
                status_code=409,
                detail=str(error),
            ) from error

    # ========================================================
    # Demand reservations
    # ========================================================

    @api.post(
        "/api/v1/demands/{demand_id}/reserve",
        response_model=DemandPlanResponse,
        tags=["demands"],
    )
    def demand_reserve(
        demand_id: int,
    ):

        try:
            plan = (
                demand_service
                .reserve_available_stock(
                    demand_id
                )
            )

            return demand_plan_response(
                plan
            )

        except DemandNotFoundError as error:
            raise HTTPException(
                status_code=404,
                detail=str(error),
            ) from error

        except DemandMaterialNotFoundError as error:
            raise HTTPException(
                status_code=409,
                detail=str(error),
            ) from error

    @api.get(
        "/api/v1/demands/{demand_id}/reservations",
        response_model=list[
            StockReservationResponse
        ],
        tags=["demands"],
    )
    def demand_reservations(
        demand_id: int,
    ):

        try:
            reservations = (
                demand_service
                .list_reservations(
                    demand_id
                )
            )

            return [
                reservation_response(
                    reservation
                )
                for reservation
                in reservations
            ]

        except DemandNotFoundError as error:
            raise HTTPException(
                status_code=404,
                detail=str(error),
            ) from error

    # ========================================================
    # Resolve missing material
    # ========================================================

    @api.post(
        "/api/v1/demands/{demand_id}/missing-materials/resolve",
        response_model=MissingMaterialResolveResponse,
        status_code=201,
        tags=["demands"],
    )
    def demand_resolve_missing_material(
        demand_id: int,
        request: MissingMaterialResolveRequest,
    ):
        try:
            result = missing_material_service.resolve(
                demand_id=demand_id,
                code=request.code,
                name=request.name,
                quantity=request.quantity,
                unit=request.unit,
                minimum_quantity=request.minimum_quantity,
                required_quantity=request.required_quantity,
            )

            return MissingMaterialResolveResponse(
                material=material_response(
                    result.material
                ),
                requirement=requirement_response(
                    result.requirement
                ),
                plan=demand_plan_response(
                    result.plan
                ),
            )

        except DemandNotFoundError as error:
            raise HTTPException(
                status_code=404,
                detail=str(error),
            ) from error

        except MaterialAlreadyExistsError as error:
            raise HTTPException(
                status_code=409,
                detail=str(error),
            ) from error

        except DemandMaterialNotFoundError as error:
            raise HTTPException(
                status_code=409,
                detail=str(error),
            ) from error

        except MissingMaterialResolutionError as error:
            raise HTTPException(
                status_code=500,
                detail=str(error),
            ) from error

        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail=str(error),
            ) from error

    # ========================================================
    # Suppliers / Pricing Intelligence
    # ========================================================

    def supplier_response(supplier) -> SupplierResponse:
        return SupplierResponse(
            id=supplier.id,
            code=supplier.code,
            name=supplier.name,
            nif=supplier.nif,
            email=supplier.email,
            phone=supplier.phone,
            notes=supplier.notes,
            active=supplier.active,
            created_at=supplier.created_at,
            updated_at=supplier.updated_at,
        )

    def supplier_material_response(item) -> SupplierMaterialResponse:
        return SupplierMaterialResponse(
            id=item.id,
            supplier_id=item.supplier_id,
            material_code=item.material_code,
            material_name=item.material_name,
            unit=item.unit,
            unit_price=item.unit_price,
            lead_time_days=item.lead_time_days,
            minimum_order_quantity=item.minimum_order_quantity,
            updated_at=item.updated_at,
        )

    def material_quote_response(item) -> MaterialQuoteResponse:
        return MaterialQuoteResponse(
            supplier_id=item.supplier_id,
            supplier_code=item.supplier_code,
            supplier_name=item.supplier_name,
            material_code=item.material_code,
            material_name=item.material_name,
            unit=item.unit,
            requested_quantity=item.requested_quantity,
            order_quantity=item.order_quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
            lead_time_days=item.lead_time_days,
            minimum_order_quantity=item.minimum_order_quantity,
        )

    def purchase_quote_response(result) -> PurchaseQuoteResponse:
        return PurchaseQuoteResponse(
            demand_ids=result.demand_ids,
            demand_codes=result.demand_codes,
            total_materials=result.total_materials,
            options=[
                PurchaseSupplierOptionResponse(
                    supplier_id=option.supplier_id,
                    supplier_code=option.supplier_code,
                    supplier_name=option.supplier_name,
                    covered_materials=option.covered_materials,
                    total_materials=option.total_materials,
                    full_coverage=option.full_coverage,
                    total_estimated=option.total_estimated,
                    max_lead_time_days=option.max_lead_time_days,
                    items=[material_quote_response(item) for item in option.items],
                )
                for option in result.options
            ],
            best_supplier_id=result.best_supplier_id,
            best_supplier_name=result.best_supplier_name,
            best_total_estimated=result.best_total_estimated,
            best_mix_total=result.best_mix_total,
            best_mix=[material_quote_response(item) for item in result.best_mix],
            analysis=result.analysis,
        )

    @api.post("/api/v1/suppliers", response_model=SupplierResponse, status_code=201, tags=["suppliers"])
    def supplier_create(request: SupplierCreateRequest):
        try:
            return supplier_response(supplier_service.create_supplier(
                request.code, request.name, request.nif, request.email, request.phone, request.notes
            ))
        except SupplierAlreadyExistsError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @api.get("/api/v1/suppliers", response_model=list[SupplierResponse], tags=["suppliers"])
    def supplier_list(active_only: bool = False):
        return [supplier_response(item) for item in supplier_service.list_suppliers(active_only)]

    @api.get("/api/v1/suppliers/{supplier_id}", response_model=SupplierResponse, tags=["suppliers"])
    def supplier_get(supplier_id: int):
        try:
            return supplier_response(supplier_service.get_supplier(supplier_id))
        except SupplierNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @api.put("/api/v1/suppliers/{supplier_id}", response_model=SupplierResponse, tags=["suppliers"])
    def supplier_update(supplier_id: int, request: SupplierUpdateRequest):
        try:
            return supplier_response(supplier_service.update_supplier(
                supplier_id, request.name, request.nif, request.email, request.phone, request.notes
            ))
        except SupplierNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @api.put("/api/v1/suppliers/{supplier_id}/status", response_model=SupplierResponse, tags=["suppliers"])
    def supplier_status(supplier_id: int, request: SupplierStatusRequest):
        try:
            return supplier_response(supplier_service.set_active(supplier_id, request.active))
        except SupplierNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @api.get("/api/v1/suppliers/{supplier_id}/materials", response_model=list[SupplierMaterialResponse], tags=["suppliers"])
    def supplier_materials(supplier_id: int):
        try:
            return [supplier_material_response(item) for item in supplier_service.list_supplier_materials(supplier_id)]
        except SupplierNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @api.post("/api/v1/suppliers/{supplier_id}/materials", response_model=SupplierMaterialResponse, tags=["suppliers"])
    def supplier_material_upsert(supplier_id: int, request: SupplierMaterialUpsertRequest):
        try:
            return supplier_material_response(supplier_service.upsert_material(
                supplier_id,
                request.material_code,
                request.unit_price,
                request.lead_time_days,
                request.minimum_order_quantity,
            ))
        except (SupplierNotFoundError, MaterialNotFoundError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except SupplierCatalogError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @api.delete("/api/v1/suppliers/{supplier_id}/materials/{material_code}", tags=["suppliers"])
    def supplier_material_delete(supplier_id: int, material_code: str):
        try:
            supplier_service.remove_material(supplier_id, material_code)
            return {"deleted": True, "material_code": material_code}
        except (SupplierNotFoundError, MaterialNotFoundError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except SupplierCatalogError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @api.get("/api/v1/suppliers/{supplier_id}/materials/{material_code}/history", response_model=list[SupplierPriceHistoryResponse], tags=["suppliers"])
    def supplier_material_history(supplier_id: int, material_code: str):
        try:
            return [
                SupplierPriceHistoryResponse(
                    id=item.id,
                    supplier_id=item.supplier_id,
                    material_code=item.material_code,
                    unit_price=item.unit_price,
                    recorded_at=item.recorded_at,
                )
                for item in supplier_service.price_history(supplier_id, material_code)
            ]
        except (SupplierNotFoundError, MaterialNotFoundError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @api.get("/api/v1/supplier-quotes/materials/{material_code}", response_model=list[MaterialQuoteResponse], tags=["suppliers"])
    def supplier_material_quotes(material_code: str, quantity: float = Query(default=1, gt=0)):
        try:
            return [material_quote_response(item) for item in supplier_service.compare_material(material_code, quantity)]
        except MaterialNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @api.post("/api/v1/procurement/quotes", response_model=PurchaseQuoteResponse, tags=["procurement"])
    def procurement_quotes(request: PurchaseQuoteRequest):
        try:
            return purchase_quote_response(supplier_service.quote_purchase(request.demand_ids))
        except DemandNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    # ========================================================
    # Procurement / Purchase lists
    # ========================================================
    @api.get("/api/v1/demands/{demand_id}/purchase-list",response_model=PurchaseListResponse,tags=["procurement"])
    def demand_purchase_list(demand_id:int):
        try: return purchase_list_response(procurement_service.for_demand(demand_id))
        except DemandNotFoundError as error: raise HTTPException(status_code=404,detail=str(error)) from error

    @api.post("/api/v1/procurement/consolidated",response_model=PurchaseListResponse,tags=["procurement"])
    def consolidated_purchase_list(request:ConsolidatedPurchaseListRequest):
        try: return purchase_list_response(procurement_service.consolidated(request.demand_ids))
        except DemandNotFoundError as error: raise HTTPException(status_code=404,detail=str(error)) from error

    # ========================================================
    # Purchase Orders / Receiving
    # ========================================================

    @api.post(
        "/api/v1/procurement/orders",
        response_model=PurchaseOrderResponse,
        status_code=201,
        tags=["procurement"],
    )
    def create_purchase_order(request: PurchaseOrderCreateRequest):
        try:
            return purchase_order_response(
                purchase_order_service.create(
                    request.demand_ids,
                    request.notes,
                    request.supplier_id,
                )
            )
        except DemandNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except PurchaseOrderDuplicateError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except SupplierCatalogError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except SupplierNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @api.get(
        "/api/v1/procurement/orders",
        response_model=list[PurchaseOrderResponse],
        tags=["procurement"],
    )
    def list_purchase_orders():
        return [purchase_order_response(order) for order in purchase_order_service.list_orders()]

    @api.get(
        "/api/v1/procurement/orders/{order_id}",
        response_model=PurchaseOrderResponse,
        tags=["procurement"],
    )
    def get_purchase_order(order_id: int):
        try:
            return purchase_order_response(purchase_order_service.get(order_id))
        except PurchaseOrderNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @api.post(
        "/api/v1/procurement/orders/{order_id}/mark-ordered",
        response_model=PurchaseOrderResponse,
        tags=["procurement"],
    )
    def mark_purchase_order_ordered(order_id: int):
        try:
            return purchase_order_response(purchase_order_service.mark_ordered(order_id))
        except PurchaseOrderNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except PurchaseOrderStateError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @api.post(
        "/api/v1/procurement/orders/{order_id}/cancel",
        response_model=PurchaseOrderResponse,
        tags=["procurement"],
    )
    def cancel_purchase_order(order_id: int):
        try:
            return purchase_order_response(purchase_order_service.cancel(order_id))
        except PurchaseOrderNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except PurchaseOrderStateError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @api.post(
        "/api/v1/procurement/orders/{order_id}/items/{item_id}/receive",
        response_model=PurchaseOrderResponse,
        tags=["procurement"],
    )
    def receive_purchase_order_item(
        order_id: int,
        item_id: int,
        request: PurchaseOrderReceiveRequest,
    ):
        try:
            return purchase_order_response(
                purchase_order_service.receive(order_id, item_id, request.quantity)
            )
        except PurchaseOrderNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except PurchaseOrderStateError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    # ========================================================
    # Demand quantity map import
    # ========================================================

    @api.post(
        "/api/v1/demands/{demand_id}/quantity-map/import",
        response_model=(
            QuantityMapImportResponse
        ),
        tags=["demands"],
    )
    async def demand_quantity_map_import(
        demand_id: int,
        file: UploadFile = File(...),
    ):

        filename = (
            file.filename
            or "mapa_quantidades.xlsx"
        )

        if not filename.lower().endswith(
            ".xlsx"
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "O mapa de quantidades deve "
                    "estar no formato .xlsx."
                ),
            )

        try:
            demand_service.get_demand(
                demand_id
            )

        except DemandNotFoundError as error:
            raise HTTPException(
                status_code=404,
                detail=str(error),
            ) from error

        suffix = Path(
            filename
        ).suffix

        temporary_path = None

        try:
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            ) as temporary_file:

                temporary_path = Path(
                    temporary_file.name
                )

                shutil.copyfileobj(
                    file.file,
                    temporary_file,
                )

            result = (
                quantity_map_importer
                .import_file(
                    demand_id,
                    temporary_path,
                )
            )

            return QuantityMapImportResponse(
                filename=filename,
                demand_id=demand_id,
                total_rows=(
                    result.total_rows
                ),
                imported=(
                    result.imported
                ),
                skipped=(
                    result.skipped
                ),
                missing_materials=[
                    QuantityMapMissingMaterialResponse(
                        row=item.row,
                        code=item.code,
                        name=item.name,
                        quantity=(
                            item.quantity
                        ),
                        unit=item.unit,
                    )
                    for item
                    in result.missing_materials
                ],
                errors=result.errors,
            )

        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail=str(error),
            ) from error

        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=(
                    "NÃƒÂ£o foi possÃƒÂ­vel importar "
                    "o mapa de quantidades: "
                    f"{error}"
                ),
            ) from error

        finally:
            await file.close()

            if (
                temporary_path
                is not None
                and temporary_path.exists()
            ):
                temporary_path.unlink(
                    missing_ok=True
                )

    # ========================================================
    # Material Requests - Etapa 23
    # ========================================================

    api.include_router(
        create_material_request_router(DATABASE_PATH)
    )

    return api


app = create_app()


