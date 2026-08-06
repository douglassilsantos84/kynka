"""
Registry central da plataforma Kynka.
"""

from __future__ import annotations

from typing import Dict

from kynka.domain.capabilities import Capability
from kynka.domain.plugins.plugin import Plugin


class Registry:
    """
    Registro central da plataforma.

    Mantém Plugins e Capabilities registradas.
    """

    def __init__(self) -> None:

        self._plugins: Dict[str, Plugin] = {}

        self._capabilities: Dict[str, Capability] = {}

    # --------------------------------------------------
    # Plugins
    # --------------------------------------------------

    def register_plugin(
        self,
        plugin: Plugin,
    ) -> None:

        self._plugins[plugin.name] = plugin

        plugin.load()

        for capability in plugin.capabilities:

            self.register_capability(capability)

    def get_plugin(
        self,
        name: str,
    ) -> Plugin:

        return self._plugins[name]

    @property
    def plugins(self) -> Dict[str, Plugin]:

        return dict(self._plugins)

    # --------------------------------------------------
    # Capabilities
    # --------------------------------------------------

    def register_capability(
        self,
        capability: Capability,
    ) -> None:

        self._capabilities[
            capability.name
        ] = capability

    def get_capability(
        self,
        name: str,
    ) -> Capability:

        return self._capabilities[name]

    @property
    def capabilities(self) -> Dict[str, Capability]:

        return dict(self._capabilities)

    # --------------------------------------------------

    def unload_plugins(self) -> None:

        for plugin in self._plugins.values():

            plugin.unload()