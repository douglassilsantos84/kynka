"""
Roteador híbrido de intenções da plataforma Kynka.
"""

from __future__ import annotations

from collections.abc import Mapping

from kynka.application.intent_router.intent_router import (
    IntentNotFoundError,
    IntentRoute,
    IntentRouter,
)
from kynka.application.intent_router.llm_intent_router import (
    LLMIntentRouter,
)


class HybridIntentRouter:
    """
    Combina roteamento determinístico e roteamento por LLM.

    Estratégia:
    1. tenta primeiro o roteamento determinístico;
    2. caso nenhuma intenção seja encontrada, utiliza o LLM;
    3. caso ambos falhem, a intenção é considerada desconhecida.
    """

    def __init__(
        self,
        deterministic_router: IntentRouter,
        llm_router: LLMIntentRouter,
    ) -> None:
        self._deterministic_router = deterministic_router
        self._llm_router = llm_router

    def route(
        self,
        text: str,
        available_capabilities: Mapping[str, str],
    ) -> IntentRoute:
        """
        Resolve uma intenção utilizando a estratégia híbrida.
        """

        try:
            route = self._deterministic_router.route(
                text
            )

            if route.capability not in available_capabilities:
                raise IntentNotFoundError(
                    "A Capability selecionada pelo roteador "
                    "determinístico não está disponível: "
                    f"{route.capability!r}"
                )

            return IntentRoute(
                capability=route.capability,
                confidence=route.confidence,
                reason=(
                    "Capability selecionada pelo "
                    "roteador determinístico."
                ),
            )

        except IntentNotFoundError:
            pass

        try:
            return self._llm_router.route(
                text=text,
                available_capabilities=available_capabilities,
            )

        except IntentNotFoundError as error:
            raise IntentNotFoundError(
                f"Nenhuma rota encontrada para: {text!r}"
            ) from error