from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.auth import RegisterRequest, LoginRequest
from app.services.auth_service import AuthService
from app.api.deps import get_current_user
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

auth_service = AuthService()


@router.get("/test")
def test_auth():
    return {"message": "auth router funcionando"}


@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return auth_service.register(db, data.email, data.password)


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.login(db, data.email, data.password)


@router.get("/protected")
def protected_route(current_user: str = Depends(get_current_user)):
    return {
        "message": "acceso permitido",
        "user": current_user
    }