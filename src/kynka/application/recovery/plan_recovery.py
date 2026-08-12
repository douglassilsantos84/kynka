"""
Mecanismo de recuperação de planos da plataforma Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from kynka.application.planning import (
    PlanExecutionResult,
)


class RecoveryAction(str, Enum):
    """
    Ações possíveis após uma falha
    durante a execução de um plano.
    """

    NONE = "none"
    RETRY = "retry"
    REPLAN = "replan"
    ABORT = "abort"


@dataclass(frozen=True, slots=True)
class RecoveryDecision:
    """
    Representa uma decisão de recuperação.
    """

    action: RecoveryAction
    reason: str

    @property
    def should_retry(self) -> bool:
        return self.action is RecoveryAction.RETRY

    @property
    def should_replan(self) -> bool:
        return self.action is RecoveryAction.REPLAN

    @property
    def should_abort(self) -> bool:
        return self.action is RecoveryAction.ABORT


class PlanRecovery:
    """
    Analisa resultados de execução e determina
    qual estratégia de recuperação deve ser usada.

    Nesta primeira versão, nenhuma nova execução
    é realizada. A classe apenas classifica a falha.
    """

    def decide(
        self,
        result: PlanExecutionResult,
    ) -> RecoveryDecision:
        """
        Analisa o resultado de um plano.
        """

        if result.success:
            return RecoveryDecision(
                action=RecoveryAction.NONE,
                reason=(
                    "O plano foi executado "
                    "com sucesso."
                ),
            )

        error = (
            result.error or ""
        ).strip()

        normalized_error = (
            error.lower()
        )

        # --------------------------------------------------
        # Plano inválido
        # --------------------------------------------------

        if normalized_error.startswith(
            "plano inválido:"
        ):
            return RecoveryDecision(
                action=RecoveryAction.REPLAN,
                reason=(
                    "A estrutura do plano é inválida "
                    "e precisa ser reconstruída."
                ),
            )

        # --------------------------------------------------
        # Capability inexistente
        # --------------------------------------------------

        if (
            "capability não disponível"
            in normalized_error
        ):
            return RecoveryDecision(
                action=RecoveryAction.REPLAN,
                reason=(
                    "O plano depende de uma Capability "
                    "que não está disponível."
                ),
            )

        # --------------------------------------------------
        # Dependência não resolvida
        # --------------------------------------------------

        if (
            "resultado da etapa"
            in normalized_error
            and "não está disponível"
            in normalized_error
        ):
            return RecoveryDecision(
                action=RecoveryAction.REPLAN,
                reason=(
                    "Uma dependência entre etapas "
                    "não pôde ser resolvida."
                ),
            )

        # --------------------------------------------------
        # Falha operacional genérica
        # --------------------------------------------------

        if result.steps:
            return RecoveryDecision(
                action=RecoveryAction.RETRY,
                reason=(
                    "A estrutura do plano é válida, "
                    "mas ocorreu uma falha durante "
                    "a execução de uma etapa."
                ),
            )

        # --------------------------------------------------
        # Falha sem informação suficiente
        # --------------------------------------------------

        return RecoveryDecision(
            action=RecoveryAction.ABORT,
            reason=(
                "Não existem informações suficientes "
                "para uma recuperação automática segura."
            ),
        )