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
from kynka.application.context import (
    AgentContext,
    VariableResolver,
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
from kynka.domain.plugins.plugin import Plugin
from kynka.infrastructure.providers import (
    OllamaProvider,
)
from kynka.kernel.runtime import Runtime


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
    - resolução de variáveis contextuais;
    - seleção automática do modo de execução.
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
        # Resolução de variáveis contextuais
        # --------------------------------------------------

        self._variable_resolver = (
            VariableResolver(
                self._context
            )
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

        Antes do planejamento, variáveis existentes
        no contexto são resolvidas para seus valores.
        """

        self._ensure_running()

        goal = goal.strip()

        if not goal:
            raise PlanningError(
                "O objetivo não pode estar vazio."
            )

        capability_catalog = (
            self._build_capability_catalog()
        )

        if not capability_catalog:
            raise PlanningError(
                "Nenhuma Capability está disponível "
                "para planejamento."
            )

        # --------------------------------------------------
        # Resolve variáveis do contexto antes do planner
        # --------------------------------------------------

        variable_resolution = (
            self._variable_resolver.resolve(
                goal
            )
        )

        resolved_goal = (
            variable_resolution.resolved_text
        )

        # --------------------------------------------------
        # Planejamento
        # --------------------------------------------------

        return self._planner.plan(
            goal=resolved_goal,
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
        """

        self._ensure_running()

        plan = self.plan(
            goal
        )

        return self.execute_plan(
            plan
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
    def execution_mode_selector(
        self,
    ) -> ExecutionModeSelector:
        return self._execution_mode_selector