from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.settings_model import AppSetting


class SettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> dict:
        rows = self.db.scalars(select(AppSetting)).all()
        return {row.clave: row.valor for row in rows}

    def upsert_many(self, valores: dict) -> dict:
        for clave, valor in valores.items():
            existing = self.db.scalar(select(AppSetting).where(AppSetting.clave == clave))
            if existing:
                existing.valor = valor
            else:
                self.db.add(AppSetting(clave=clave, valor=valor))
        self.db.commit()
        return self.get_all()
