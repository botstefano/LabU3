import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String
from app.db.guid import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class EstadoFactura(str, enum.Enum):
    PENDIENTE = "pendiente"
    PAGADA = "pagada"
    VENCIDA = "vencida"
    ANULADA = "anulada"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    serie: Mapped[str] = mapped_column(String(4), nullable=False, default="F001")
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("clients.id"), nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    igv: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    estado: Mapped[EstadoFactura] = mapped_column(
        Enum(EstadoFactura, name="estado_factura"), nullable=False, default=EstadoFactura.PENDIENTE
    )
    created_by: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    client = relationship("Client", lazy="joined")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

    __table_args__ = ()


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("invoices.id"), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    cantidad: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=1)
    precio_unitario: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    invoice = relationship("Invoice", back_populates="items")
