"""
Executor agêntico da plataforma Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kynka.application.argument_extractor import (
    ArgumentExtractionError,
)
from kynka.application.hybrid_argument_extractor import (
    HybridArgumentExtractor,
)
from kynka.application.intent_router import (
    HybridIntentRouter,
    IntentNotFoundError,
)
from kynka.domain.capabilities import CapabilityResult
from kynka.kernel.runtime import Runtime


class AgentExecutionError(Exception):
    """
    Erro ocorrido durante a execução agêntica.
    """


@dataclass(slots=True)
class AgentExecutionResult:
    """
    Resultado completo de uma execução agêntica.
    """

    success: bool
    text: str
    capability: str | None = None
    arguments: dict[str, Any] | None = None
    result: Any = None
    error: str | None = None


class AgentExecutor:
    """
    Coordena seleção de Capability,
    extração de argumentos e execução.
    """

    def __init__(
        self,
        runtime: Runtime,
        router: HybridIntentRouter,
        argument_extractor: HybridArgumentExtractor,
    ) -> None:
        self._runtime = runtime
        self._router = router
        self._argument_extractor = argument_extractor

    def execute(
        self,
        text: str,
    ) -> AgentExecutionResult:

        text = text.strip()

        if not text:
            return AgentExecutionResult(
                success=False,
                text=text,
                error="A solicitação não pode estar vazia.",
            )

        capability_catalog = (
            self._build_capability_catalog()
        )

        try:
            route = self._router.route(
                text=text,
                available_capabilities=capability_catalog,
            )

        except IntentNotFoundError as error:
            return AgentExecutionResult(
                success=False,
                text=text,
                error=str(error),
            )

        try:
            capability = (
                self._runtime.registry.get_capability(
                    route.capability
                )
            )

        except Exception as error:
            return AgentExecutionResult(
                success=False,
                text=text,
                capability=route.capability,
                error=str(error),
            )

        parameters = {
            parameter.name: parameter.description
            for parameter
            in capability.metadata.parameters
        }

        try:
            arguments = (
                self._argument_extractor.extract(
                    text=text,
                    capability=capability.name,
                    parameters=parameters,
                )
            )

        except Exception as error:
            return AgentExecutionResult(
                success=False,
                text=text,
                capability=capability.name,
                error=str(error),
            )

        try:
            execution_result = (
                self._runtime.execute(
                    capability.name,
                    **arguments,
                )
            )

        except Exception as error:
            return AgentExecutionResult(
                success=False,
                text=text,
                capability=capability.name,
                arguments=arguments,
                error=str(error),
            )

        if isinstance(
            execution_result,
            CapabilityResult,
        ):
            return AgentExecutionResult(
                success=execution_result.success,
                text=text,
                capability=capability.name,
                arguments=arguments,
                result=execution_result.data,
                error=execution_result.error,
            )

        return AgentExecutionResult(
            success=True,
            text=text,
            capability=capability.name,
            arguments=arguments,
            result=execution_result,
        )

    def _build_capability_catalog(
        self,
    ) -> dict[str, str]:

        return {
            name: capability.metadata.description
            for name, capability
            in self._runtime.registry.capabilities.items()
        }