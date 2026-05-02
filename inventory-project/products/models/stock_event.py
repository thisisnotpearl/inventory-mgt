from mongoengine import Document, StringField, IntField, FloatField, DateTimeField
from datetime import datetime, timezone

class StockEvent(Document):
    product_sku    = StringField(required=True)
    product_name   = StringField(required=True)
    event_type     = StringField(required=True)
    expected_date  = StringField(required=True)
    quantity_delta = IntField(required=True)
    unit_price     = FloatField(default=0.0)
    supplier       = StringField(default="")
    notes          = StringField(default="")
    status         = StringField(default="PENDING")
    created_at     = DateTimeField(default=lambda: datetime.now(timezone.utc))

    meta = {"collection": "stock_events"}
