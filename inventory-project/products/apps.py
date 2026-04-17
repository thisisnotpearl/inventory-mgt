from django.apps import AppConfig


class ProductsConfig(AppConfig):
    name = 'products'
    def ready(self):
        from config.db import init_db
        init_db()
        print("MongoDB connection initialized successfully!")
