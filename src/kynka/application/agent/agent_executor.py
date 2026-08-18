"""
Executor agêntico da plataforma Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kynka.application.assistant import (
    GeneralAssistant,
    GeneralAssistantError,
)
from kynka.application.context import (
    AgentContext,
    ContextCommandHandler,
    ContextResolutionError,
    ContextResolver,
    VariableResolver,
)
from kynka.application.intent_router import (
    IntentNotFoundError,
)
from kynka.application.memory import (
    ExecutionRecord,
)
from kynka.domain.capabilities import (
    CapabilityResult,
)
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
    Coordena:

    - contexto;
    - variáveis;
    - roteamento;
    - extração de argumentos;
    - execução;
    - fallback conversacional;
    - memória.
    """

    def __init__(
        self,
        runtime: Runtime,
        router: Any,
        argument_extractor: Any,
        context: AgentContext,
        assistant: GeneralAssistant | None = None,
    ) -> None:
        self._runtime = runtime
        self._router = router
        self._argument_extractor = argument_extractor
        self._context = context
        self._assistant = assistant

        self._context_resolver = ContextResolver(
            self._context
        )

        self._variable_resolver = VariableResolver(
            self._context
        )

        self._context_command_handler = (
            ContextCommandHandler(
                self._context
            )
        )

    @property
    def context(self) -> AgentContext:
        return self._context

    @property
    def memory(self):
        return self._context.memory

    def execute(
        self,
        text: str,
    ) -> AgentExecutionResult:

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
                ),
                operational=False,
            )

        self._context.set_current(
            original_text
        )

        try:
            return self._execute(
                original_text
            )

        finally:
            self._context.clear_current()

    def _execute(
        self,
        original_text: str,
    ) -> AgentExecutionResult:

        # ==================================================
        # 1. Comandos contextuais
        # ==================================================

        context_command = (
            self._context_command_handler.handle(
                original_text
            )
        )

        if context_command.handled:
            return self._finish(
                AgentExecutionResult(
                    success=context_command.success,
                    text=original_text,
                    result=(
                        context_command.message
                        if context_command.success
                        else None
                    ),
                    error=context_command.error,
                ),
                operational=False,
            )

        # ==================================================
        # 2. Resultado anterior
        # ==================================================

        try:
            context_resolution = (
                self._context_resolver.resolve(
                    original_text
                )
            )

        except ContextResolutionError as error:
            return self._finish(
                AgentExecutionResult(
                    success=False,
                    text=original_text,
                    error=str(error),
                )
            )

        execution_text = (
            context_resolution.resolved_text
        )

        # ==================================================
        # 3. Variáveis nomeadas
        # ==================================================

        variable_resolution = (
            self._variable_resolver.resolve(
                execution_text
            )
        )

        execution_text = (
            variable_resolution.resolved_text
        )

        # ==================================================
        # 4. Catálogo
        # ==================================================

        capability_catalog = (
            self._build_capability_catalog()
        )

        # ==================================================
        # 5. Roteamento
        # ==================================================

        try:
            route = self._router.route(
                text=execution_text,
                available_capabilities=(
                    capability_catalog
                ),
            )

        except IntentNotFoundError:
            return self._execute_fallback(
                original_text
            )

        # ==================================================
        # 6. Capability
        # ==================================================

        try:
            capability = (
                self._runtime.registry
                .get_capability(
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

        # ==================================================
        # 7. Parâmetros
        # ==================================================

        parameters = {
            parameter.name:
                parameter.description
            for parameter
            in capability.metadata.parameters
        }

        # ==================================================
        # 8. Extração
        # ==================================================

        try:
            arguments = (
                self._extract_arguments(
                    text=execution_text,
                    capability_name=(
                        capability.name
                    ),
                    parameters=parameters,
                )
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

        # ==================================================
        # 9. Execução
        # ==================================================

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

        # ==================================================
        # 10. CapabilityResult
        # ==================================================

        if isinstance(
            execution_result,
            CapabilityResult,
        ):
            return self._finish(
                AgentExecutionResult(
                    success=(
                        execution_result.success
                    ),
                    text=original_text,
                    capability=capability.name,
                    arguments=arguments,
                    result=execution_result.data,
                    error=execution_result.error,
                )
            )

        # ==================================================
        # 11. Resultado genérico
        # ==================================================

        return self._finish(
            AgentExecutionResult(
                success=True,
                text=original_text,
                capability=capability.name,
                arguments=arguments,
                result=execution_result,
            )
        )

    def _execute_fallback(
        self,
        original_text: str,
    ) -> AgentExecutionResult:
        """
        Usa o assistente geral quando nenhuma
        Capability adequada foi encontrada.
        """

        if self._assistant is None:
            return self._finish(
                AgentExecutionResult(
                    success=False,
                    text=original_text,
                    error=(
                        "Nenhuma Capability adequada "
                        "foi encontrada."
                    ),
                )
            )

        try:
            answer = self._assistant.answer(
                original_text
            )

        except GeneralAssistantError as error:
            return self._finish(
                AgentExecutionResult(
                    success=False,
                    text=original_text,
                    capability="assistant.general",
                    error=str(error),
                )
            )

        except Exception as error:
            return self._finish(
                AgentExecutionResult(
                    success=False,
                    text=original_text,
                    capability="assistant.general",
                    error=str(error),
                )
            )

        return self._finish(
            AgentExecutionResult(
                success=True,
                text=original_text,
                capability="assistant.general",
                arguments={},
                result=answer,
            )
        )

    def _finish(
        self,
        result: AgentExecutionResult,
        *,
        operational: bool = True,
    ) -> AgentExecutionResult:
        """
        Registra o resultado na memória.
        """

        self._context.memory.add(
            ExecutionRecord(
                text=result.text,
                success=result.success,
                capability=result.capability,
                arguments=result.arguments,
                result=result.result,
                error=result.error,
                operational=operational,
            )
        )

        return result

    def _build_capability_catalog(
        self,
    ) -> dict[str, str]:

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

        if not parameters:
            return {}

        return self._argument_extractor.extract(
            text=text,
            capability=capability_name,
            parameters=parameters,
        )