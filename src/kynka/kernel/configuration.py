"""
Configuration Manager
"""

from pathlib import Path


class Configuration:

    def __init__(self) -> None:

        self.root = Path.cwd()

        self.logs = self.root / "logs"

        self.docs = self.root / "docs"

        self.plugins = self.root / "plugins"

    def load(self) -> None:

        self.logs.mkdir(exist_ok=True)

        self.docs.mkdir(exist_ok=True)

        self.plugins.mkdir(exist_ok=True)

        print("✓ Configuração carregada")