import uuid
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.client import Client


class ClientRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, client_id: uuid.UUID) -> Optional[Client]:
        return self.db.get(Client, client_id)

    def get_by_documento(self, numero_documento: str) -> Optional[Client]:
        return self.db.scalar(select(Client).where(Client.numero_documento == numero_documento))

    def list(self, search: Optional[str] = None, skip: int = 0, limit: int = 50):
        query = select(Client)
        if search:
            like = f"%{search}%"
            query = query.where(
                or_(Client.nombre_razon_social.ilike(like), Client.numero_documento.ilike(like))
            )
        query = query.order_by(Client.created_at.desc()).offset(skip).limit(limit)
        return self.db.scalars(query).all()

    def create(self, client: Client) -> Client:
        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)
        return client

    def update(self, client: Client) -> Client:
        self.db.commit()
        self.db.refresh(client)
        return client

    def delete(self, client: Client) -> None:
        self.db.delete(client)
        self.db.commit()
