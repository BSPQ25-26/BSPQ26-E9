from app.db.base import Base
from app.db.session import engine
import app.models.product  # Ensure model is imported so table is registered

def init_db():
    Base.metadata.create_all(bind=engine)
