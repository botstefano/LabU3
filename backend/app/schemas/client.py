import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.client import TipoDocumento


class ClientBase(BaseModel):
    tipo_documento: TipoDocumento
    numero_documento: str
    nombre_razon_social: str = Field(min_length=2, max_length=200)
    direccion: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None

    @field_validator("numero_documento")
    @classmethod
    def validar_documento(cls, value: str, info):
        tipo = info.data.get("tipo_documento")
        digits = value.strip()
        if not digits.isdigit():
            raise ValueError("El numero de documento debe contener solo digitos")
        if tipo == TipoDocumento.DNI and len(digits) != 8:
            raise ValueError("El DNI debe tener 8 digitos")
        if tipo == TipoDocumento.RUC and len(digits) != 11:
            raise ValueError("El RUC debe tener 11 digitos")
        return digits


class ClientCreate(ClientBase):
    pass


class ClientUpdate(ClientBase):
    pass


class ClientResponse(ClientBase):
    id: uuid.UUID
    created_at: datetime
    riesgo_heuristico: Optional[dict] = None

    model_config = {"from_attributes": True}
