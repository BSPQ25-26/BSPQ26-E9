"""
Definition of database table with SQLAlchemy 

Two  Tables needed 
products: (ID, title, description, category, price, state, owner_id, created_at, updated_at)
product_state_history:
"""

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Integer
from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase, relationship

from app.services.state_machine import ProductState


class Base(DeclarativeBase):
    pass

#Product table definition
class Product(Base):
    __tablename__ = "products"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    category    = Column(String(100), nullable=True)
    price       = Column(Float, nullable=False)
    state       = Column(String(20), nullable=False, default=ProductState.AVAILABLE)
    owner_id    = Column(String(255), nullable=False)
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))
    
    #Relationship with state history
    state_history = relationship("ProductStateHistory", back_populates="product")

#Product state history table definition
class ProductStateHistory(Base):
    __tablename__ = "product_state_history"

    id         = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    from_state = Column(String(20), nullable=True)
    to_state   = Column(String(20), nullable=False)
    changed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    changed_by = Column(String(255), nullable=True)

    #Relationship with product
    product = relationship("Product", back_populates="state_history")