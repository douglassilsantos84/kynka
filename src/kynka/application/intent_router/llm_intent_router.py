"""
Roteador de intenções baseado em Provider da plataforma Kynka.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from kynka.application.intent_router.intent_router import (
    IntentNotFoundError,
    IntentRoute,
)
from kynka.domain.providers import (
    Provider,
    ProviderRequest,
)


class LLMIntentRouter:
    """
    Utiliza um Provider de linguagem para selecionar
    uma Capability disponível na plataforma.
    """

    def __init__(
        self,
        provider: Provider,
    ) -> None:
        self._provider = provider

    def route(
        self,
        text: str,
        available_capabilities: Mapping[str, str],
    ) -> IntentRoute:
        """
        Seleciona semanticamente uma Capability.

        available_capabilities:
            chave -> nome da Capability
            valor -> descrição da Capability
        """

        text = text.strip()

        if not text:
            raise IntentNotFoundError(
                "Não é possível identificar uma intenção em um texto vazio."
            )

        if not available_capabilities:
            raise IntentNotFoundError(
                "Nenhuma Capability está disponível para roteamento."
            )

        capability_catalog = "\n".join(
            f"- {name}: {description}"
            for name, description in available_capabilities.items()
        )

        prompt = (
            "Você é exclusivamente um classificador de intenções.\n"
            "Você NÃO deve responder nem executar o pedido do usuário.\n"
            "\n"
            "CAPABILITIES DISPONÍVEIS:\n"
            f"{capability_catalog}\n"
            "\n"
            "PEDIDO:\n"
            f"{text}\n"
            "\n"
            "Analise se alguma Capability pode REALMENTE executar "
            "esse pedido.\n"
            "\n"
            "Se existir uma Capability adequada, responda JSON:\n"
            '{"decision":"capability","capability":"NOME_EXATO"}\n'
            "\n"
            "Se nenhuma Capability puder executar o pedido, responda:\n"
            '{"decision":"none","capability":null}\n'
            "\n"
            "IMPORTANTE:\n"
            "- Não escolha uma Capability apenas por ela existir.\n"
            "- Uma Capability de cumprimento NÃO calcula valores.\n"
            "- Uma Capability de cumprimento NÃO consulta clima.\n"
            "- Uma Capability de cumprimento NÃO executa tarefas "
            "não relacionadas a cumprimentos.\n"
            "- Retorne somente o objeto JSON.\n"
        )

        response = self._provider.generate(
            ProviderRequest(
                prompt=prompt,
            )
        )

        if not response.success:
            raise IntentNotFoundError(
                "O Provider não conseguiu determinar a intenção: "
                f"{response.error}"
            )

        raw_content = (
            response.content or ""
        ).strip()

        decision = self._parse_response(
            raw_content
        )

        decision_type = decision.get(
            "decision"
        )

        selected = decision.get(
            "capability"
        )

        if decision_type == "none":
            raise IntentNotFoundError(
                f"Nenhuma intenção conhecida para: {text!r}"
            )

        if decision_type != "capability":
            raise IntentNotFoundError(
                "O Provider retornou uma decisão inválida."
            )

        if not isinstance(selected, str):
            raise IntentNotFoundError(
                "O Provider não informou uma Capability válida."
            )

        selected = selected.strip()

        if selected not in available_capabilities:
            raise IntentNotFoundError(
                "O Provider retornou uma Capability não registrada: "
                f"{selected!r}"
            )

        return IntentRoute(
            capability=selected,
            confidence=0.8,
            reason=(
                f"Capability selecionada pelo Provider "
                f"'{self._provider.name}'."
            ),
        )

    @staticmethod
    def _parse_response(
        content: str,
    ) -> dict[str, Any]:
        """
        Extrai e valida a estrutura JSON retornada pelo Provider.
        """

        if not content:
            raise IntentNotFoundError(
                "O Provider retornou uma resposta vazia."
            )

        normalized = content.strip()

        # Compatibilidade defensiva com respostas simples
        # de modelos pequenos, como NONE ou NONE.
        if normalized.rstrip(".").upper() == "NONE":
            return {
                "decision": "none",
                "capability": None,
            }

        try:
            parsed = json.loads(
                normalized
            )

        except json.JSONDecodeError:
            match = re.search(
                r"\{.*\}",
                normalized,
                flags=re.DOTALL,
            )

            if match is None:
                raise IntentNotFoundError(
                    "O Provider não retornou uma decisão "
                    f"estruturada válida: {content!r}"
                )

            try:
                parsed = json.loads(
                    match.group(0)
                )

            except json.JSONDecodeError as error:
                raise IntentNotFoundError(
                    "O Provider retornou JSON inválido: "
                    f"{content!r}"
                ) from error

        if not isinstance(parsed, dict):
            raise IntentNotFoundError(
                "A decisão do Provider precisa ser um objeto JSON."
            )

        return parsed