"""
Planner baseado em Provider da plataforma Kynka.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from kynka.domain.providers import (
    Provider,
    ProviderRequest,
)

from .plan_step import (
    PlanStep,
    ResultReference,
)
from .planner import PlanningError
from .task_plan import TaskPlan


class LLMPlanner:
    """
    Utiliza um Provider de linguagem para construir
    planos compostos por Capabilities registradas.

    O Provider somente propõe o plano.

    A execução continua sendo responsabilidade
    do PlanExecutor.
    """

    def __init__(
        self,
        provider: Provider,
    ) -> None:
        self._provider = provider

    def plan(
        self,
        text: str,
        available_capabilities: Mapping[str, str],
    ) -> TaskPlan:
        """
        Constrói um TaskPlan utilizando um Provider.
        """

        text = text.strip()

        if not text:
            raise PlanningError(
                "Não é possível planejar "
                "uma solicitação vazia."
            )

        if not available_capabilities:
            raise PlanningError(
                "Nenhuma Capability está disponível "
                "para planejamento."
            )

        capability_catalog = "\n".join(
            f"- {name}: {description}"
            for name, description
            in available_capabilities.items()
        )

        prompt = (
            "Você é exclusivamente um planejador de tarefas.\n"
            "Você NÃO deve executar nem responder o pedido.\n"
            "\n"
            "Sua função é criar uma sequência de etapas usando "
            "SOMENTE as Capabilities disponíveis.\n"
            "\n"
            "CAPABILITIES DISPONÍVEIS:\n"
            f"{capability_catalog}\n"
            "\n"
            "OBJETIVO:\n"
            f"{text}\n"
            "\n"
            "Retorne SOMENTE JSON válido no formato:\n"
            "{\n"
            '  "steps": [\n'
            "    {\n"
            '      "id": "step1",\n'
            '      "capability": "NOME_EXATO",\n'
            '      "arguments": {\n'
            '        "left": 10,\n'
            '        "right": 5\n'
            "      }\n"
            "    },\n"
            "    {\n"
            '      "id": "step2",\n'
            '      "capability": "NOME_EXATO",\n'
            '      "arguments": {\n'
            '        "left": {"result_of": "step1"},\n'
            '        "right": 3\n'
            "      }\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "\n"
            "REGRAS OBRIGATÓRIAS:\n"
            "- Use somente Capabilities listadas acima.\n"
            "- Não invente Capabilities.\n"
            "- Cada etapa deve possuir id único.\n"
            "- Os ids devem seguir step1, step2, step3...\n"
            "- arguments deve ser um objeto JSON.\n"
            "- Para usar o resultado de uma etapa anterior, use "
            'exatamente {"result_of":"stepN"}.\n'
            "- Uma etapa só pode referenciar etapas anteriores.\n"
            "- Não calcule os resultados das operações.\n"
            "- Não inclua campos extras.\n"
            "- Não use Markdown.\n"
            "- Não use ```json.\n"
            "- Retorne somente o objeto JSON.\n"
        )

        response = self._provider.generate(
            ProviderRequest(
                prompt=prompt,
            )
        )

        if not response.success:
            raise PlanningError(
                "O Provider não conseguiu criar o plano: "
                f"{response.error}"
            )

        content = (
            response.content or ""
        ).strip()

        data = self._parse_response(
            content
        )

        return self._build_plan(
            data=data,
            available_capabilities=(
                available_capabilities
            ),
        )

    @staticmethod
    def _parse_response(
        content: str,
    ) -> dict[str, Any]:
        """
        Extrai JSON da resposta do Provider.
        """

        if not content:
            raise PlanningError(
                "O Provider retornou um plano vazio."
            )

        normalized = content.strip()

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
                raise PlanningError(
                    "O Provider não retornou "
                    "um plano JSON válido."
                )

            try:
                parsed = json.loads(
                    match.group(0)
                )

            except json.JSONDecodeError as error:
                raise PlanningError(
                    "O Provider retornou JSON inválido."
                ) from error

        if not isinstance(parsed, dict):
            raise PlanningError(
                "O plano precisa ser um objeto JSON."
            )

        return parsed

    def _build_plan(
        self,
        data: dict[str, Any],
        available_capabilities: Mapping[str, str],
    ) -> TaskPlan:
        """
        Valida o plano recebido e converte
        sua estrutura para TaskPlan.
        """

        if set(data.keys()) != {"steps"}:
            raise PlanningError(
                "O plano retornado possui "
                "estrutura inválida."
            )

        raw_steps = data.get("steps")

        if not isinstance(raw_steps, list):
            raise PlanningError(
                "'steps' precisa ser uma lista."
            )

        if not raw_steps:
            raise PlanningError(
                "O plano retornado não possui etapas."
            )

        plan = TaskPlan()

        known_step_ids: set[str] = set()

        for index, raw_step in enumerate(
            raw_steps,
            start=1,
        ):
            if not isinstance(raw_step, dict):
                raise PlanningError(
                    "Cada etapa precisa ser "
                    "um objeto JSON."
                )

            allowed_fields = {
                "id",
                "capability",
                "arguments",
            }

            if set(raw_step.keys()) != allowed_fields:
                raise PlanningError(
                    f"A etapa {index} possui "
                    "campos inválidos."
                )

            step_id = raw_step.get("id")
            capability = raw_step.get(
                "capability"
            )
            arguments = raw_step.get(
                "arguments"
            )

            expected_id = f"step{index}"

            if step_id != expected_id:
                raise PlanningError(
                    "Identificador de etapa inválido. "
                    f"Esperado {expected_id!r}, "
                    f"recebido {step_id!r}."
                )

            if step_id in known_step_ids:
                raise PlanningError(
                    "Identificador de etapa duplicado: "
                    f"{step_id!r}."
                )

            if not isinstance(
                capability,
                str,
            ):
                raise PlanningError(
                    f"A etapa {step_id!r} não possui "
                    "uma Capability válida."
                )

            if capability not in (
                available_capabilities
            ):
                raise PlanningError(
                    "O Provider tentou utilizar uma "
                    "Capability não registrada: "
                    f"{capability!r}."
                )

            if not isinstance(
                arguments,
                dict,
            ):
                raise PlanningError(
                    f"Os argumentos da etapa "
                    f"{step_id!r} precisam ser "
                    "um objeto."
                )

            resolved_arguments = {
                name: self._convert_argument(
                    value=value,
                    known_step_ids=known_step_ids,
                )
                for name, value
                in arguments.items()
            }

            plan.add_step(
                PlanStep(
                    id=step_id,
                    capability=capability,
                    arguments=resolved_arguments,
                )
            )

            known_step_ids.add(
                step_id
            )

        return plan

    def _convert_argument(
        self,
        value: Any,
        known_step_ids: set[str],
    ) -> Any:
        """
        Converte referências JSON em ResultReference.
        """

        if not isinstance(value, dict):
            return value

        if set(value.keys()) != {
            "result_of"
        }:
            raise PlanningError(
                "Referência de resultado inválida."
            )

        referenced_step = value.get(
            "result_of"
        )

        if not isinstance(
            referenced_step,
            str,
        ):
            raise PlanningError(
                "'result_of' precisa conter "
                "um identificador de etapa."
            )

        if referenced_step not in (
            known_step_ids
        ):
            raise PlanningError(
                "Uma etapa tentou utilizar "
                "um resultado ainda não disponível: "
                f"{referenced_step!r}."
            )

        return ResultReference(
            referenced_step
        )
