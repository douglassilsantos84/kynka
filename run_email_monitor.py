from dotenv import load_dotenv

load_dotenv()

from kynka.application.email_quotes import (
    EmailQuoteConfig,
    EmailQuoteMonitor,
    EmailQuoteService,
)
from kynka.infrastructure.email_quotes import SQLiteEmailQuoteRepository
from kynka.presentation.api.app import DATABASE_PATH, create_app


def main():
    app = create_app()

    config = EmailQuoteConfig()

    print("==========================================")
    print(" KYNKA - EMAIL QUOTE MONITOR")
    print("==========================================")
    print(f"E-mail: {config.username or 'não configurado'}")
    print(f"Servidor: {config.host or 'não configurado'}")
    print(f"Caixa: {config.mailbox}")
    print(f"Automação ativa: {config.enabled}")
    print(f"Configuração completa: {config.configured}")
    print("==========================================")

    if not config.enabled:
        print("ERRO: KYNKA_EMAIL_ENABLED não está ativado.")
        return

    if not config.configured:
        print("ERRO: configuração de e-mail incompleta.")
        return

    service = EmailQuoteService(
        SQLiteEmailQuoteRepository(DATABASE_PATH),
        DATABASE_PATH,
        app.state.supplier_service,
        app.state.inventory_service,
        config,
    )

    EmailQuoteMonitor(service).run_forever()


if __name__ == "__main__":
    main()
