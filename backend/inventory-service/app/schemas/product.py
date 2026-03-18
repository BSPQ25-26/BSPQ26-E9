from pydantic import BaseModel, Field, validator
from typing import Optional
from enum import Enum
from datetime import datetime

class ProductState(str, Enum):
    AVAILABLE = "Available"
    RESERVED = "Reserved"
    SOLD = "Sold"


class ProductBase(BaseModel):

    title: str = Field(None, min_length=1)
    name: str = Field(None, min_length=1)
    description: str = Field(..., min_length=1)
    category: str = Field(None, min_length=1)
    price: float = Field(..., gt=0)
    condition: str = Field(None, min_length=1)
    stock: int = Field(None, ge=0)

    @validator('title', pre=True, always=True)
    def set_title(cls, v, values):
        if v is not None:
            return v
        name = values.get('name')
        if name is not None:
            return name
        return ""

    @validator('category', pre=True, always=True)
    def set_category(cls, v, values):
        if v is not None:
            return v
        return ""

    @validator('condition', pre=True, always=True)
    def set_condition(cls, v, values):
        if v is not None:
            return v
        return ""

    class Config:
        extra = "allow"

class ProductCreate(ProductBase):
    pass

class ProductOut(ProductBase):
    id: int
    state: ProductState
    seller_id: str
    created_at: datetime

    class Config:
        orm_mode = True
