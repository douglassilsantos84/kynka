"""
Ponto de entrada da plataforma Kynka.
"""

from kynka import __version__

from kynka.kernel.configuration import Configuration
from kynka.kernel.logger import Logger
from kynka.kernel.runtime import Runtime

from kynka.plugins.hello.plugin_v2 import HelloPluginV2


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

    runtime.register_plugin(
        HelloPluginV2()
    )

    resultado = runtime.execute(
        capability="greeting.hello",
        name="Douglas",
    )

    print()

    print(resultado.data)

    print()

    print(
        f"Plugins registrados: {len(runtime.registry.plugins)}"
    )

    print(
        f"Capabilities registradas: {len(runtime.registry.capabilities)}"
    )

    runtime.stop()

    print()

    print("Sistema finalizado.")

    print()


if __name__ == "__main__":
    main()