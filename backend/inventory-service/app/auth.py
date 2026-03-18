from fastapi import Depends, HTTPException, status, Header
from typing import Optional

# Dummy user for testing
class User:
    def __init__(self, id: int):
        self.id = id

# Simula autenticación por token
def get_current_user(authorization: Optional[str] = Header(None)):
    # En un entorno real, validarías el token JWT aquí
    # Para test, si hay header Authorization, devuelve un usuario simulado
    if authorization == "testtoken":
        return User(id=1)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
