"""Endpoints del módulo de cuentas por cobrar / morosidad."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User, UserRole
from app.routers.deps import get_current_user, require_roles
from app.schemas.payment import DebtSegment, OverdueInvoice, PaymentCreate, PaymentResponse
from app.services.collections_service import CollectionsService

router = APIRouter(prefix="/api/collections", tags=["Cobranzas"])


@router.post("/payments", response_model=PaymentResponse, status_code=201)
def registrar_pago(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMINISTRADOR, UserRole.CONTADOR)),
):
    return CollectionsService(db).registrar_pago(data, registrado_por=current_user.id)


@router.get("/overdue", response_model=List[OverdueInvoice])
def cartera_vencida(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return CollectionsService(db).cartera_vencida()


@router.get("/segments", response_model=List[DebtSegment])
def segmentacion_deuda(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return CollectionsService(db).segmentacion_deuda()
