from products.models.models import Product
from django.core.management.base import BaseCommand

# Django automatically finds any file inside management/commands/ and makes it available as a manage.py command — no registration needed anywhere.

class Command(BaseCommand):
    help = "Seed the database with initial product data"

    Product.objects.all().delete() # Delete existing data

    def handle(self, *args, **kwargs):
        
        sample_products = [
            # Electronics
            {
                "name": "Sony WH-1000XM5 Headphones",
                "description": "Industry-leading noise cancelling wireless headphones",
                "category": "Electronics",
                "brand": "Sony",
                "price": 24999.00,
                "quantity": 18,
            },
            {
                "name": "Logitech MX Master 3S Mouse",
                "description": "Advanced wireless mouse for professionals",
                "category": "Electronics",
                "brand": "Logitech",
                "price": 8999.00,
                "quantity": 3,   # intentionally low stock
            },
            {
                "name": "Anker 65W GaN Charger",
                "description": "Compact 3-port fast charger with foldable plug",
                "category": "Electronics",
                "brand": "Anker",
                "price": 2499.00,
                "quantity": 42,
            },
            # Kitchen
            {
                "name": "Victorinox Chef Knife 8 inch",
                "description": "Professional chef's knife with ergonomic handle",
                "category": "Kitchen",
                "brand": "Victorinox",
                "price": 3799.00,
                "quantity": 15,
            },
            {
                "name": "Prestige Stainless Steel Pressure Cooker 5L",
                "description": "5 litre inner lid pressure cooker",
                "category": "Kitchen",
                "brand": "Prestige",
                "price": 1899.00,
                "quantity": 0,   # intentionally out of stock
            },
            {
                "name": "Borosil Glass Water Bottle 1L",
                "description": "Leak-proof borosilicate glass bottle",
                "category": "Kitchen",
                "brand": "Borosil",
                "price": 599.00,
                "quantity": 60,
            },
            # Stationery
            {
                "name": "Pilot G2 Gel Pen Pack of 12",
                "description": "Smooth writing retractable gel pens, black",
                "category": "Stationery",
                "brand": "Pilot",
                "price": 649.00,
                "quantity": 120,
            },
            {
                "name": "Moleskine Classic Notebook A5",
                "description": "Hard cover ruled notebook, 240 pages",
                "category": "Stationery",
                "brand": "Moleskine",
                "price": 1299.00,
                "quantity": 34,
            },
            {
                "name": "Staedtler Mars Plastic Eraser Pack of 5",
                "description": "Premium vinyl erasers for clean corrections",
                "category": "Stationery",
                "brand": "Staedtler",
                "price": 199.00,
                "quantity": 200,
            },
            # Sports
            {
                "name": "Cosco Championship Badminton Racket",
                "description": "Aluminium shaft racket for intermediate players",
                "category": "Sports",
                "brand": "Cosco",
                "price": 849.00,
                "quantity": 25,
            },
            {
                "name": "Boldfit Resistance Bands Set of 5",
                "description": "Latex resistance bands for home workouts",
                "category": "Sports",
                "brand": "Boldfit",
                "price": 499.00,
                "quantity": 2,   # intentionally low stock
            },
            {
                "name": "Nivia Football Size 5",
                "description": "PU leather match quality football",
                "category": "Sports",
                "brand": "Nivia",
                "price": 1199.00,
                "quantity": 40,
            },
            # Food
            {
                "name": "Tata Salt Lite Low Sodium 1kg",
                "description": "Low sodium iodised salt for health-conscious users",
                "category": "Food",
                "brand": "Tata",
                "price": 89.00,
                "quantity": 500,
            },
            {
                "name": "Bagrry's Rolled Oats 1kg",
                "description": "100% whole grain rolled oats, no added sugar",
                "category": "Food",
                "brand": "Bagrry's",
                "price": 299.00,
                "quantity": 88,
            },
            {
                "name": "Epigamia Greek Yogurt Strawberry 90g",
                "description": "High protein greek yogurt, no artificial sweeteners",
                "category": "Food",
                "brand": "Epigamia",
                "price": 55.00,
                "quantity": 0,   # intentionally out of stock
            },
        ]

        # upserting the data - if a product with the same name and brand already exists, it will be updated with the new data; otherwise, a new product will be created
        # for data in sample_products:
        #     Product.objects(
        #         name=data["name"],
        #         brand=data["brand"]
        #     ).update_one(
        #         set__name=data["name"],
        #         set__description=data["description"],
        #         set__category=data["category"],
        #         set__quantity=data["quantity"],
        #         set__price=data["price"],
        #         set__brand=data["brand"],
        #         upsert=True
        #     )

        for data in sample_products:
            Product(**data).save()      # calls your save() method, which generates the SKU

        self.stdout.write(self.style.SUCCESS("Seed data inserted/updated successfully"))