"""
Executor de Capabilities.
"""

from __future__ import annotations

from typing import Any

from kynka.application.capability_registry import CapabilityRegistry


class CapabilityExecutor:
    """
    Executa Capabilities registradas.
    """

    def __init__(
        self,
        registry: CapabilityRegistry,
    ) -> None:

        self._registry = registry

    def execute(
        self,
        capability: str,
        **kwargs: Any,
    ) -> Any:

        plugin = self._registry.get(capability)

        return plugin.execute(**kwargs)