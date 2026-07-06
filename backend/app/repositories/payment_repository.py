import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment import Payment


class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def list_by_invoice(self, invoice_id: uuid.UUID):
        return self.db.scalars(select(Payment).where(Payment.invoice_id == invoice_id)).all()

    def total_pagado(self, invoice_id: uuid.UUID) -> float:
        payments = self.list_by_invoice(invoice_id)
        return float(sum(p.monto for p in payments))
