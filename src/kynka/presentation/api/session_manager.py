from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import RLock
from uuid import uuid4
from kynka import Kynka
from kynka.plugins.calculator import CalculatorPlugin
from kynka.plugins.hello.plugin_v2 import HelloPluginV2
from .config import APISettings

@dataclass(slots=True)
class ManagedSession:
    id: str
    kynka: Kynka
    created_at: datetime
    last_access: datetime

class SessionManager:
    def __init__(self, settings: APISettings) -> None:
        self._settings = settings
        self._sessions: dict[str, ManagedSession] = {}
        self._lock = RLock()

    def create(self) -> ManagedSession:
        with self._lock:
            self.cleanup()
            now = datetime.now(timezone.utc)
            s = ManagedSession(str(uuid4()), self._build_kynka(), now, now)
            self._sessions[s.id] = s
            return s

    def get(self, session_id: str) -> ManagedSession | None:
        with self._lock:
            self.cleanup()
            s = self._sessions.get(session_id)
            if s:
                s.last_access = datetime.now(timezone.utc)
            return s

    def get_or_create(self, session_id: str | None) -> ManagedSession:
        if session_id:
            s = self.get(session_id)
            if s:
                return s
        return self.create()

    def delete(self, session_id: str) -> bool:
        with self._lock:
            s = self._sessions.pop(session_id, None)
            if not s:
                return False
            s.kynka.stop()
            return True

    def cleanup(self) -> int:
        limit = datetime.now(timezone.utc) - timedelta(minutes=self._settings.session_ttl_minutes)
        expired = [sid for sid, s in self._sessions.items() if s.last_access < limit]
        for sid in expired:
            self._sessions.pop(sid).kynka.stop()
        return len(expired)

    def shutdown(self) -> None:
        with self._lock:
            for s in self._sessions.values():
                s.kynka.stop()
            self._sessions.clear()

    @property
    def count(self) -> int:
        return len(self._sessions)

    def _build_kynka(self) -> Kynka:
        k = Kynka(model=self._settings.model, memory_size=self._settings.memory_size)
        k.start()
        k.install(HelloPluginV2())
        k.install(CalculatorPlugin())
        return k
