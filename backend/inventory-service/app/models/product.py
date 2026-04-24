from sqlalchemy import Column, Integer, String, Float, Enum, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.base import Base

class ProductState(str, enum.Enum):
    AVAILABLE = "Available"
    RESERVED = "Reserved"
    SOLD = "Sold"

class ProductCondition(str, enum.Enum):
    NEW = "New"
    LIKE_NEW = "Like New"
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"

class Product(Base):
    __tablename__ = "inventory_products"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    condition = Column(
        Enum(
            ProductCondition,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
            name="productcondition",
            native_enum=True,
        ),
        nullable=False,
    )
    state = Column(
        Enum(
            ProductState,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
            native_enum=False,
        ),
        default=ProductState.AVAILABLE,
        nullable=False,
    )
    seller_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    images = Column(JSON(String), nullable=False, default=list)

    # seller = relationship("User", back_populates="products")
