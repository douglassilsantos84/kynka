"""
Interface de linha de comando da plataforma Kynka.
"""

from __future__ import annotations

from kynka import Kynka, __version__
from kynka.application.planning import PlanExecutionResult
from kynka.plugins.calculator import CalculatorPlugin
from kynka.plugins.hello.plugin_v2 import HelloPluginV2


class KynkaCLI:
    """
    Interface interativa de linha de comando da Kynka.
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

            try:
                result = self._kynka.run(
                    text
                )

            except Exception as error:
                print(
                    f"Erro: {error}"
                )
                print()
                continue

            if not result.success:
                print(
                    f"Erro: {result.error}"
                )
                print()
                continue

            if isinstance(
                result,
                PlanExecutionResult,
            ):
                self._show_plan_result(
                    result
                )
            else:
                print(
                    result.result
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

        if normalized in {
            "variaveis",
            "variáveis",
        }:
            self._show_variables()
            return True

        if normalized in {
            "limpar variaveis",
            "limpar variáveis",
        }:
            self._clear_variables()
            return True

        if normalized == "contexto":
            self._show_context()
            return True

        return False

    def _show_plan_result(
        self,
        result: PlanExecutionResult,
    ) -> None:
        """
        Exibe o resultado de uma execução planejada.
        """

        print(
            f"Resultado: {result.result}"
        )

        print("Etapas:")

        for step in result.steps:
            print(
                f"  {step.step_id}: "
                f"{step.capability} "
                f"-> {step.result}"
            )

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

        print(
            "Variáveis no contexto: "
            f"{len(self._kynka.context.variables)}"
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
            print(
                "Plugins instalados:"
            )

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
        Exibe o histórico de execuções armazenado
        na memória da sessão.
        """

        records = (
            self._kynka.memory.records
        )

        print()

        if not records:
            print(
                "A memória da sessão está vazia."
            )
            print()
            return

        print(
            "Histórico da sessão:"
        )
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
                f"{quantity} execuções removidas."
            )

        print()

    def _show_variables(self) -> None:
        """
        Lista as variáveis armazenadas
        no contexto da sessão.
        """

        variables = (
            self._kynka.context.variables
        )

        print()

        if not variables:
            print(
                "Nenhuma variável armazenada."
            )
            print()
            return

        print(
            "Variáveis do contexto:"
        )
        print()

        for name, value in (
            variables.items()
        ):
            print(
                f"{name} = {value}"
            )

        print()

    def _clear_variables(self) -> None:
        """
        Remove todas as variáveis
        armazenadas no contexto.
        """

        quantity = len(
            self._kynka.context.variables
        )

        self._kynka.context.clear_variables()

        print()

        if quantity == 0:
            print(
                "Nenhuma variável para remover."
            )
        elif quantity == 1:
            print(
                "1 variável removida."
            )
        else:
            print(
                f"{quantity} variáveis removidas."
            )

        print()

    def _show_context(self) -> None:
        """
        Exibe o contexto atual da sessão.
        """

        context = self._kynka.context
        variables = context.variables
        memory = context.memory

        print()
        print(
            "Contexto atual:"
        )
        print()

        print(
            f"Variáveis: {len(variables)}"
        )

        print(
            "Execuções na memória: "
            f"{len(memory)}"
        )

        last = memory.last

        if last is not None:
            print(
                f"Última execução: {last.text}"
            )

            if last.success:
                print(
                    "Último status: sucesso"
                )
            else:
                print(
                    "Último status: erro"
                )

        last_successful = (
            memory.last_successful
        )

        if last_successful is not None:
            print(
                "Último resultado: "
                f"{last_successful.result}"
            )

        if variables:
            print()
            print("Estado:")

            for name, value in (
                variables.items()
            ):
                print(
                    f"{name} = {value}"
                )

        print()

    @staticmethod
    def _show_help() -> None:
        """
        Exibe os comandos internos.
        """

        print()
        print(
            "Comandos disponíveis:"
        )

        print(
            "  ajuda             "
            "Exibe esta ajuda."
        )

        print(
            "  status            "
            "Exibe o estado da plataforma."
        )

        print(
            "  plugins           "
            "Lista os Plugins instalados."
        )

        print(
            "  capabilities      "
            "Lista as Capabilities disponíveis."
        )

        print(
            "  memoria           "
            "Exibe o histórico da sessão."
        )

        print(
            "  limpar memoria    "
            "Limpa o histórico da sessão."
        )

        print(
            "  variaveis         "
            "Lista as variáveis do contexto."
        )

        print(
            "  limpar variaveis  "
            "Remove as variáveis do contexto."
        )

        print(
            "  contexto          "
            "Exibe o contexto atual."
        )

        print(
            "  sair              "
            "Finaliza a Kynka."
        )

        print()