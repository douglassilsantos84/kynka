"""
Logger da plataforma.
"""

import logging


class Logger:

    def __init__(self) -> None:

        self.logger = logging.getLogger("kynka")

    def initialize(self) -> None:

        logging.basicConfig(

            level=logging.INFO,

            format="%(asctime)s | %(levelname)s | %(message)s",

        )

        print("✓ Logger inicializado")

    def info(self, message: str) -> None:

        self.logger.info(message)

    def error(self, message: str) -> None:

        self.logger.error(message)