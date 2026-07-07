import uuid
from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.invoice import EstadoFactura, Invoice


class InvoiceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, invoice_id: uuid.UUID) -> Optional[Invoice]:
        return self.db.get(Invoice, invoice_id)

    def next_numero(self, serie: str = "F001") -> int:
        max_numero = self.db.scalar(select(func.max(Invoice.numero)).where(Invoice.serie == serie))
        return (max_numero or 0) + 1

    def create(self, invoice: Invoice) -> Invoice:
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def update(self, invoice: Invoice) -> Invoice:
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def list(
        self,
        estado: Optional[EstadoFactura] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        client_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ):
        query = select(Invoice)
        if estado:
            query = query.where(Invoice.estado == estado)
        if fecha_desde:
            query = query.where(Invoice.fecha_emision >= fecha_desde)
        if fecha_hasta:
            query = query.where(Invoice.fecha_emision <= fecha_hasta)
        if client_id:
            query = query.where(Invoice.client_id == client_id)
        query = query.order_by(Invoice.fecha_emision.desc()).offset(skip).limit(limit)
        return self.db.scalars(query).all()

    def list_pendientes_vencidas(self):
        query = select(Invoice).where(Invoice.estado.in_([EstadoFactura.PENDIENTE, EstadoFactura.VENCIDA]))
        return self.db.scalars(query).all()

    def list_all_in_range(self, fecha_desde: date, fecha_hasta: date):
        query = select(Invoice).where(
            Invoice.fecha_emision >= fecha_desde, Invoice.fecha_emision <= fecha_hasta
        )
        return self.db.scalars(query).all()
