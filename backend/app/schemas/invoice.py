import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.invoice import EstadoFactura
from app.schemas.client import ClientResponse


class InvoiceItemCreate(BaseModel):
    descripcion: str = Field(min_length=1, max_length=255)
    cantidad: float = Field(gt=0)
    precio_unitario: float = Field(gt=0)


class InvoiceItemResponse(InvoiceItemCreate):
    id: uuid.UUID
    subtotal: float

    model_config = {"from_attributes": True}


class InvoiceCreate(BaseModel):
    client_id: uuid.UUID
    fecha_vencimiento: date
    items: List[InvoiceItemCreate] = Field(min_length=1)


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    serie: str
    numero: int
    fecha_emision: date
    fecha_vencimiento: date
    subtotal: float
    igv: float
    total: float
    estado: EstadoFactura
    client: ClientResponse
    items: List[InvoiceItemResponse]
    dias_mora: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceListItem(BaseModel):
    id: uuid.UUID
    serie: str
    numero: int
    fecha_emision: date
    fecha_vencimiento: date
    total: float
    estado: EstadoFactura
    cliente_nombre: str
    dias_mora: Optional[int] = None

    model_config = {"from_attributes": True}


class RiskAlert(BaseModel):
    nivel: str
    score: float
    mensaje: str
    factores: dict


class InvoiceCreateResponse(BaseModel):
    invoice: InvoiceResponse
    risk_alert: Optional[RiskAlert] = None
