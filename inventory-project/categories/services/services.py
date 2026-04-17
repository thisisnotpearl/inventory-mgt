from categories.repositories.repository import CategoryRepository

class CategoryService:
    @staticmethod
    def create_category(data):
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        existing = CategoryRepository.get_by_title(title)
        if existing:
            raise ValueError(f"Category {title} already exists!") 
        return CategoryRepository.create({
            "title": title,
            "description" : description
            })
    
    @staticmethod
    def get_all():
        return CategoryRepository.get_all()
    
    @staticmethod
    def get_by_id(category_id):
        existing = CategoryRepository.get_by_id(category_id)
        if not existing:
            raise ValueError("Category not found!")
        return existing
    
    @staticmethod
    def update(data, category_id):
        category = CategoryRepository.get_by_id(category_id)
        if not category:
            raise ValueError("Category does not exist")
        title = data.get("title","").strip()
        if not title:
            raise ValueError("Title not found!")
        existing = CategoryRepository.get_by_title(title)
         # existing is ok if it's the same category being updated
        if existing and str(existing.id) != str(category_id):
            raise ValueError(f"Cateogory {title} already exists!")
        return CategoryRepository.update(data,category_id)
