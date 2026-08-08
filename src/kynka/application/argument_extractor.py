"""
Extração de argumentos para Capabilities da plataforma Kynka.
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


class ArgumentExtractionError(Exception):
    """
    Erro lançado quando os argumentos de uma Capability
    não podem ser extraídos.
    """


class ArgumentExtractor:
    """
    Utiliza um Provider para extrair argumentos estruturados
    de uma solicitação em linguagem natural.
    """

    def __init__(
        self,
        provider: Provider,
    ) -> None:
        self._provider = provider

    def extract(
        self,
        text: str,
        capability: str,
        parameters: Mapping[str, str],
    ) -> dict[str, Any]:
        """
        Extrai os argumentos necessários para uma Capability.
        """

        text = text.strip()

        if not text:
            raise ArgumentExtractionError(
                "Não é possível extrair argumentos de um texto vazio."
            )

        if not capability.strip():
            raise ArgumentExtractionError(
                "O nome da Capability não pode estar vazio."
            )

        if not parameters:
            return {}

        parameter_description = "\n".join(
            f"- {name}: {description}"
            for name, description in parameters.items()
        )

        prompt = (
            "Você é um extrator de argumentos da plataforma Kynka.\n"
            "\n"
            "Sua tarefa é extrair valores do pedido do usuário "
            "para executar uma Capability.\n"
            "\n"
            f"CAPABILITY:\n{capability}\n"
            "\n"
            "PARÂMETROS NECESSÁRIOS:\n"
            f"{parameter_description}\n"
            "\n"
            "PEDIDO DO USUÁRIO:\n"
            f"{text}\n"
            "\n"
            "REGRAS:\n"
            "- Retorne somente um objeto JSON.\n"
            "- Use exatamente os nomes dos parâmetros informados.\n"
            "- Números devem ser números JSON, não strings.\n"
            "- Não faça o cálculo.\n"
            "- Não explique a resposta.\n"
            "- Não adicione texto antes ou depois do JSON.\n"
            "- Se um valor não puder ser identificado, use null.\n"
            "\n"
            "RESPOSTA:"
        )

        response = self._provider.generate(
            ProviderRequest(
                prompt=prompt,
            )
        )

        if not response.success:
            raise ArgumentExtractionError(
                "O Provider não conseguiu extrair os argumentos: "
                f"{response.error}"
            )

        raw_content = (
            response.content or ""
        ).strip()

        extracted = self._parse_response(
            raw_content
        )

        self._validate_parameters(
            extracted=extracted,
            parameters=parameters,
        )

        return extracted

    @staticmethod
    def _parse_response(
        content: str,
    ) -> dict[str, Any]:
        """
        Converte a resposta do Provider em um dicionário.
        """

        if not content:
            raise ArgumentExtractionError(
                "O Provider retornou uma resposta vazia."
            )

        try:
            parsed = json.loads(
                content
            )

        except json.JSONDecodeError:
            match = re.search(
                r"\{.*\}",
                content,
                flags=re.DOTALL,
            )

            if match is None:
                raise ArgumentExtractionError(
                    "O Provider não retornou argumentos "
                    f"estruturados válidos: {content!r}"
                )

            try:
                parsed = json.loads(
                    match.group(0)
                )

            except json.JSONDecodeError as error:
                raise ArgumentExtractionError(
                    "O Provider retornou JSON inválido: "
                    f"{content!r}"
                ) from error

        if not isinstance(parsed, dict):
            raise ArgumentExtractionError(
                "Os argumentos retornados precisam formar "
                "um objeto JSON."
            )

        return parsed

    @staticmethod
    def _validate_parameters(
        extracted: dict[str, Any],
        parameters: Mapping[str, str],
    ) -> None:
        """
        Garante que o Provider não inventou parâmetros e que
        todos os parâmetros necessários foram encontrados.
        """

        allowed_parameters = set(
            parameters.keys()
        )

        returned_parameters = set(
            extracted.keys()
        )

        unexpected = (
            returned_parameters - allowed_parameters
        )

        if unexpected:
            names = ", ".join(
                sorted(unexpected)
            )

            raise ArgumentExtractionError(
                "O Provider retornou parâmetros não permitidos: "
                f"{names}"
            )

        missing = (
            allowed_parameters - returned_parameters
        )

        if missing:
            names = ", ".join(
                sorted(missing)
            )

            raise ArgumentExtractionError(
                "O Provider não retornou os parâmetros: "
                f"{names}"
            )

        null_parameters = [
            name
            for name in allowed_parameters
            if extracted[name] is None
        ]

        if null_parameters:
            names = ", ".join(
                sorted(null_parameters)
            )

            raise ArgumentExtractionError(
                "Não foi possível identificar valores para: "
                f"{names}"
            )