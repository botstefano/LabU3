"""
Dependencias reutilizables de FastAPI.

Provee la extracción del usuario autenticado a partir del JWT y un
generador de dependencias para restringir endpoints por rol.
"""
import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if not token:
        raise UnauthorizedError("No se proporciono token de autenticacion")
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise UnauthorizedError(str(exc)) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Token invalido")

    user = UserRepository(db).get_by_id(uuid.UUID(user_id))
    if not user or not user.activo:
        raise UnauthorizedError("Usuario no encontrado o inactivo")
    return user


def require_roles(*roles: UserRole):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if roles and user.rol not in roles:
            raise ForbiddenError("No tiene permisos suficientes para esta accion")
        return user

    return dependency
