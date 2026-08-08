"""
Plugin Loader da plataforma Kynka.
"""

from __future__ import annotations

from typing import Iterable

from kynka.domain.plugins.plugin import Plugin
from kynka.kernel.registry import Registry


class PluginLoader:
    """
    Responsável por carregar Plugins no Registry.
    """

    def __init__(
        self,
        registry: Registry,
    ) -> None:

        self._registry = registry

    def load(
        self,
        plugin: Plugin,
    ) -> None:

        self._registry.register_plugin(plugin)

    def load_many(
        self,
        plugins: Iterable[Plugin],
    ) -> None:

        for plugin in plugins:

            self.load(plugin)