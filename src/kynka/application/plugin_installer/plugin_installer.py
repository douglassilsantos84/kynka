"""
Instalação de Plugins na plataforma Kynka.
"""

from __future__ import annotations

from kynka.application.hybrid_argument_extractor import (
    HybridArgumentExtractor,
)
from kynka.domain.plugins.plugin import Plugin
from kynka.kernel.runtime import Runtime


class PluginInstallationError(Exception):
    """
    Erro ocorrido durante a instalação de um Plugin.
    """


class PluginInstaller:
    """
    Coordena a instalação de Plugins nos subsistemas
    da plataforma Kynka.
    """

    def __init__(
        self,
        runtime: Runtime,
        argument_extractor: HybridArgumentExtractor,
    ) -> None:
        self._runtime = runtime
        self._argument_extractor = argument_extractor

    def install(
        self,
        plugin: Plugin,
    ) -> None:
        """
        Instala um Plugin na plataforma.

        A instalação registra:
        - o Plugin no Runtime;
        - suas Capabilities no Registry;
        - suas estratégias específicas de extração.
        """

        try:
            self._runtime.register_plugin(
                plugin
            )

            self._argument_extractor.register_plugin(
                plugin
            )

        except Exception as error:
            raise PluginInstallationError(
                f"Não foi possível instalar "
                f"o Plugin '{plugin.name}'."
            ) from error