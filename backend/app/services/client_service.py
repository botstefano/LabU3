"""Servicio de negocio para la gestión de clientes (CRUD y validaciones)."""
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.client import Client
from app.repositories.client_repository import ClientRepository
from app.schemas.client import ClientCreate, ClientUpdate


class ClientService:
    def __init__(self, db: Session):
        self.repo = ClientRepository(db)

    def create(self, data: ClientCreate) -> Client:
        if self.repo.get_by_documento(data.numero_documento):
            raise ConflictError("Ya existe un cliente con ese numero de documento")
        client = Client(**data.model_dump())
        return self.repo.create(client)

    def get(self, client_id: uuid.UUID) -> Client:
        client = self.repo.get_by_id(client_id)
        if not client:
            raise NotFoundError("Cliente no encontrado")
        return client

    def list(self, search: Optional[str], skip: int, limit: int):
        return self.repo.list(search=search, skip=skip, limit=limit)

    def update(self, client_id: uuid.UUID, data: ClientUpdate) -> Client:
        client = self.get(client_id)
        existing = self.repo.get_by_documento(data.numero_documento)
        if existing and existing.id != client.id:
            raise ConflictError("Ya existe otro cliente con ese numero de documento")
        for field, value in data.model_dump().items():
            setattr(client, field, value)
        return self.repo.update(client)

    def delete(self, client_id: uuid.UUID) -> None:
        client = self.get(client_id)
        self.repo.delete(client)
