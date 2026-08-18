"""
Gerenciamento de sessões da API Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from threading import RLock
from uuid import uuid4

from kynka import Kynka
from kynka.application.bootstrap import (
    build_default_kynka,
)

from .config import APISettings


@dataclass(slots=True)
class ManagedSession:
    """
    Sessão ativa da API.
    """

    id: str
    kynka: Kynka
    created_at: datetime
    last_access: datetime


class SessionManager:
    """
    Gerencia as instâncias da Kynka associadas
    às sessões da API.
    """

    def __init__(
        self,
        settings: APISettings,
    ) -> None:

        self._settings = settings

        self._sessions: dict[
            str,
            ManagedSession,
        ] = {}

        self._lock = RLock()

    def create(
        self,
    ) -> ManagedSession:

        with self._lock:
            self.cleanup()

            now = datetime.now(
                timezone.utc
            )

            session = ManagedSession(
                id=str(uuid4()),
                kynka=self._build_kynka(),
                created_at=now,
                last_access=now,
            )

            self._sessions[
                session.id
            ] = session

            return session

    def get(
        self,
        session_id: str,
    ) -> ManagedSession | None:

        with self._lock:
            self.cleanup()

            session = self._sessions.get(
                session_id
            )

            if session:
                session.last_access = (
                    datetime.now(
                        timezone.utc
                    )
                )

            return session

    def get_or_create(
        self,
        session_id: str | None,
    ) -> ManagedSession:

        if session_id:
            session = self.get(
                session_id
            )

            if session:
                return session

        return self.create()

    def delete(
        self,
        session_id: str,
    ) -> bool:

        with self._lock:

            session = self._sessions.pop(
                session_id,
                None,
            )

            if session is None:
                return False

            session.kynka.stop()

            return True

    def cleanup(
        self,
    ) -> int:

        limit = (
            datetime.now(timezone.utc)
            - timedelta(
                minutes=(
                    self._settings
                    .session_ttl_minutes
                )
            )
        )

        expired = [
            session_id
            for session_id, session
            in self._sessions.items()
            if session.last_access < limit
        ]

        for session_id in expired:

            session = self._sessions.pop(
                session_id
            )

            session.kynka.stop()

        return len(expired)

    def shutdown(
        self,
    ) -> None:

        with self._lock:

            for session in (
                self._sessions.values()
            ):
                session.kynka.stop()

            self._sessions.clear()

    @property
    def count(
        self,
    ) -> int:

        return len(
            self._sessions
        )

    def _build_kynka(
        self,
    ) -> Kynka:
        """
        Constrói uma Kynka completa para a sessão.

        Todas as sessões compartilham o mesmo banco
        persistente de inventário, mas possuem memória
        conversacional independente.
        """

        return build_default_kynka(
            model=self._settings.model,
            memory_size=(
                self._settings.memory_size
            ),
            database_path="data/kynka.db",
            start=True,
        )