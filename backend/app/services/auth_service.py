"""Servicio de negocio para autenticación y gestión de usuarios."""
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, UserCreate


class AuthService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def login(self, data: LoginRequest) -> tuple[str, User]:
        user = self.repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.password_hash):
            raise UnauthorizedError("Credenciales invalidas")
        if not user.activo:
            raise UnauthorizedError("Usuario inactivo. Contacte al administrador")
        token = create_access_token(subject=str(user.id), role=user.rol.value)
        return token, user

    def register(self, data: UserCreate) -> User:
        if self.repo.get_by_email(data.email):
            raise ConflictError("Ya existe un usuario con ese correo")
        user = User(
            nombre=data.nombre,
            email=data.email,
            password_hash=hash_password(data.password),
            rol=data.rol,
        )
        return self.repo.create(user)

    def list_users(self):
        return self.repo.list_all()
