# categories / controllers / views.py 
import json
from categories.services.services import CategoryService
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from products.models.models import Product

# Convert ObjectId to string because MongoDB uses ObjectId for _id field, which is not JSON serializable. Converting it to string allows us to include it in the JSON response.
def serialize_category(category):
    category_dict = category.to_mongo().to_dict()
    category_dict['_id'] = str(category_dict['_id'])  # Convert ObjectId to string
    return category_dict

@csrf_exempt
def category_detail(request):
    if request.method == "POST":
        body = json.loads(request.body)
        category = CategoryService.create_category(body)
        return JsonResponse(serialize_category(category), safe=False)
    # safe=False allows us to return a list of dictionaries as JSON response

    if request.method=="GET":
        categories = CategoryService.get_all()
        data = [serialize_category(c) for c in categories]
        return JsonResponse(data, safe=False)

@csrf_exempt
def category_detail(request, category_id):
    if request.method == "GET":
        category = CategoryService.get_by_id(category_id)
        if not category:
            return JsonResponse({"error": "Category not found"}, status=404)
        return JsonResponse(serialize_category(category), safe=False)
    
    if request.method == "PATCH":
        try:
            body = json.loads(request.body)
            category = CategoryService.update_category(category_id, body)
            return JsonResponse(serialize_category(category))
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)
