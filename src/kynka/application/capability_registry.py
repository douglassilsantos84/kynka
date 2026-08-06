"""
Registro de Capabilities da plataforma.
"""

from __future__ import annotations

from typing import Any

from kynka.domain.plugins.plugin import Plugin


class CapabilityRegistry:
    """
    Responsável por registrar
    qual Plugin executa determinada Capability.
    """

    def __init__(self) -> None:

        self._capabilities: dict[str, Plugin] = {}

    def register(
        self,
        capability: str,
        plugin: Plugin,
    ) -> None:

        capability = capability.strip().lower()

        self._capabilities[capability] = plugin

    def get(
        self,
        capability: str,
    ) -> Plugin:

        capability = capability.strip().lower()

        return self._capabilities[capability]

    @property
    def capabilities(self) -> dict[str, Plugin]:

        return dict(self._capabilities)