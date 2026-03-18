from sqlalchemy.orm import Session
from app.models.product import Product
from app.schemas.product import ProductCreate

class ProductRepository:
    @staticmethod
    def create_product(db: Session, product_in: ProductCreate, seller_id: str) -> Product:
        # Accept both 'name' and 'title', and require category/condition
        title = product_in.title or product_in.name
        if not title or not isinstance(title, str) or not title.strip():
            raise ValueError('title (or name) is required and must be a non-empty string')
        category = product_in.category or "general"
        condition = product_in.condition or "new"
        product = Product(
            title=title,
            description=product_in.description,
            category=category,
            price=product_in.price,
            condition=condition,
            seller_id=seller_id
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def update_product(db: Session, product: Product, updates: dict) -> Product:
        allowed_fields = {"title", "name", "description", "category", "price", "condition"}
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
