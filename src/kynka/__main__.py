"""
Ponto de entrada da plataforma Kynka.
"""

from __future__ import annotations

from kynka import Kynka, __version__
from kynka.plugins.calculator import CalculatorPlugin
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
    Executa a demonstração principal da plataforma.
    """

    banner()

    kynka = Kynka()

    try:
        kynka.start()

        kynka.install(
            HelloPluginV2()
        )

        kynka.install(
            CalculatorPlugin()
        )

        print()
        print(
            f"Modelo: {kynka.model}"
        )

        print(
            f"Plugins registrados: "
            f"{len(kynka.plugins)}"
        )

        print(
            f"Capabilities registradas: "
            f"{len(kynka.capabilities)}"
        )

        print()

        greeting_result = kynka.execute(
            "Olá Douglas"
        )

        print(
            "Cumprimento:",
            greeting_result.result,
        )

        calculation_result = kynka.execute(
            "Calcule 125 vezes 37"
        )

        print(
            "Cálculo:",
            calculation_result.result,
        )

        print()

    finally:
        kynka.stop()

    print("Sistema finalizado.")
    print()


if __name__ == "__main__":
    main()