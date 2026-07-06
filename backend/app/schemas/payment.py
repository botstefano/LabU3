import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    invoice_id: uuid.UUID
    monto: float = Field(gt=0)
    metodo_pago: str = Field(default="transferencia", max_length=50)
    fecha_pago: date = Field(default_factory=date.today)


class PaymentResponse(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    monto: float
    metodo_pago: str
    fecha_pago: date
    created_at: datetime

    model_config = {"from_attributes": True}


class DebtSegment(BaseModel):
    segmento: str
    cantidad_facturas: int
    monto_total: float


class OverdueInvoice(BaseModel):
    id: uuid.UUID
    serie: str
    numero: int
    cliente_nombre: str
    fecha_vencimiento: date
    dias_mora: int
    total: float
    saldo_pendiente: float

    model_config = {"from_attributes": True}
