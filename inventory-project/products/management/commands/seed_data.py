from products.models.models import Product
from categories.models.models import Category
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed the database with initial product and category data"

    def handle(self, *args, **kwargs):

        #  1. Clean up 
        Product.objects.all().delete()
        Category.objects.all().delete()
        # empty products first because it has Foreign Key reference to categories. 
        # removing categories first would cause integrity errors

        # 2. Create categories first 
        category_data = [
            {"title": "Electronics",  "description": "Electronic devices and accessories"},
            {"title": "Kitchen",      "description": "Kitchen tools and cookware"},
            {"title": "Stationery",   "description": "Office and writing supplies"},
            {"title": "Sports",       "description": "Sports and fitness equipment"},
            {"title": "Food",         "description": "Food and grocery items"},
        ]

        # Build a lookup dict: "Electronics" -> <Category object>
        categories = {}
        for data in category_data:
            cat = Category(**data).save()
            categories[data["title"]] = cat

        self.stdout.write(f"  Created {len(categories)} categories")

        # 3. Seed products using category objects
        sample_products = [
            # Electronics
            {
                "name": "Sony WH-1000XM5 Headphones",
                "description": "Industry-leading noise cancelling wireless headphones",
                "category": categories["Electronics"],   # ← object, not string
                "brand": "Sony",
                "price": 24999.00,
                "quantity": 18,
            },
            {
                "name": "Logitech MX Master 3S Mouse",
                "description": "Advanced wireless mouse for professionals",
                "category": categories["Electronics"],
                "brand": "Logitech",
                "price": 8999.00,
                "quantity": 3,
            },
            {
                "name": "Anker 65W GaN Charger",
                "description": "Compact 3-port fast charger with foldable plug",
                "category": categories["Electronics"],
                "brand": "Anker",
                "price": 2499.00,
                "quantity": 42,
            },
            # Kitchen
            {
                "name": "Victorinox Chef Knife 8 inch",
                "description": "Professional chef's knife with ergonomic handle",
                "category": categories["Kitchen"],
                "brand": "Victorinox",
                "price": 3799.00,
                "quantity": 15,
            },
            {
                "name": "Prestige Stainless Steel Pressure Cooker 5L",
                "description": "5 litre inner lid pressure cooker",
                "category": categories["Kitchen"],
                "brand": "Prestige",
                "price": 1899.00,
                "quantity": 0,
            },
            {
                "name": "Borosil Glass Water Bottle 1L",
                "description": "Leak-proof borosilicate glass bottle",
                "category": categories["Kitchen"],
                "brand": "Borosil",
                "price": 599.00,
                "quantity": 60,
            },
            # Stationery
            {
                "name": "Pilot G2 Gel Pen Pack of 12",
                "description": "Smooth writing retractable gel pens, black",
                "category": categories["Stationery"],
                "brand": "Pilot",
                "price": 649.00,
                "quantity": 120,
            },
            {
                "name": "Moleskine Classic Notebook A5",
                "description": "Hard cover ruled notebook, 240 pages",
                "category": categories["Stationery"],
                "brand": "Moleskine",
                "price": 1299.00,
                "quantity": 34,
            },
            {
                "name": "Staedtler Mars Plastic Eraser Pack of 5",
                "description": "Premium vinyl erasers for clean corrections",
                "category": categories["Stationery"],
                "brand": "Staedtler",
                "price": 199.00,
                "quantity": 200,
            },
            # Sports
            {
                "name": "Cosco Championship Badminton Racket",
                "description": "Aluminium shaft racket for intermediate players",
                "category": categories["Sports"],
                "brand": "Cosco",
                "price": 849.00,
                "quantity": 25,
            },
            {
                "name": "Boldfit Resistance Bands Set of 5",
                "description": "Latex resistance bands for home workouts",
                "category": categories["Sports"],
                "brand": "Boldfit",
                "price": 499.00,
                "quantity": 2,
            },
            {
                "name": "Nivia Football Size 5",
                "description": "PU leather match quality football",
                "category": categories["Sports"],
                "brand": "Nivia",
                "price": 1199.00,
                "quantity": 40,
            },
            # Food
            {
                "name": "Tata Salt Lite Low Sodium 1kg",
                "description": "Low sodium iodised salt for health-conscious users",
                "category": categories["Food"],
                "brand": "Tata",
                "price": 89.00,
                "quantity": 500,
            },
            {
                "name": "Bagrry's Rolled Oats 1kg",
                "description": "100% whole grain rolled oats, no added sugar",
                "category": categories["Food"],
                "brand": "Bagrry's",
                "price": 299.00,
                "quantity": 88,
            },
            {
                "name": "Epigamia Greek Yogurt Strawberry 90g",
                "description": "High protein greek yogurt, no artificial sweeteners",
                "category": categories["Food"],
                "brand": "Epigamia",
                "price": 55.00,
                "quantity": 0,
            },
        ]

        for data in sample_products:
            Product(**data).save()

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(sample_products)} products across {len(categories)} categories successfully"
        ))