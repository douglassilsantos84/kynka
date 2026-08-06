"""
Contrato base para plugins da plataforma Kynka.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from kynka.domain.capabilities import Capability


@dataclass(slots=True)
class PluginMetadata:
    """
    Metadados de um Plugin.
    """

    name: str
    version: str
    description: str
    author: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)


class Plugin(ABC):
    """
    Contrato base de todos os plugins.
    """

    def __init__(
        self,
        metadata: PluginMetadata,
    ) -> None:

        self._metadata = metadata

        self._loaded = False

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    @abstractmethod
    def capabilities(self) -> list[Capability]:
        """
        Lista de Capabilities fornecidas pelo plugin.
        """
        ...

    def load(self) -> None:

        if self._loaded:
            return

        self.on_load()

        self._loaded = True

    def unload(self) -> None:

        if not self._loaded:
            return

        self.on_unload()

        self._loaded = False

    def on_load(self) -> None:
        """
        Executado quando o plugin é carregado.
        """

    def on_unload(self) -> None:
        """
        Executado quando o plugin é descarregado.
        """

    def execute(self, **kwargs: Any) -> Any:
        """
        Mantido temporariamente por compatibilidade.

        Será removido na versão 1.0.
        """
        raise NotImplementedError(
            "Use uma Capability em vez de executar o Plugin diretamente."
        )