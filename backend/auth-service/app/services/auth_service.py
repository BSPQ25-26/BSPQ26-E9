from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.repositories.user_repository import UserRepository
from app.core.security import hash_password, verify_password, create_access_token


class AuthService:

    def __init__(self):
        self.user_repository = UserRepository()

    def register(self, db: Session, email: str, password: str):
        existing_user = self.user_repository.get_user_by_email(db, email)

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario ya existe"
            )

        password_hash = hash_password(password)

        user = self.user_repository.create_user(db, email, password_hash)

        token = create_access_token({"sub": user.email})

        return {
            "message": "usuario creado correctamente",
            "access_token": token,
            "token_type": "bearer"
        }

    def login(self, db: Session, email: str, password: str):
        user = self.user_repository.get_user_by_email(db, email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )

        # Si el usuario se registró con OAuth no tiene contraseña
        if not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Esta cuenta usa login social. Accede con Google o Facebook."
            )

        if not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )

        token = create_access_token({"sub": user.email})
        return {
            "message": "login correcto",
            "access_token": token,
            "token_type": "bearer"
        }