"""
Resposta produzida por um Provider da Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ProviderResponse:
    """
    Resultado padronizado retornado por um Provider.
    """

    success: bool

    content: str | None = None

    error: str | None = None

    metadata: dict[str, Any] | None = None