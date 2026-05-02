from bson import ObjectId

from products.models.models import Product
from datetime import datetime
import pytz

class ProductRepository:
# using static methods to avoid the need for instantiating the repository class, as it doesn't maintain any state and is just a collection of related functions for data access. This way, we can directly call these methods without creating an instance of ProductRepository.
    @staticmethod
    def create(data):
        product = Product(**data)
        product.save()
        return product

    @staticmethod
    def get_all():
        return Product.objects(is_deleted=False)

    @staticmethod
    def get_by_id(product_id):
        return Product.objects(id=product_id, is_deleted=False).first()

    @staticmethod
    def update(product_id, data):
        product = Product.objects(id=product_id, is_deleted=False).first()
        allowed_fields = ["name", "description", "category", "price", "quantity", "brand"]
        if product:
            for key, value in data.items():
                if key in allowed_fields:
                    setattr(product, key, value)
                product.save()
        return product

    @staticmethod
    def delete(product_id):
        product = Product.objects(id=product_id, is_deleted=False).first()
        if product:  
            product.is_deleted = True
            product.deleted_at = datetime.now(pytz.utc)
            product.save()
        return product
    
    @staticmethod
    def get_by_category(category_id):
        return Product.objects(category=ObjectId(category_id), is_deleted=False)

    # ── Embedding helpers ──────────────────────────────────────────────
    # These are used by the semantic search feature.  We keep them in the
    # repository so the service layer never touches MongoEngine directly.

    @staticmethod
    def get_products_with_embeddings():
        """Return non-deleted products that already have a computed embedding."""
        return Product.objects(is_deleted=False, embedding__ne=[])

    @staticmethod
    def update_embedding(product_id, embedding: list[float]):
        """Store a pre-computed embedding vector on a product document."""
        product = Product.objects(id=product_id).first()
        if product:
            product.embedding = embedding
            product.save()
        return product