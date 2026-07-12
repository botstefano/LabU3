
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User, UserRole
from app.routers.deps import get_current_user, require_roles
from app.schemas.risk import ClientRiskResponse, TrainRiskResponse
from app.services.risk_service import RiskService

router = APIRouter(prefix="/api/risk", tags=["Riesgo de Morosidad (IA)"])


@router.post("/train", response_model=TrainRiskResponse)
def train_model(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMINISTRADOR, UserRole.CONTADOR)),
):
    return RiskService(db).train()


@router.get("/clients", response_model=List[ClientRiskResponse])
def list_clients_risk(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return RiskService(db).score_all_clients()


@router.get("/clients/{client_id}", response_model=ClientRiskResponse)
def get_client_risk(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return RiskService(db).score_client(client_id)

