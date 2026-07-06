"""Endpoint del dashboard analítico."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
def resumen_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return DashboardService(db).resumen()
