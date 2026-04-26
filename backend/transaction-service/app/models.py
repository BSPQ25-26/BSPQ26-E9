"""
Definition of database tables with SQLAlchemy 

Tables:
- transaction_products: Products for transactions
- product_state_history: State transitions history
- wallet_ledger: Wallet movements and balance history
- transactions: Purchase/sale transactions
"""

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Integer, Numeric, Index, TypeDecorator
from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase, relationship

from app.services.state_machine import ProductState


class Base(DeclarativeBase):
    pass


class ProductStateType(TypeDecorator):
    """Custom type for ProductState enum - converts string to enum on load."""
    impl = String(20)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, ProductState):
            return value.value
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return ProductState(value)

#Product table definition
class Product(Base):
    __tablename__ = "transaction_products"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    category    = Column(String(100), nullable=True)
    price       = Column(Float, nullable=False)
    state       = Column(ProductStateType, nullable=False, default=ProductState.AVAILABLE)
    owner_id    = Column(String(255), nullable=False)
    reserved_at = Column(DateTime, nullable=True)  # Sprint 2: Timestamp when product was reserved 
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))
    
    #Relationship with state history
    state_history = relationship("ProductStateHistory", back_populates="product")

#Product state history table definition
class ProductStateHistory(Base):
    __tablename__ = "product_state_history"

    id         = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("transaction_products.id"), nullable=False)
    from_state = Column(String(20), nullable=True)
    to_state   = Column(String(20), nullable=False)
    changed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    changed_by = Column(String(255), nullable=True)

    #Relationship with product
    product = relationship("Product", back_populates="state_history")


# Sprint 2: Wallet & Transaction Models 

# BALANCE INTEGRITY GUARANTEE:
#   - EVERY wallet mutation (top-up, purchase, refund) creates a NEW entry
#   - NEVER update balance_after directly (no UPDATE on this table)
#   - Current balance = balance_after from the LAST entry ordered by created_at
#   - This ensures a complete, immutable audit trail
class WalletLedger(Base):
    __tablename__ = "wallet_ledger"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(String(255), nullable=False, index=True)  
    amount          = Column("delta", Numeric(12, 2), nullable=False)  # positive=credit, negative=debit
    transaction_type = Column("type", String(20), nullable=False)  # TOP_UP, PURCHASE, SALE
    description     = Column(String(255), nullable=True)
    balance_after   = Column(Numeric(12, 2), nullable=False)  # Balance AFTER this movement (immutable)
    created_at      = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        Index('ix_wallet_ledger_user_id_created_at', 'user_id', 'created_at'),
    )


# Transaction: Purchase or sale between buyer and seller
class Transaction(Base):
    __tablename__ = "transactions"  

    id              = Column(Integer, primary_key=True, index=True)
    buyer_id        = Column(String(255), nullable=False)  #user_id of the buyer
    seller_id       = Column(String(255), nullable=False)  #user_id of the seller
    product_id      = Column(Integer, ForeignKey("transaction_products.id"), nullable=False)
    amount          = Column(Float, nullable=False)
    created_at      = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('ix_transactions_buyer_id', 'buyer_id'),
        Index('ix_transactions_seller_id', 'seller_id'),
        Index('ix_transactions_created_at', 'created_at'),
    )