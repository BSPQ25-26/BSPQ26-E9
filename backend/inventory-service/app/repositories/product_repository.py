from sqlalchemy.orm import Session
from app.models.product import Product
from app.schemas.product import ProductCreate

class ProductRepository:
    @staticmethod
    def create_product(db: Session, product_in: ProductCreate, seller_id: int) -> Product:
        product = Product(
            title=product_in.title,
            description=product_in.description,
            category=product_in.category,
            price=product_in.price,
            condition=product_in.condition,
            seller_id=seller_id
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product
