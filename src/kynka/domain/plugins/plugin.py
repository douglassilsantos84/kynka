"""
Contratos de plugins da plataforma Kynka.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PluginMetadata:
    """
    Metadados descritivos de um plugin.
    """

    name: str
    version: str
    description: str
    author: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)


class Plugin(ABC):
    """
    Contrato base para todos os plugins da plataforma Kynka.
    """

    def __init__(self, metadata: PluginMetadata) -> None:
        self._metadata = metadata
        self._loaded = False

    @property
    def metadata(self) -> PluginMetadata:
        """
        Retorna os metadados do plugin.
        """
        return self._metadata

    @property
    def name(self) -> str:
        """
        Retorna o nome único do plugin.
        """
        return self._metadata.name

    @property
    def is_loaded(self) -> bool:
        """
        Indica se o plugin foi carregado.
        """
        return self._loaded

    def load(self) -> None:
        """
        Carrega o plugin.
        """
        if self._loaded:
            return

        self.on_load()
        self._loaded = True

    def unload(self) -> None:
        """
        Descarrega o plugin.
        """
        if not self._loaded:
            return

        self.on_unload()
        self._loaded = False

    def on_load(self) -> None:
        """
        Executado durante o carregamento do plugin.

        Pode ser sobrescrito por plugins concretos.
        """

    def on_unload(self) -> None:
        """
        Executado durante o encerramento do plugin.

        Pode ser sobrescrito por plugins concretos.
        """

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """
        Executa a funcionalidade principal do plugin.
        """
        raise NotImplementedError