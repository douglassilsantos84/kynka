"""
Resultado de execução de uma Capability.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CapabilityResult:

    success: bool

    data: Any = None

    error: str | None = None