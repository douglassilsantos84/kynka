"""
Contrato base dos Providers da plataforma Kynka.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from kynka.domain.providers.provider_request import (
    ProviderRequest,
)
from kynka.domain.providers.provider_response import (
    ProviderResponse,
)


class Provider(ABC):
    """
    Contrato base para Providers utilizados pela Kynka.

    Um Provider representa uma implementação externa ou local
    capaz de processar uma solicitação da plataforma.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Nome único do Provider.
        """
        ...

    @abstractmethod
    def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        """
        Processa uma solicitação e retorna uma resposta.
        """
        ...