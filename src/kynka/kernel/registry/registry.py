"""
Registro central de componentes da plataforma Kynka.
"""

from __future__ import annotations

from typing import Any

from kynka.domain.plugins.plugin import Plugin


class RegistryError(Exception):
    """
    Erro base do Registry.
    """


class ComponentAlreadyRegisteredError(RegistryError):
    """
    Componente já registrado.
    """


class ComponentNotFoundError(RegistryError):
    """
    Componente não encontrado.
    """


class Registry:
    """
    Registro central de providers, capabilities e plugins.
    """

    def __init__(self) -> None:
        self._providers: dict[str, Any] = {}
        self._capabilities: dict[str, Any] = {}
        self._plugins: dict[str, Plugin] = {}

    def register_provider(
        self,
        name: str,
        provider: Any,
        *,
        replace: bool = False,
    ) -> None:
        self._register(
            collection=self._providers,
            name=name,
            component=provider,
            replace=replace,
        )

    def get_provider(self, name: str) -> Any:
        return self._get(
            collection=self._providers,
            name=name,
            component_type="Provider",
        )

    def register_capability(
        self,
        name: str,
        capability: Any,
        *,
        replace: bool = False,
    ) -> None:
        self._register(
            collection=self._capabilities,
            name=name,
            component=capability,
            replace=replace,
        )

    def get_capability(self, name: str) -> Any:
        return self._get(
            collection=self._capabilities,
            name=name,
            component_type="Capability",
        )

    def register_plugin(
        self,
        plugin: Plugin,
        *,
        replace: bool = False,
    ) -> None:
        self._register(
            collection=self._plugins,
            name=plugin.name,
            component=plugin,
            replace=replace,
        )

        plugin.load()

    def get_plugin(self, name: str) -> Plugin:
        plugin = self._get(
            collection=self._plugins,
            name=name,
            component_type="Plugin",
        )

        if not isinstance(plugin, Plugin):
            raise TypeError(
                f"O componente '{name}' não implementa o contrato Plugin."
            )

        return plugin

    def unload_plugins(self) -> None:
        for plugin in self._plugins.values():
            plugin.unload()

    @property
    def providers(self) -> dict[str, Any]:
        return dict(self._providers)

    @property
    def capabilities(self) -> dict[str, Any]:
        return dict(self._capabilities)

    @property
    def plugins(self) -> dict[str, Plugin]:
        return dict(self._plugins)

    @staticmethod
    def _register(
        collection: dict[str, Any],
        name: str,
        component: Any,
        replace: bool,
    ) -> None:
        normalized_name = name.strip().lower()

        if not normalized_name:
            raise ValueError("O nome do componente não pode ficar vazio.")

        if normalized_name in collection and not replace:
            raise ComponentAlreadyRegisteredError(
                f"O componente '{normalized_name}' já está registrado."
            )

        collection[normalized_name] = component

    @staticmethod
    def _get(
        collection: dict[str, Any],
        name: str,
        component_type: str,
    ) -> Any:
        normalized_name = name.strip().lower()

        try:
            return collection[normalized_name]
        except KeyError as error:
            raise ComponentNotFoundError(
                f"{component_type} '{normalized_name}' não encontrado."
            ) from error