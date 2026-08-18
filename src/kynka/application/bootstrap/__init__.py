"""
Bootstrap da plataforma Kynka.
"""

from .default_kynka import (
    DEFAULT_DATABASE_PATH,
    build_default_kynka,
)

__all__ = [
    "DEFAULT_DATABASE_PATH",
    "build_default_kynka",
]