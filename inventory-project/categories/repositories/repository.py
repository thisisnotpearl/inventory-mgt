from bson import ObjectId

from categories.models.models import Category

class CategoryRepository:

    @staticmethod
    def create(data):
        category = Category(**data)
        category.save()
        return category
    
    @staticmethod
    def delete(category_id):
        category = Category.objects(id = category_id).first()
        if category:
            category.delete()
        return category
    
    @staticmethod
    def get_all():
        return Category.objects()
    
    @staticmethod
    def get_by_id(category_id):
        return Category.objects(id=category_id).first()
    
    @staticmethod
    def update(data, category_id):
        category = Category.objects(id = category_id).first()
        for attr,value in data.items():
            fields = ["title", "description"]
            if attr in fields:
                setattr(category, attr, value)
        category.save()
        return category
    
    @staticmethod
    def get_by_title(title):
        #  to find a case insensitive match
        title = Category.objects(title__iexact = title ).first()
        return title    
