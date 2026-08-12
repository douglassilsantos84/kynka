from __future__ import annotations
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any
from kynka.application.planning import PlanExecutionResult

def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(v) for v in value]
    return str(value)

def serialize_execution(session_id: str, result: Any) -> dict[str, Any]:
    if isinstance(result, PlanExecutionResult):
        return {
            "session_id": session_id, "success": result.success, "mode": "plan",
            "result": json_safe(result.result), "error": result.error,
            "capability": None, "arguments": None,
            "steps": [{
                "step_id": s.step_id, "capability": s.capability,
                "arguments": json_safe(s.arguments), "success": s.success,
                "result": json_safe(s.result), "error": s.error,
            } for s in result.steps],
        }
    return {
        "session_id": session_id, "success": result.success, "mode": "simple",
        "result": json_safe(result.result), "error": result.error,
        "capability": result.capability, "arguments": json_safe(result.arguments),
        "steps": [],
    }
