"""
Memória de execução da plataforma Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class ExecutionRecord:
    """
    Representa uma execução armazenada na memória.
    """

    text: str
    success: bool
    capability: str | None = None
    arguments: dict[str, Any] | None = None
    result: Any = None
    error: str | None = None

    # Indica se o resultado pode ser utilizado
    # como resultado operacional em referências
    # como "esse resultado".
    operational: bool = True


class ExecutionMemory:
    """
    Memória temporária das execuções realizadas
    durante uma sessão da Kynka.
    """

    def __init__(
        self,
        max_records: int = 100,
    ) -> None:
        if max_records <= 0:
            raise ValueError(
                "max_records precisa ser maior que zero."
            )

        self._max_records = max_records
        self._records: list[ExecutionRecord] = []

    def add(
        self,
        record: ExecutionRecord,
    ) -> None:
        """
        Adiciona uma execução à memória.
        """

        self._records.append(record)

        if len(self._records) > self._max_records:
            self._records.pop(0)

    @property
    def records(
        self,
    ) -> tuple[ExecutionRecord, ...]:
        """
        Retorna uma cópia imutável do histórico.
        """

        return tuple(self._records)

    @property
    def last(
        self,
    ) -> ExecutionRecord | None:
        """
        Retorna a última execução registrada,
        independentemente do tipo.
        """

        if not self._records:
            return None

        return self._records[-1]

    @property
    def last_successful(
        self,
    ) -> ExecutionRecord | None:
        """
        Retorna a execução operacional bem-sucedida
        mais recente.

        Comandos administrativos/contextuais não
        substituem o último resultado operacional.
        """

        for record in reversed(
            self._records
        ):
            if (
                record.success
                and record.operational
            ):
                return record

        return None

    @property
    def last_any_successful(
        self,
    ) -> ExecutionRecord | None:
        """
        Retorna o registro bem-sucedido mais recente,
        incluindo comandos contextuais.
        """

        for record in reversed(
            self._records
        ):
            if record.success:
                return record

        return None

    @property
    def last_operational(
        self,
    ) -> ExecutionRecord | None:
        """
        Retorna a execução operacional mais recente,
        independentemente de sucesso ou erro.
        """

        for record in reversed(
            self._records
        ):
            if record.operational:
                return record

        return None

    def clear(self) -> None:
        """
        Remove todas as execuções armazenadas.
        """

        self._records.clear()

    def __len__(self) -> int:
        return len(self._records)