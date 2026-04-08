from mongoengine import Document, FloatField, StringField, IntField, DateTimeField, BooleanField
from datetime import datetime
import pytz

def generate_sku(category, brand):
    cat = category[:4].upper()
    br = (brand[:4] if brand else "GEN").upper()

    last_product = Product.objects.order_by('-id').first()
    
    if last_product and last_product.sku:
        last_number = int(last_product.sku.split('-')[-1])
        new_number = str(last_number + 1).zfill(4)
    else:
        new_number = "0001"

    return f"{cat}-{br}-{new_number}"

class Product(Document):
    CATEGORY_CHOICES = (
    ("Electronics",     "Electronics"),
    ("Kitchen",         "Kitchen"),
    ("Stationery",      "Stationery"),
    ("Sports",          "Sports"),
    ("Food",            "Food"),
)
    sku = StringField(required=True, unique=True)
    name = StringField(max_length=100, required=True)
    description = StringField(max_length=500)
    category = StringField(max_length=100, required=True, choices = CATEGORY_CHOICES)
    quantity = IntField(required=True)
    price = FloatField(required = True)    
    brand = StringField(max_length=100)
    # the databases store UTC timezone, and while displaying, we can convert it to the user's local timezone if needed
    created_at = DateTimeField(default=lambda: datetime.now(pytz.utc)) 
    updated_at = DateTimeField(default=lambda: datetime.now(pytz.utc))
    is_deleted = BooleanField(default=False)
    deleted_at = DateTimeField(null=True)


    meta = {"collection":"products"}

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = generate_sku(self.category, self.brand)

        self.updated_at = datetime.now(pytz.utc)
        return super().save(*args, **kwargs)
    

