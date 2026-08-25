from __future__ import annotations

import shutil
import tempfile
from contextlib import asynccontextmanager
from datetime import date
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

from kynka.application.inventory import (
    InsufficientStockError,
    InventoryService,
    MaterialAlreadyExistsError,
    MaterialNotFoundError,
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

    DATA_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

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

    api.state.inventory_service = (
        inventory_service
    )

    api.state.demand_service = (
        demand_service
    )

    api.state.missing_material_service = (
        missing_material_service
    )

    api.state.quantity_map_importer = (
        quantity_map_importer
    )

    # ========================================================
    # CORS
    # ========================================================

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
                    "SessÃ£o nÃ£o encontrada."
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
                    "SessÃ£o nÃ£o encontrada."
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
                    "SessÃ£o nÃ£o encontrada."
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
                    "SessÃ£o nÃ£o encontrada."
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
                    "Arquivo invÃ¡lido. "
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
                    "Tipo de movimentaÃ§Ã£o invÃ¡lido."
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
                            "Data inicial invÃ¡lida. "
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
                    "NÃ£o foi possÃ­vel importar "
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

    return api


app = create_app()
