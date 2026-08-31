from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from kynka.application.demand import (
    DemandNotFoundError,
    DemandService,
)
from kynka.application.inventory import (
    InventoryService,
    MaterialNotFoundError,
)
from kynka.application.material_requests import (
    MaterialRequestService,
)
from kynka.infrastructure.demand import (
    SQLiteDemandRepository,
)
from kynka.infrastructure.inventory import (
    SQLiteInventoryRepository,
)
from kynka.infrastructure.material_requests import (
    SQLiteMaterialRequestRepository,
)


class MaterialRequestItemIn(BaseModel):
    material_code: str
    quantity: float = Field(gt=0)


class MaterialRequestCreateIn(BaseModel):
    demand_id: int
    requester_name: str
    priority: str = "normal"
    notes: str = ""
    items: list[MaterialRequestItemIn]


class MaterialRequestTransitionIn(BaseModel):
    status: str
    actor: str = ""
    notes: str = ""


class MaterialRequestActionIn(BaseModel):
    actor: str = ""
    notes: str = ""


def create_material_request_router(
    database_path: str | Path,
) -> APIRouter:
    request_repository = SQLiteMaterialRequestRepository(
        database_path
    )
    demand_repository = SQLiteDemandRepository(
        database_path
    )
    inventory_repository = SQLiteInventoryRepository(
        database_path
    )

    demand_service = DemandService(
        demand_repository,
        inventory_repository,
    )
    inventory_service = InventoryService(
        inventory_repository
    )

    service = MaterialRequestService(
        request_repository,
        demand_service,
        demand_repository,
        inventory_service,
    )

    router = APIRouter(
        prefix="/api/v1/material-requests",
        tags=["material-requests"],
    )

    def execute(action):
        try:
            return action()
        except DemandNotFoundError as error:
            raise HTTPException(
                status_code=404,
                detail=str(error),
            ) from error
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

    @router.get("")
    def list_requests(
        status: str | None = None,
        demand_id: int | None = None,
    ):
        return execute(
            lambda: service.list(
                status=status,
                demand_id=demand_id,
            )
        )

    @router.get("/summary")
    def summary():
        return service.summary()

    @router.get("/{request_id}")
    def get_request(request_id: int):
        return execute(
            lambda: service.get(request_id)
        )

    @router.post("", status_code=201)
    def create_request(
        payload: MaterialRequestCreateIn,
    ):
        return execute(
            lambda: service.create(
                demand_id=payload.demand_id,
                requester=payload.requester_name,
                items=[
                    item.model_dump()
                    for item in payload.items
                ],
                priority=payload.priority,
                notes=payload.notes,
            )
        )

    @router.post("/{request_id}/transition")
    def transition(
        request_id: int,
        payload: MaterialRequestTransitionIn,
    ):
        return execute(
            lambda: service.transition(
                request_id=request_id,
                status=payload.status,
                actor=payload.actor,
                notes=payload.notes,
            )
        )

    @router.post("/{request_id}/separate")
    def separate(
        request_id: int,
        payload: MaterialRequestActionIn,
    ):
        return execute(
            lambda: service.separate(
                request_id=request_id,
                actor=payload.actor,
                notes=payload.notes,
            )
        )

    @router.post("/{request_id}/deliver")
    def deliver(
        request_id: int,
        payload: MaterialRequestActionIn,
    ):
        return execute(
            lambda: service.deliver(
                request_id=request_id,
                actor=payload.actor,
                notes=payload.notes,
            )
        )

    return router
