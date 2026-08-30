from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ["KYNKA_EMBEDDING_MODEL"] = ""
os.environ["KYNKA_DOCUMENT_CHAT_MODEL"] = ""

from kynka.application.documents import DocumentService
from kynka.infrastructure.documents import SQLiteDocumentRepository


def main():
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        repo = SQLiteDocumentRepository(base / "test.db")
        service = DocumentService(repo, base / "documents")

        content = (
            "PROPOSTA COMERCIAL KYNKA\n"
            "Fornecedor: Material Teste Lda\n"
            "NIF: 509123456\n"
            "Prazo de entrega: 12 dias.\n"
            "Valor total: 1.250,00 €.\n"
            "Referência: MAT-C16-001\n"
        ).encode("utf-8")

        document = service.upload(
            file_name="proposta_teste.txt",
            content=content,
            mime_type="text/plain",
        )

        assert document["id"] == 1
        assert document["category"] in {"cotacao", "geral"}
        assert "509123456" in document["metadata"]["nifs"]

        results = service.search(
            "qual é o prazo de entrega",
            limit=3,
        )
        assert results
        assert results[0]["document_id"] == 1

        answer = service.ask(
            "Qual é o prazo de entrega?",
            limit=3,
        )
        assert answer["sources"]
        assert answer["grounded"] is True

        stats = service.stats()
        assert stats["documents"] == 1
        assert stats["chunks"] >= 1

        print("ETAPA 22 CORE: OK")
        print("Documento:", document["id"])
        print("Categoria:", document["category"])
        print("Chunks:", stats["chunks"])
        print("Busca RAG:", results[0]["score"])
        print("Modo resposta:", answer["mode"])


if __name__ == "__main__":
    main()
