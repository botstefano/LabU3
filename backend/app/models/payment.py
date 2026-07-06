import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from app.db.guid import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("invoices.id"), nullable=False)
    fecha_pago: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    monto: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    metodo_pago: Mapped[str] = mapped_column(String(50), nullable=False, default="transferencia")
    registrado_por: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="payments")
