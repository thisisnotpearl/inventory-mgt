from bson import ObjectId
from categories.models.models import Category
from products.repositories.repository import ProductRepository

class ProductService:

    @staticmethod
    def create_product(data):
        brand = data.get("brand", "").strip()
        if not brand:
            raise ValueError("Brand is required")

        name = data.get("name", "").strip()
        if not name:
            raise ValueError("Product name is required")

        try:
            quantity = int(data.get("quantity", 0))
            price = float(data.get("price", 0))
        except (TypeError, ValueError):
            raise ValueError("Invalid quantity or price format")
        
        try:
            quantity = int(data.get("quantity", 0))
            price = float(data.get("price", 0))
        except (TypeError, ValueError):
            raise ValueError("Invalid quantity or price format")
        
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")

        if price <= 0:
            raise ValueError("Price must be greater than zero")
        
        if "category" in data:
            category = Category.objects.get(id=ObjectId(data["category"]))
            data["category"] = category
        
        return ProductRepository.create({
            "name": name,
            "description": data.get("description", "").strip(),
            "category": data.get("category"),
            "brand": brand,
            "quantity": quantity,
            "price": price
        })
        
        
    @staticmethod
    def get_all_products():
        return ProductRepository.get_all()

    @staticmethod
    def get_product(product_id):
        product = ProductRepository.get_by_id(product_id)
        if not product:
            raise ValueError("Product not found")
        return product

    @staticmethod
    def update_product(product_id, data):
        if "category" in data:
            category_id = data["category"]

            try:
                category = Category.objects.get(id=ObjectId(category_id))
                data["category"] = category 
            except:
                raise ValueError("Invalid category ID")
            
        return ProductRepository.update(product_id, data)

    @staticmethod
    def delete_product(product_id):
        return ProductRepository.delete(product_id)
    
    @staticmethod
    def get_products_by_category(category_id):
        from categories.repositories.repository import CategoryRepository
        if not CategoryRepository.get_by_id(category_id):
            raise ValueError("Category not found")
        return ProductRepository.get_by_category(category_id)