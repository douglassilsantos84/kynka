from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class SessionCreateResponse(BaseModel):
    session_id: str

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
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
    steps: list[StepResponse] = Field(default_factory=list)

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

class CapabilityResponse(BaseModel):
    name: str
    description: str
    version: str | None = None

class StatusResponse(BaseModel):
    status: Literal["ok"]
    version: str
    model: str
    sessions: int

class HealthResponse(BaseModel):
    status: Literal["ok"]
