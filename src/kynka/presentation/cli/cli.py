"""
Interface de linha de comando da plataforma Kynka.
"""

from __future__ import annotations

from kynka import Kynka, __version__
from kynka.plugins.calculator import CalculatorPlugin
from kynka.plugins.hello.plugin_v2 import HelloPluginV2


class KynkaCLI:
    """
    Interface interativa de linha de comando da Kynka.

    Esta classe pertence exclusivamente à camada
    de apresentação. A execução agêntica continua
    sendo responsabilidade da plataforma.
    """

    def __init__(
        self,
        kynka: Kynka,
    ) -> None:
        self._kynka = kynka

    def run(self) -> None:
        """
        Executa a interface interativa.
        """

        self._show_banner()

        try:
            self._kynka.start()

            self._install_plugins()

            self._show_status()

            print("Kynka pronta.")
            print(
                "Digite 'ajuda' para ver os comandos "
                "ou 'sair' para finalizar."
            )
            print()

            self._interactive_loop()

        finally:
            self._kynka.stop()

        print()
        print("Sistema finalizado.")
        print()

    def _install_plugins(self) -> None:
        """
        Instala os Plugins padrão da CLI.
        """

        self._kynka.install(
            HelloPluginV2()
        )

        self._kynka.install(
            CalculatorPlugin()
        )

    def _interactive_loop(self) -> None:
        """
        Mantém a interface ativa até o usuário sair.
        """

        while True:
            try:
                text = input(
                    "Kynka > "
                ).strip()

            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not text:
                continue

            if text.lower() in {
                "sair",
                "exit",
                "quit",
            }:
                break

            if self._process_internal_command(
                text
            ):
                continue

            result = self._kynka.execute(
                text
            )

            if result.success:
                print(result.result)
            else:
                print(
                    f"Erro: {result.error}"
                )

            print()

    def _process_internal_command(
        self,
        command: str,
    ) -> bool:
        """
        Processa comandos pertencentes à própria CLI.
        """

        normalized = (
            command.strip().lower()
        )

        if normalized == "ajuda":
            self._show_help()
            return True

        if normalized == "status":
            self._show_status()
            return True

        if normalized == "plugins":
            self._show_plugins()
            return True

        if normalized == "capabilities":
            self._show_capabilities()
            return True

        if normalized in {
            "memoria",
            "memória",
        }:
            self._show_memory()
            return True

        if normalized in {
            "limpar memoria",
            "limpar memória",
        }:
            self._clear_memory()
            return True

        return False

    def _show_banner(self) -> None:
        """
        Exibe o banner da plataforma.
        """

        print()
        print("=" * 50)
        print(
            f"KYNKA PLATFORM {__version__}"
        )
        print("=" * 50)
        print()

    def _show_status(self) -> None:
        """
        Exibe o estado atual da plataforma.
        """

        print(
            f"Modelo: {self._kynka.model}"
        )

        print(
            "Plugins registrados: "
            f"{len(self._kynka.plugins)}"
        )

        print(
            "Capabilities registradas: "
            f"{len(self._kynka.capabilities)}"
        )

        print(
            "Execuções na memória: "
            f"{len(self._kynka.memory)}"
        )

        print()

    def _show_plugins(self) -> None:
        """
        Lista os Plugins instalados.
        """

        print()

        if not self._kynka.plugins:
            print(
                "Nenhum Plugin instalado."
            )
        else:
            print("Plugins instalados:")

            for plugin in self._kynka.plugins:
                print(
                    f"  - {plugin}"
                )

        print()

    def _show_capabilities(self) -> None:
        """
        Lista as Capabilities disponíveis.
        """

        print()

        if not self._kynka.capabilities:
            print(
                "Nenhuma Capability disponível."
            )
        else:
            print(
                "Capabilities disponíveis:"
            )

            for capability in (
                self._kynka.capabilities
            ):
                print(
                    f"  - {capability}"
                )

        print()

    def _show_memory(self) -> None:
        """
        Exibe o histórico de execuções
        armazenado na memória da sessão.
        """

        records = self._kynka.memory.records

        print()

        if not records:
            print(
                "A memória da sessão está vazia."
            )
            print()
            return

        print("Histórico da sessão:")
        print()

        for index, record in enumerate(
            records,
            start=1,
        ):
            print(
                f"{index}. "
                f"{record.capability or 'sem capability'}"
            )

            print(
                f"   Solicitação: {record.text}"
            )

            if record.arguments is not None:
                print(
                    "   Argumentos: "
                    f"{record.arguments}"
                )

            if record.success:
                print(
                    f"   Resultado: {record.result}"
                )
            else:
                print(
                    f"   Erro: {record.error}"
                )

            print()

    def _clear_memory(self) -> None:
        """
        Limpa a memória da sessão.
        """

        quantity = len(
            self._kynka.memory
        )

        self._kynka.memory.clear()

        print()

        if quantity == 0:
            print(
                "A memória já estava vazia."
            )
        else:
            print(
                "Memória da sessão limpa."
            )

        print()

    @staticmethod
    def _show_help() -> None:
        """
        Exibe os comandos internos.
        """

        print()
        print("Comandos disponíveis:")

        print(
            "  ajuda           "
            "Exibe esta ajuda."
        )

        print(
            "  status          "
            "Exibe o estado da plataforma."
        )

        print(
            "  plugins         "
            "Lista os Plugins instalados."
        )

        print(
            "  capabilities    "
            "Lista as Capabilities disponíveis."
        )

        print(
            "  memoria         "
            "Exibe o histórico da sessão."
        )

        print(
            "  limpar memoria  "
            "Limpa o histórico da sessão."
        )

        print(
            "  sair            "
            "Finaliza a Kynka."
        )

        print()