"""
Boot da plataforma Kynka.
"""

from __future__ import annotations

from kynka.kernel.configuration import Configuration
from kynka.kernel.logger import Logger
from kynka.kernel.plugin_loader import PluginLoader
from kynka.kernel.runtime import Runtime

from kynka.plugins.hello.plugin_v2 import HelloPluginV2


class Boot:

    def __init__(self) -> None:

        self.configuration = Configuration()

        self.logger = Logger()

        self.runtime = Runtime()

        self.loader = PluginLoader(
            self.runtime.registry
        )

    def start(self) -> Runtime:

        self.configuration.load()

        self.logger.initialize()

        self.runtime.start()

        self.loader.load(
            HelloPluginV2()
        )

        return self.runtime

    def stop(self) -> None:

        self.runtime.stop()