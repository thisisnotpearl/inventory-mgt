from mongoengine import Document, StringField, ReferenceField, FloatField, IntField, DateTimeField
from datetime import datetime

class Category(Document):
    title = StringField(max_length = 100, required=True, unique = True)
    description = StringField(max_length = 500)
    created_at = DateTimeField(default=datetime.utcnow)
    
    # categories / models / models.py
    meta = {"meta":"categories"}

    



