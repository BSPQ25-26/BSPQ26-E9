from pydantic import BaseModel, Field, validator
from typing import Optional
from enum import Enum
from datetime import datetime

class ProductState(str, Enum):
    AVAILABLE = "Available"
    RESERVED = "Reserved"
    SOLD = "Sold"

class ProductBase(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)
    condition: str = Field(..., min_length=1)

class ProductCreate(ProductBase):
    pass

class ProductOut(ProductBase):
    id: int
    state: ProductState
    seller_id: int
    created_at: datetime

    class Config:
        orm_mode = True
