from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class APISettings:
    app_name: str = "Kynka API"
    version: str = "6.0.0"
    model: str = "llama3.2:3b"
    memory_size: int = 100
    session_ttl_minutes: int = 120
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:3000", "http://127.0.0.1:3000",
    )

    @classmethod
    def from_env(cls) -> "APISettings":
        origins = tuple(x.strip() for x in os.getenv("KYNKA_CORS_ORIGINS", "").split(",") if x.strip())
        return cls(
            app_name=os.getenv("KYNKA_APP_NAME", "Kynka API"),
            version=os.getenv("KYNKA_VERSION", "6.0.0"),
            model=os.getenv("KYNKA_MODEL", "llama3.2:3b"),
            memory_size=int(os.getenv("KYNKA_MEMORY_SIZE", "100")),
            session_ttl_minutes=int(os.getenv("KYNKA_SESSION_TTL_MINUTES", "120")),
            cors_origins=origins or cls().cors_origins,
        )
