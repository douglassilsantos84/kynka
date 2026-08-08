"""
Provider Ollama da plataforma Kynka.
"""

from __future__ import annotations

import json
from urllib import error, request

from kynka.domain.providers import (
    Provider,
    ProviderRequest,
    ProviderResponse,
)


class OllamaProvider(Provider):
    """
    Implementação de Provider para um servidor Ollama local.
    """

    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        timeout: float = 120.0,
    ) -> None:
        model = model.strip()
        base_url = base_url.strip().rstrip("/")

        if not model:
            raise ValueError(
                "O modelo do Ollama não pode estar vazio."
            )

        if not base_url:
            raise ValueError(
                "A URL do Ollama não pode estar vazia."
            )

        self._model = model
        self._base_url = base_url
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    def generate(
        self,
        provider_request: ProviderRequest,
    ) -> ProviderResponse:
        """
        Envia o prompt para o Ollama e converte a resposta
        para o formato interno ProviderResponse.
        """

        payload = {
            "model": self._model,
            "prompt": provider_request.prompt,
            "stream": False,
        }

        body = json.dumps(payload).encode("utf-8")

        http_request = request.Request(
            url=f"{self._base_url}/api/generate",
            data=body,
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(
                http_request,
                timeout=self._timeout,
            ) as response:
                response_body = response.read().decode(
                    "utf-8"
                )

            data = json.loads(response_body)

            content = data.get("response")

            if not isinstance(content, str):
                return ProviderResponse(
                    success=False,
                    error=(
                        "O Ollama retornou uma resposta "
                        "sem conteúdo válido."
                    ),
                    metadata=data,
                )

            return ProviderResponse(
                success=True,
                content=content.strip(),
                metadata={
                    "provider": self.name,
                    "model": data.get(
                        "model",
                        self._model,
                    ),
                    "done": data.get("done"),
                    "total_duration": data.get(
                        "total_duration"
                    ),
                    "eval_count": data.get(
                        "eval_count"
                    ),
                },
            )

        except error.HTTPError as exc:
            return ProviderResponse(
                success=False,
                error=(
                    "Erro HTTP ao comunicar com o Ollama: "
                    f"{exc.code} {exc.reason}"
                ),
                metadata={
                    "provider": self.name,
                    "model": self._model,
                },
            )

        except error.URLError as exc:
            return ProviderResponse(
                success=False,
                error=(
                    "Não foi possível conectar ao Ollama: "
                    f"{exc.reason}"
                ),
                metadata={
                    "provider": self.name,
                    "model": self._model,
                },
            )

        except TimeoutError:
            return ProviderResponse(
                success=False,
                error="A comunicação com o Ollama excedeu o tempo limite.",
                metadata={
                    "provider": self.name,
                    "model": self._model,
                },
            )

        except json.JSONDecodeError:
            return ProviderResponse(
                success=False,
                error="O Ollama retornou JSON inválido.",
                metadata={
                    "provider": self.name,
                    "model": self._model,
                },
            )