from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ============================================================
# Sessions
# ============================================================


class SessionCreateResponse(BaseModel):
    session_id: str


# ============================================================
# Chat
# ============================================================


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=10000,
    )
    session_id: str | None = None


class StepResponse(BaseModel):
    step_id: str
    capability: str
    arguments: dict[str, Any]
    success: bool
    result: Any = None
    error: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    success: bool
    mode: Literal["simple", "plan"]
    result: Any = None
    error: str | None = None
    capability: str | None = None
    arguments: dict[str, Any] | None = None
    steps: list[StepResponse] = Field(
        default_factory=list
    )


# ============================================================
# Memory
# ============================================================


class MemoryRecordResponse(BaseModel):
    text: str
    success: bool
    capability: str | None = None
    arguments: dict[str, Any] | None = None
    result: Any = None
    error: str | None = None
    operational: bool = True


class MemoryResponse(BaseModel):
    session_id: str
    records: list[MemoryRecordResponse]


class VariablesResponse(BaseModel):
    session_id: str
    variables: dict[str, Any]


# ============================================================
# Capabilities
# ============================================================


class CapabilityResponse(BaseModel):
    name: str
    description: str
    version: str | None = None


# ============================================================
# System
# ============================================================


class StatusResponse(BaseModel):
    status: Literal["ok"]
    version: str
    model: str
    sessions: int


class HealthResponse(BaseModel):
    status: Literal["ok"]


# ============================================================
# Inventory
# ============================================================


class MaterialCreateRequest(BaseModel):
    code: str = Field(
        min_length=1,
        max_length=100,
    )
    name: str = Field(
        min_length=1,
        max_length=300,
    )
    quantity: float = Field(
        default=0,
        ge=0,
    )
    unit: str = Field(
        default="un",
        max_length=50,
    )
    minimum_quantity: float = Field(
        default=0,
        ge=0,
    )


class MaterialUpdateRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=300,
    )
    unit: str = Field(
        default="un",
        max_length=50,
    )
    minimum_quantity: float = Field(
        default=0,
        ge=0,
    )


class MaterialResponse(BaseModel):
    code: str
    name: str
    quantity: float
    unit: str
    minimum_quantity: float
    below_minimum: bool


class InventorySummaryResponse(BaseModel):
    total_materials: int
    below_minimum: int
    zero_stock: int


class InventoryImportResponse(BaseModel):
    filename: str
    imported: int
    skipped: int
    errors: list[str] = Field(
        default_factory=list
    )
    summary: InventorySummaryResponse


class InventoryMovementRequest(BaseModel):
    type: Literal[
        "entry",
        "exit",
        "adjustment",
    ]

    quantity: float = Field(
        ge=0,
    )

    reason: str = Field(
        default="",
        max_length=500,
    )


class InventoryMovementResponse(BaseModel):
    id: int
    material_code: str

    type: Literal[
        "entry",
        "exit",
        "adjustment",
    ]

    quantity: float
    previous_quantity: float
    new_quantity: float
    reason: str
    created_at: datetime

# ============================================================
# Demands / Projects
# ============================================================


class DemandCreateRequest(BaseModel):
    code: str = Field(
        min_length=1,
        max_length=100,
    )

    name: str = Field(
        min_length=1,
        max_length=300,
    )

    kind: str = Field(
        default="project",
        min_length=1,
        max_length=100,
    )

    client: str = Field(
        default="",
        max_length=300,
    )

    location: str = Field(
        default="",
        max_length=500,
    )

    start_date: str | None = None

    notes: str = Field(
        default="",
        max_length=2000,
    )


class DemandResponse(BaseModel):
    id: int
    code: str
    name: str
    kind: str
    client: str
    location: str
    start_date: str | None = None
    status: str
    notes: str
    created_at: datetime | None = None


class DemandRequirementRequest(BaseModel):
    material_code: str = Field(
        min_length=1,
        max_length=100,
    )

    required_quantity: float = Field(
        gt=0,
    )


class DemandRequirementResponse(BaseModel):
    id: int
    demand_id: int
    material_code: str
    required_quantity: float


class StockReservationResponse(BaseModel):
    id: int
    demand_id: int
    material_code: str
    quantity: float
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DemandPlanItemResponse(BaseModel):
    material_code: str
    material_name: str
    unit: str

    required_quantity: float

    physical_quantity: float
    minimum_quantity: float

    reserved_total: float
    reserved_for_this_demand: float
    reserved_for_other_demands: float

    free_quantity: float

    quantity_still_required: float
    quantity_available_to_reserve: float

    shortage_quantity: float

    fully_available: bool


class DemandPlanResponse(BaseModel):
    demand_id: int
    demand_code: str
    demand_name: str

    total_items: int
    available_items: int
    shortage_items: int

    items: list[DemandPlanItemResponse] = Field(
        default_factory=list
    )

# ============================================================
# Quantity Map Import
# ============================================================


class QuantityMapMissingMaterialResponse(BaseModel):
    row: int
    code: str
    name: str
    quantity: float
    unit: str


class QuantityMapImportResponse(BaseModel):
    filename: str
    demand_id: int

    total_rows: int
    imported: int
    skipped: int

    missing_materials: list[
        QuantityMapMissingMaterialResponse
    ] = Field(default_factory=list)

    errors: list[str] = Field(
        default_factory=list
    )


# ============================================================
# Missing material resolution
# ============================================================


class MissingMaterialResolveRequest(BaseModel):
    code: str = Field(
        min_length=1,
        max_length=100,
    )
    name: str = Field(
        min_length=1,
        max_length=300,
    )
    quantity: float = Field(
        default=0,
        ge=0,
    )
    unit: str = Field(
        default="un",
        min_length=1,
        max_length=50,
    )
    minimum_quantity: float = Field(
        default=0,
        ge=0,
    )
    required_quantity: float = Field(
        gt=0,
    )


class MissingMaterialResolveResponse(BaseModel):
    material: MaterialResponse
    requirement: DemandRequirementResponse
    plan: DemandPlanResponse


# ============================================================
# Procurement / Purchase lists
# ============================================================
class PurchaseDemandShareResponse(BaseModel):
    demand_id:int; demand_code:str; demand_name:str
    required_quantity:float; reserved_quantity:float; remaining_quantity:float
class PurchaseListItemResponse(BaseModel):
    material_code:str; material_name:str; unit:str
    required_quantity:float; reserved_quantity:float
    physical_quantity:float; minimum_quantity:float; reserved_total:float; free_quantity:float
    quantity_to_buy:float
    demands:list[PurchaseDemandShareResponse]=Field(default_factory=list)
class PurchaseListResponse(BaseModel):
    demand_ids:list[int]=Field(default_factory=list); demand_codes:list[str]=Field(default_factory=list)
    total_materials:int; materials_to_buy:int
    items:list[PurchaseListItemResponse]=Field(default_factory=list)
    analysis:str
class ConsolidatedPurchaseListRequest(BaseModel):
    demand_ids:list[int]|None=None


# ============================================================
# Purchase Orders / Receiving
# ============================================================


class PurchaseOrderCreateRequest(BaseModel):
    demand_ids: list[int] | None = None
    notes: str = Field(default="", max_length=2000)


class PurchaseOrderReceiveRequest(BaseModel):
    quantity: float = Field(gt=0)


class PurchaseOrderItemResponse(BaseModel):
    id: int
    material_code: str
    material_name: str
    unit: str
    quantity_ordered: float
    quantity_received: float
    quantity_pending: float


class PurchaseOrderResponse(BaseModel):
    id: int
    status: str
    demand_ids: list[int] = Field(default_factory=list)
    demand_codes: list[str] = Field(default_factory=list)
    notes: str
    created_at: str
    ordered_at: str | None = None
    completed_at: str | None = None
    items: list[PurchaseOrderItemResponse] = Field(default_factory=list)
