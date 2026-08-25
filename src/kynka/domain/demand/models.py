"""
Entidades do domínio de planejamento de demandas da Kynka.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class DemandStatus(str, Enum):
    """
    Estados possíveis de uma demanda.
    """

    DRAFT = "draft"
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class Demand:
    """
    Representa uma demanda empresarial.

    Exemplos:

    - obra;
    - evento;
    - ordem de produção;
    - ordem de serviço.
    """

    code: str
    name: str

    kind: str = "project"

    client: str = ""
    location: str = ""

    start_date: date | None = None

    status: DemandStatus = DemandStatus.DRAFT

    notes: str = ""

    id: int | None = None

    created_at: datetime | None = None


@dataclass(slots=True)
class DemandRequirement:
    """
    Material necessário para atender uma demanda.
    """

    demand_id: int
    material_code: str
    required_quantity: float

    id: int | None = None


@dataclass(slots=True)
class StockReservation:
    """
    Quantidade de estoque reservada para uma demanda.
    """

    demand_id: int
    material_code: str
    quantity: float

    id: int | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None