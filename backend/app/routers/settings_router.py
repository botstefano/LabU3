"""Endpoints del panel de configuración persistente."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User, UserRole
from app.routers.deps import require_roles
from app.schemas.settings_schema import SettingsResponse, SettingsUpdate
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/api/settings", tags=["Configuracion"])


@router.get("", response_model=SettingsResponse)
def get_settings_values(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMINISTRADOR)),
):
    return SettingsResponse(valores=SettingsService(db).get_all())


@router.put("", response_model=SettingsResponse)
def update_settings_values(
    data: SettingsUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMINISTRADOR)),
):
    return SettingsResponse(valores=SettingsService(db).update(data.valores))
