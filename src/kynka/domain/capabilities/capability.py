"""
Contrato base das Capabilities.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from kynka.domain.capabilities.capability_metadata import (
    CapabilityMetadata,
)
from kynka.domain.capabilities.capability_result import (
    CapabilityResult,
)


class Capability(ABC):

    def __init__(
        self,
        metadata: CapabilityMetadata,
    ) -> None:

        self._metadata = metadata

    @property
    def metadata(self) -> CapabilityMetadata:

        return self._metadata

    @property
    def name(self) -> str:

        return self.metadata.name

    @abstractmethod
    def execute(
        self,
        **kwargs: Any,
    ) -> CapabilityResult:
        ...