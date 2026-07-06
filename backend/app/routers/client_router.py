"""Endpoints CRUD de clientes."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User, UserRole
from app.routers.deps import get_current_user, require_roles
from app.schemas.client import ClientCreate, ClientResponse, ClientUpdate
from app.services.client_service import ClientService

router = APIRouter(prefix="/api/clients", tags=["Clientes"])


@router.post("", response_model=ClientResponse, status_code=201)
def create_client(
    data: ClientCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMINISTRADOR, UserRole.VENDEDOR, UserRole.CONTADOR)),
):
    return ClientService(db).create(data)


@router.get("", response_model=List[ClientResponse])
def list_clients(
    search: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ClientService(db).list(search=search, skip=skip, limit=limit)


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ClientService(db).get(client_id)


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: uuid.UUID,
    data: ClientUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMINISTRADOR, UserRole.VENDEDOR, UserRole.CONTADOR)),
):
    return ClientService(db).update(client_id, data)


@router.delete("/{client_id}", status_code=204)
def delete_client(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMINISTRADOR)),
):
    ClientService(db).delete(client_id)
