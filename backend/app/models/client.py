import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String
from app.db.guid import GUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TipoDocumento(str, enum.Enum):
    DNI = "DNI"
    RUC = "RUC"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    tipo_documento: Mapped[TipoDocumento] = mapped_column(Enum(TipoDocumento, name="tipo_documento"), nullable=False)
    numero_documento: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    nombre_razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    direccion: Mapped[str] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(150), nullable=True)
    telefono: Mapped[str] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
