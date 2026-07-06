import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from app.db.guid import GUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AppSetting(Base):
    """Almacena configuraciones persistentes clave-valor del panel de configuración."""

    __tablename__ = "app_settings"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    clave: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    valor: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
