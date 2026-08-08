"""
Executor agêntico da plataforma Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kynka.application.context import (
    ContextResolutionError,
    ContextResolver,
)
from kynka.application.intent_router import (
    IntentNotFoundError,
)
from kynka.application.memory import (
    ExecutionMemory,
    ExecutionRecord,
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
    Coordena contexto, roteamento, extração
    de argumentos, execução e memória.
    """

    def __init__(
        self,
        runtime: Runtime,
        router: Any,
        argument_extractor: Any,
        memory: ExecutionMemory | None = None,
    ) -> None:
        self._runtime = runtime
        self._router = router
        self._argument_extractor = argument_extractor

        self._memory = (
            memory
            if memory is not None
            else ExecutionMemory()
        )

        self._context_resolver = ContextResolver(
            self._memory
        )

    @property
    def memory(self) -> ExecutionMemory:
        """
        Retorna a memória utilizada pelo agente.
        """

        return self._memory

    def execute(
        self,
        text: str,
    ) -> AgentExecutionResult:
        """
        Executa uma solicitação em linguagem natural.
        """

        original_text = text.strip()

        if not original_text:
            return self._finish(
                AgentExecutionResult(
                    success=False,
                    text=original_text,
                    error=(
                        "A solicitação não pode "
                        "estar vazia."
                    ),
                )
            )

        # --------------------------------------------------
        # 1. Resolver contexto
        # --------------------------------------------------

        try:
            context = self._context_resolver.resolve(
                original_text
            )

        except ContextResolutionError as error:
            return self._finish(
                AgentExecutionResult(
                    success=False,
                    text=original_text,
                    error=str(error),
                )
            )

        execution_text = context.resolved_text

        # --------------------------------------------------
        # 2. Construir catálogo de Capabilities
        # --------------------------------------------------

        capability_catalog = (
            self._build_capability_catalog()
        )

        # --------------------------------------------------
        # 3. Identificar intenção
        # --------------------------------------------------

        try:
            route = self._router.route(
                text=execution_text,
                available_capabilities=(
                    capability_catalog
                ),
            )

        except IntentNotFoundError as error:
            return self._finish(
                AgentExecutionResult(
                    success=False,
                    text=original_text,
                    error=str(error),
                )
            )

        # --------------------------------------------------
        # 4. Obter Capability
        # --------------------------------------------------

        try:
            capability = (
                self._runtime.registry.get_capability(
                    route.capability
                )
            )

        except Exception as error:
            return self._finish(
                AgentExecutionResult(
                    success=False,
                    text=original_text,
                    capability=route.capability,
                    error=str(error),
                )
            )

        # --------------------------------------------------
        # 5. Obter parâmetros da Capability
        # --------------------------------------------------

        parameters = {
            parameter.name: parameter.description
            for parameter
            in capability.metadata.parameters
        }

        # --------------------------------------------------
        # 6. Extrair argumentos
        # --------------------------------------------------

        try:
            arguments = self._extract_arguments(
                text=execution_text,
                capability_name=capability.name,
                parameters=parameters,
            )

        except Exception as error:
            return self._finish(
                AgentExecutionResult(
                    success=False,
                    text=original_text,
                    capability=capability.name,
                    error=str(error),
                )
            )

        # --------------------------------------------------
        # 7. Executar Capability
        # --------------------------------------------------

        try:
            execution_result = (
                self._runtime.execute(
                    capability.name,
                    **arguments,
                )
            )

        except Exception as error:
            return self._finish(
                AgentExecutionResult(
                    success=False,
                    text=original_text,
                    capability=capability.name,
                    arguments=arguments,
                    error=str(error),
                )
            )

        # --------------------------------------------------
        # 8. Converter CapabilityResult
        # --------------------------------------------------

        if isinstance(
            execution_result,
            CapabilityResult,
        ):
            return self._finish(
                AgentExecutionResult(
                    success=execution_result.success,
                    text=original_text,
                    capability=capability.name,
                    arguments=arguments,
                    result=execution_result.data,
                    error=execution_result.error,
                )
            )

        # --------------------------------------------------
        # 9. Resultado genérico
        # --------------------------------------------------

        return self._finish(
            AgentExecutionResult(
                success=True,
                text=original_text,
                capability=capability.name,
                arguments=arguments,
                result=execution_result,
            )
        )

    def _finish(
        self,
        result: AgentExecutionResult,
    ) -> AgentExecutionResult:
        """
        Finaliza uma execução registrando-a
        na memória da sessão.
        """

        self._memory.add(
            ExecutionRecord(
                text=result.text,
                success=result.success,
                capability=result.capability,
                arguments=result.arguments,
                result=result.result,
                error=result.error,
            )
        )

        return result

    def _build_capability_catalog(
        self,
    ) -> dict[str, str]:
        """
        Constrói o catálogo de Capabilities
        disponível para o roteador.
        """

        return {
            name: capability.metadata.description
            for name, capability
            in self._runtime.registry.capabilities.items()
        }

    def _extract_arguments(
        self,
        text: str,
        capability_name: str,
        parameters: dict[str, str],
    ) -> dict[str, Any]:
        """
        Extrai os argumentos necessários
        para executar uma Capability.
        """

        if not parameters:
            return {}

        return self._argument_extractor.extract(
            text=text,
            capability=capability_name,
            parameters=parameters,
        )