"""
Fachada principal da plataforma Kynka.
"""

from __future__ import annotations

from kynka.application.agent import (
    AgentExecutionResult,
    AgentExecutor,
)
from kynka.application.argument_extractor import (
    ArgumentExtractor,
)
from kynka.application.hybrid_argument_extractor import (
    HybridArgumentExtractor,
)
from kynka.application.intent_router import (
    HybridIntentRouter,
    IntentRouter,
    LLMIntentRouter,
)
from kynka.application.plugin_installer import (
    PluginInstaller,
)
from kynka.domain.plugins.plugin import Plugin
from kynka.infrastructure.providers import OllamaProvider
from kynka.kernel.runtime import Runtime


class Kynka:
    """
    Fachada principal da plataforma Kynka.

    Centraliza:
    - Runtime;
    - Provider;
    - roteamento;
    - extração de argumentos;
    - instalação de Plugins;
    - execução agêntica.
    """

    def __init__(
        self,
        model: str = "llama3.2:3b",
    ) -> None:
        self._runtime = Runtime()

        self._provider = OllamaProvider(
            model=model
        )

        self._argument_extractor = (
            HybridArgumentExtractor(
                ArgumentExtractor(
                    self._provider
                )
            )
        )

        self._router = HybridIntentRouter(
            deterministic_router=IntentRouter(),
            llm_router=LLMIntentRouter(
                self._provider
            ),
        )

        self._installer = PluginInstaller(
            runtime=self._runtime,
            argument_extractor=(
                self._argument_extractor
            ),
        )

        self._agent = AgentExecutor(
            runtime=self._runtime,
            router=self._router,
            argument_extractor=(
                self._argument_extractor
            ),
        )

    def start(self) -> None:
        """
        Inicia a plataforma.
        """

        self._runtime.start()

    def stop(self) -> None:
        """
        Finaliza a plataforma.
        """

        self._runtime.stop()

    def install(
        self,
        plugin: Plugin,
    ) -> None:
        """
        Instala um Plugin na plataforma.
        """

        self._installer.install(
            plugin
        )

    def execute(
        self,
        text: str,
    ) -> AgentExecutionResult:
        """
        Executa uma solicitação em linguagem natural.
        """

        if not self._runtime.is_running:
            raise RuntimeError(
                "A plataforma Kynka não está iniciada."
            )

        return self._agent.execute(
            text
        )

    @property
    def runtime(self) -> Runtime:
        """
        Expõe o Runtime para inspeção.
        """

        return self._runtime

    @property
    def plugins(self) -> tuple[str, ...]:
        """
        Retorna os Plugins instalados.
        """

        return tuple(
            self._runtime.registry.plugins.keys()
        )

    @property
    def capabilities(self) -> tuple[str, ...]:
        """
        Retorna as Capabilities disponíveis.
        """

        return tuple(
            self._runtime.registry.capabilities.keys()
        )

    @property
    def model(self) -> str:
        """
        Retorna o modelo configurado no Provider.
        """

        return self._provider.model