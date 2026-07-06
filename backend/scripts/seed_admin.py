"""
Script de siembra (seed) para crear el primer usuario administrador.

Uso:
    python scripts/seed_admin.py
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models.user import User, UserRole


def main():
    db = SessionLocal()
    try:
        email = input("Correo del administrador: ").strip()
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print("Ya existe un usuario con ese correo.")
            return

        nombre = input("Nombre completo: ").strip()
        password = input("Contrasena (minimo 6 caracteres): ").strip()

        admin = User(
            nombre=nombre,
            email=email,
            password_hash=hash_password(password),
            rol=UserRole.ADMINISTRADOR,
            activo=True,
        )
        db.add(admin)
        db.commit()
        print(f"Usuario administrador '{email}' creado correctamente.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
