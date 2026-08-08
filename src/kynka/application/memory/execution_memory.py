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
        Retorna a última execução registrada.
        """

        if not self._records:
            return None

        return self._records[-1]

    @property
    def last_successful(
        self,
    ) -> ExecutionRecord | None:
        """
        Retorna a execução bem-sucedida mais recente.
        """

        for record in reversed(
            self._records
        ):
            if record.success:
                return record

        return None

    def clear(self) -> None:
        """
        Remove todas as execuções armazenadas.
        """

        self._records.clear()

    def __len__(self) -> int:
        return len(self._records)