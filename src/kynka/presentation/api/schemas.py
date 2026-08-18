from __future__ import annotations

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