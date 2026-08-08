"""
Ponto de entrada da plataforma Kynka.
"""

from kynka import __version__
from kynka.domain.tasks import Task
from kynka.kernel.configuration import Configuration
from kynka.kernel.logger import Logger
from kynka.kernel.runtime import Runtime
from kynka.plugins.hello.plugin_v2 import HelloPluginV2


def banner() -> None:
    """
    Exibe o banner da plataforma.
    """

    print()
    print("=" * 50)
    print(f"KYNKA PLATFORM {__version__}")
    print("=" * 50)
    print()


def main() -> None:
    """
    Inicializa e executa a plataforma.
    """

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

    task = Task(
        text="Diga olá para Douglas",
        context={
            "name": "Douglas",
        },
    )

    result = runtime.run(task)

    print()

    if result.success:
        print(result.data)
    else:
        print(f"Erro: {result.error}")

    print()
    print(
        f"Capability selecionada: {result.capability}"
    )

    print(
        f"Plugins registrados: {len(runtime.registry.plugins)}"
    )

    print(
        f"Capabilities registradas: "
        f"{len(runtime.registry.capabilities)}"
    )

    runtime.stop()

    print()
    print("Sistema finalizado.")
    print()


if __name__ == "__main__":
    main()