"""
Fachada principal da plataforma Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass

from kynka.application.agent import (
    AgentExecutionResult,
    AgentExecutor,
)
from kynka.application.argument_extractor import (
    ArgumentExtractor,
)
from kynka.application.context import (
    AgentContext,
)
from kynka.application.execution import (
    ExecutionMode,
    ExecutionModeSelector,
)
from kynka.application.hybrid_argument_extractor import (
    HybridArgumentExtractor,
)
from kynka.application.intent_router import (
    HybridIntentRouter,
    IntentRouter,
    LLMIntentRouter,
)
from kynka.application.memory import (
    ExecutionMemory,
)
from kynka.application.planning import (
    DeterministicPlanner,
    HybridPlanner,
    LLMPlanner,
    PlanExecutionResult,
    PlanExecutor,
    PlanningError,
    TaskPlan,
)
from kynka.application.plugin_installer import (
    PluginInstaller,
)
from kynka.application.recovery import (
    PlanRecovery,
    RecoveryDecision,
)
from kynka.domain.plugins.plugin import Plugin
from kynka.infrastructure.providers import (
    OllamaProvider,
)
from kynka.kernel.runtime import Runtime


@dataclass(frozen=True, slots=True)
class GoalExecutionResult:
    """
    Resultado de uma execução orientada a objetivo.

    Reúne:

    - resultado da execução do plano;
    - decisão de recuperação, caso necessária.
    """

    execution: PlanExecutionResult
    recovery: RecoveryDecision

    @property
    def success(self) -> bool:
        return self.execution.success

    @property
    def result(self):
        return self.execution.result

    @property
    def error(self) -> str | None:
        return self.execution.error

    @property
    def steps(self):
        return self.execution.steps


class Kynka:
    """
    Fachada principal da plataforma Kynka.

    Centraliza:

    - Runtime;
    - Plugins;
    - AgentExecutor;
    - contexto e memória;
    - roteamento;
    - extração de argumentos;
    - planejamento;
    - execução de planos;
    - seleção automática do modo de execução;
    - análise de recuperação de planos.
    """

    def __init__(
        self,
        model: str = "llama3.2:3b",
        memory_size: int = 100,
    ) -> None:
        # --------------------------------------------------
        # Runtime
        # --------------------------------------------------

        self._runtime = Runtime()

        # --------------------------------------------------
        # Provider
        # --------------------------------------------------

        self._provider = OllamaProvider(
            model=model
        )

        # --------------------------------------------------
        # Contexto e memória
        # --------------------------------------------------

        memory = ExecutionMemory(
            max_records=memory_size
        )

        self._context = AgentContext(
            memory=memory
        )

        # --------------------------------------------------
        # Extração de argumentos
        # --------------------------------------------------

        self._argument_extractor = (
            HybridArgumentExtractor(
                ArgumentExtractor(
                    self._provider
                )
            )
        )

        # --------------------------------------------------
        # Roteamento
        # --------------------------------------------------

        self._router = HybridIntentRouter(
            deterministic_router=IntentRouter(),
            llm_router=LLMIntentRouter(
                self._provider
            ),
        )

        # --------------------------------------------------
        # Plugins
        # --------------------------------------------------

        self._installer = PluginInstaller(
            runtime=self._runtime,
            argument_extractor=(
                self._argument_extractor
            ),
        )

        # --------------------------------------------------
        # Agent
        # --------------------------------------------------

        self._agent = AgentExecutor(
            runtime=self._runtime,
            router=self._router,
            argument_extractor=(
                self._argument_extractor
            ),
            context=self._context,
        )

        # --------------------------------------------------
        # Planning
        # --------------------------------------------------

        self._deterministic_planner = (
            DeterministicPlanner()
        )

        self._llm_planner = LLMPlanner(
            self._provider
        )

        self._planner = HybridPlanner(
            deterministic_planner=(
                self._deterministic_planner
            ),
            llm_planner=self._llm_planner,
        )

        self._plan_executor = PlanExecutor(
            self._runtime
        )

        # --------------------------------------------------
        # Recovery
        # --------------------------------------------------

        self._plan_recovery = PlanRecovery()

        # --------------------------------------------------
        # Seleção do modo de execução
        # --------------------------------------------------

        self._execution_mode_selector = (
            ExecutionModeSelector()
        )

    # ======================================================
    # Ciclo de vida
    # ======================================================

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

    # ======================================================
    # Plugins
    # ======================================================

    def install(
        self,
        plugin: Plugin,
    ) -> None:
        """
        Instala um Plugin.
        """

        self._installer.install(
            plugin
        )

    # ======================================================
    # Entrada unificada
    # ======================================================

    def run(
        self,
        text: str,
    ) -> AgentExecutionResult | PlanExecutionResult:
        """
        Executa uma solicitação automaticamente.

        A plataforma decide se deve utilizar:

        - execução simples;
        - planejamento multi-step.
        """

        self._ensure_running()

        mode = (
            self._execution_mode_selector.select(
                text
            )
        )

        if mode is ExecutionMode.PLAN:
            return self.execute_goal(
                text
            )

        return self.execute(
            text
        )

    # ======================================================
    # Execução simples
    # ======================================================

    def execute(
        self,
        text: str,
    ) -> AgentExecutionResult:
        """
        Executa uma solicitação individual.
        """

        self._ensure_running()

        return self._agent.execute(
            text
        )

    # ======================================================
    # Planning
    # ======================================================

    def plan(
        self,
        goal: str,
    ) -> TaskPlan:
        """
        Cria automaticamente um plano para um objetivo.
        """

        self._ensure_running()

        capability_catalog = (
            self._build_capability_catalog()
        )

        if not capability_catalog:
            raise PlanningError(
                "Nenhuma Capability está disponível "
                "para planejamento."
            )

        return self._planner.plan(
            goal=goal,
            available_capabilities=(
                capability_catalog
            ),
        )

    def execute_plan(
        self,
        plan: TaskPlan,
    ) -> PlanExecutionResult:
        """
        Executa um plano previamente criado.
        """

        self._ensure_running()

        return self._plan_executor.execute(
            plan
        )

    def execute_goal(
        self,
        goal: str,
    ) -> PlanExecutionResult:
        """
        Planeja e executa um objetivo composto.

        Mantido como operação direta para preservar
        compatibilidade com o comportamento atual.
        """

        self._ensure_running()

        plan = self.plan(
            goal
        )

        return self.execute_plan(
            plan
        )

    # ======================================================
    # Recovery
    # ======================================================

    def analyze_recovery(
        self,
        result: PlanExecutionResult,
    ) -> RecoveryDecision:
        """
        Analisa um resultado de execução e determina
        qual estratégia de recuperação é adequada.

        Nenhuma nova execução é realizada aqui.
        """

        return self._plan_recovery.decide(
            result
        )

    def execute_goal_with_recovery(
        self,
        goal: str,
    ) -> GoalExecutionResult:
        """
        Planeja e executa um objetivo e, em seguida,
        analisa se alguma recuperação é necessária.

        Nesta versão a recuperação ainda é apenas
        uma decisão. Não existe retry ou replanning
        automático.
        """

        self._ensure_running()

        execution = self.execute_goal(
            goal
        )

        recovery = self.analyze_recovery(
            execution
        )

        return GoalExecutionResult(
            execution=execution,
            recovery=recovery,
        )

    # ======================================================
    # Utilidades internas
    # ======================================================

    def _build_capability_catalog(
        self,
    ) -> dict[str, str]:
        """
        Constrói o catálogo de Capabilities disponíveis.
        """

        return {
            name: capability.metadata.description
            for name, capability
            in self._runtime.registry.capabilities.items()
        }

    def _ensure_running(self) -> None:
        """
        Garante que a plataforma esteja iniciada.
        """

        if not self._runtime.is_running:
            raise RuntimeError(
                "A plataforma Kynka "
                "não está iniciada."
            )

    # ======================================================
    # Propriedades
    # ======================================================

    @property
    def runtime(self) -> Runtime:
        return self._runtime

    @property
    def context(self) -> AgentContext:
        return self._context

    @property
    def memory(self) -> ExecutionMemory:
        return self._context.memory

    @property
    def plugins(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            self._runtime.registry.plugins.keys()
        )

    @property
    def capabilities(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            self._runtime.registry.capabilities.keys()
        )

    @property
    def model(self) -> str:
        return self._provider.model

    @property
    def planner(self) -> HybridPlanner:
        return self._planner

    @property
    def plan_recovery(self) -> PlanRecovery:
        return self._plan_recovery

    @property
    def execution_mode_selector(
        self,
    ) -> ExecutionModeSelector:
        return self._execution_mode_selector