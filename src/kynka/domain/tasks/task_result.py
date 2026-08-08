"""
Resultado de processamento de uma Task.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class TaskResult:
    """
    Resultado final produzido pelo processamento de uma Task.
    """

    task_id: UUID

    success: bool

    data: Any = None

    error: str | None = None

    capability: str | None = None