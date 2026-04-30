from sqlalchemy.orm import Session
from app.models.product import Product
from app.schemas.product import ProductCreate

class ProductRepository:
    @staticmethod
    def create_product(db: Session, product_in: ProductCreate, seller_id: str) -> Product:
        product = Product(
            title=product_in.title,
            description=product_in.description,
            category=product_in.category,
            price=product_in.price,
            condition=product_in.condition,
            seller_id=seller_id,
            images=product_in.model_dump().get("images", []),
            transaction_product_id=None,
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def update_product(db: Session, product: Product, updates: dict) -> Product:
        allowed_fields = {"title", "name", "description", "category", "price", "condition", "transaction_product_id"}
        for key, value in updates.items():
            if key == "name":
                setattr(product, "title", value)
            elif key in allowed_fields:
                setattr(product, key, value)
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def delete_product(db: Session, product: Product):
        db.delete(product)
        db.commit()
