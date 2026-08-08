"""
Ponto de entrada executável da plataforma Kynka.
"""

from kynka import Kynka
from kynka.presentation import KynkaCLI


def main() -> None:
    """
    Inicializa a interface padrão da plataforma.
    """

    kynka = Kynka()

    cli = KynkaCLI(
        kynka
    )

    cli.run()


if __name__ == "__main__":
    main()