from products.repositories.repository import ProductRepository

class ProductService:

    @staticmethod
    def create_product(data):
        # Basic validation and data.get() is used to avoid KeyError if the key is missing in the input data
        try:
            quantity = int(data.get("quantity", 0))
            price = float(data.get("price", 0))
        except (TypeError, ValueError):
            raise ValueError("Invalid quantity or price format")
        
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")

        if price <= 0:
            raise ValueError("Price must be greater than zero")

        return ProductRepository.create(data)

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
        return ProductRepository.update(product_id, data)

    @staticmethod
    def delete_product(product_id):
        return ProductRepository.delete(product_id)
    