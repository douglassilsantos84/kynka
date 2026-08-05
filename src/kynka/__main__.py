"""
Ponto de entrada da plataforma Kynka.
"""

from kynka import __version__
from kynka.domain.plugins import HelloPlugin
from kynka.kernel.configuration import Configuration
from kynka.kernel.logger import Logger
from kynka.kernel.runtime import Runtime


def banner() -> None:
    print()
    print("=" * 50)
    print(f"KYNKA PLATFORM {__version__}")
    print("=" * 50)
    print()


def main() -> None:
    banner()

    configuration = Configuration()
    logger = Logger()
    runtime = Runtime()

    configuration.load()
    logger.initialize()
    runtime.start()

    hello_plugin = HelloPlugin()

    runtime.registry.register_plugin(hello_plugin)

    result = hello_plugin.execute(name="Douglas")

    print()
    print(result)
    print()
    print(
        "Plugins registrados:",
        len(runtime.registry.plugins),
    )
    print()

    runtime.stop()

    print()
    print("Sistema finalizado.")
    print()


if __name__ == "__main__":
    main()