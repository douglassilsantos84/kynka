"""
Contexto de execução agêntica da plataforma Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kynka.application.memory import ExecutionMemory


class ContextVariableNotFoundError(Exception):
    """
    Erro lançado quando uma variável contextual
    solicitada não existe.
    """


@dataclass(slots=True)
class AgentContext:
    """
    Representa o contexto ativo de uma sessão agêntica.

    O contexto centraliza:

    - memória de execuções;
    - solicitação atualmente em processamento;
    - variáveis contextuais da sessão.
    """

    memory: ExecutionMemory
    current_text: str | None = None

    _variables: dict[str, Any] = field(
        default_factory=dict,
        repr=False,
    )

    # --------------------------------------------------
    # Solicitação atual
    # --------------------------------------------------

    def set_current(
        self,
        text: str,
    ) -> None:
        """
        Define a solicitação atualmente em execução.
        """

        self.current_text = text.strip()

    def clear_current(self) -> None:
        """
        Remove a solicitação atualmente registrada.
        """

        self.current_text = None

    # --------------------------------------------------
    # Variáveis contextuais
    # --------------------------------------------------

    def set_variable(
        self,
        name: str,
        value: Any,
    ) -> None:
        """
        Armazena ou atualiza uma variável contextual.
        """

        normalized_name = self._normalize_name(
            name
        )

        self._variables[normalized_name] = value

    def get_variable(
        self,
        name: str,
    ) -> Any:
        """
        Retorna uma variável contextual.

        Lança ContextVariableNotFoundError caso
        a variável não exista.
        """

        normalized_name = self._normalize_name(
            name
        )

        try:
            return self._variables[
                normalized_name
            ]

        except KeyError as error:
            raise ContextVariableNotFoundError(
                "Variável contextual não encontrada: "
                f"{normalized_name!r}."
            ) from error

    def get_variable_or_default(
        self,
        name: str,
        default: Any = None,
    ) -> Any:
        """
        Retorna uma variável ou um valor padrão.
        """

        normalized_name = self._normalize_name(
            name
        )

        return self._variables.get(
            normalized_name,
            default,
        )

    def has_variable(
        self,
        name: str,
    ) -> bool:
        """
        Verifica se uma variável existe.
        """

        normalized_name = self._normalize_name(
            name
        )

        return normalized_name in self._variables

    def remove_variable(
        self,
        name: str,
    ) -> None:
        """
        Remove uma variável contextual.

        Se a variável não existir, nenhuma exceção
        será lançada.
        """

        normalized_name = self._normalize_name(
            name
        )

        self._variables.pop(
            normalized_name,
            None,
        )

    def clear_variables(self) -> None:
        """
        Remove todas as variáveis contextuais.
        """

        self._variables.clear()

    # --------------------------------------------------
    # Estado
    # --------------------------------------------------

    @property
    def variables(
        self,
    ) -> dict[str, Any]:
        """
        Retorna uma cópia das variáveis contextuais.
        """

        return dict(
            self._variables
        )

    @property
    def last_result(self) -> Any:
        """
        Retorna o último resultado bem-sucedido
        disponível na memória.
        """

        record = self.memory.last_successful

        if record is None:
            return None

        return record.result

    @property
    def has_history(self) -> bool:
        """
        Indica se existe histórico de execução.
        """

        return len(self.memory) > 0

    def reset(self) -> None:
        """
        Reinicia o estado contextual da sessão.

        A memória também é limpa.
        """

        self.current_text = None

        self._variables.clear()

        self.memory.clear()

    # --------------------------------------------------
    # Utilidades
    # --------------------------------------------------

    @staticmethod
    def _normalize_name(
        name: str,
    ) -> str:
        """
        Normaliza nomes de variáveis contextuais.
        """

        normalized_name = (
            name.strip().lower()
        )

        if not normalized_name:
            raise ValueError(
                "O nome da variável contextual "
                "não pode estar vazio."
            )

        return normalized_name