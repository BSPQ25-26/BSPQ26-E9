from app.db.base import Base
from app.db.session import engine
from sqlalchemy import inspect, text
# import app.models.product  # Ensure model is imported so table is registered


def _ensure_column(table_name: str, column_name: str, ddl_by_dialect: dict[str, str]) -> None:
    with engine.begin() as conn:
        inspector = inspect(conn)
        existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
        if column_name in existing_columns:
            return
        ddl = ddl_by_dialect.get(engine.dialect.name)
        if ddl:
            conn.execute(text(ddl))

def init_db():
    Base.metadata.create_all(bind=engine)
    _ensure_column(
        table_name="inventory_products",
        column_name="transaction_product_id",
        ddl_by_dialect={
            "sqlite": "ALTER TABLE inventory_products ADD COLUMN transaction_product_id INTEGER",
            "postgresql": "ALTER TABLE inventory_products ADD COLUMN IF NOT EXISTS transaction_product_id INTEGER",
        },
    )
