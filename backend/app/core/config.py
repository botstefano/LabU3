"""
Configuración de la aplicación.

Centraliza la lectura de variables de entorno para los distintos ambientes
(desarrollo, pruebas, producción), evitando credenciales embebidas en el código.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"

    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    cors_origin_regex: Optional[str] = r"https://.*\.onrender\.com|http://localhost:.*"

    empresa_razon_social: str = "Mi Empresa S.A.C."
    empresa_ruc: str = "20123456789"
    empresa_direccion: str = "Lima, Peru"
    igv_porcentaje: float = 18.0

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def cors_origin_regex_value(self) -> Optional[str]:
        return self.cors_origin_regex or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
