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
    
    
    