"""Servicio de negocio para el panel de configuración persistente."""
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories.settings_repository import SettingsRepository

DEFAULT_KEYS = {
    "empresa_razon_social": None,
    "empresa_ruc": None,
    "empresa_direccion": None,
    "igv_porcentaje": None,
    "notificaciones_morosidad_activas": "true",
    "dias_aviso_morosidad": "7",
}


class SettingsService:
    def __init__(self, db: Session):
        self.repo = SettingsRepository(db)
        self.app_settings = get_settings()

    def get_all(self) -> dict:
        stored = self.repo.get_all()
        defaults = {
            "empresa_razon_social": self.app_settings.empresa_razon_social,
            "empresa_ruc": self.app_settings.empresa_ruc,
            "empresa_direccion": self.app_settings.empresa_direccion,
            "igv_porcentaje": str(self.app_settings.igv_porcentaje),
            "notificaciones_morosidad_activas": "true",
            "dias_aviso_morosidad": "7",
        }
        defaults.update(stored)
        return defaults

    def update(self, valores: dict) -> dict:
        return self.repo.upsert_many(valores)
