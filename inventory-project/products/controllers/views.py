from urllib import request

from products.services.services import ProductService
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import csv

def parse_json(request):
    try:
        return json.loads(request.body)
    except:
        return None
    
def serialize_product(product):
    product_dict = product.to_mongo().to_dict()
    product_dict['_id'] = str(product_dict['_id'])  # Convert ObjectId to string because MongoDB uses ObjectId for _id field, which is not JSON serializable. Converting it to string allows us to include it in the JSON response.
    if product.category:
        product_dict['category'] = {
            "id": str(product.category.id),
            "title": product.category.title
        }
    return product_dict

# GET all / POST create
@csrf_exempt
def products(request):
    if request.method == "GET":
        category_id = request.GET.get("category")
        if category_id:
            try:
                products = ProductService.get_products_by_category(category_id)
            except ValueError as e:
                return JsonResponse({"error": str(e)}, status=404)
        else:
            products = ProductService.get_all_products()
        data = [serialize_product(p) for p in products]
        return JsonResponse(data, safe=False)
    # safe=False allows us to return a list of dictionaries as JSON response without needing to wrap it in another dictionary. By default, JsonResponse expects a dictionary, so if we want to return a list directly, we need to set safe=False.

    if request.method == "POST":
        body = parse_json(request)

        if not body:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        
        try:
            product = ProductService.create_product(body)
            return JsonResponse(serialize_product(product), status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
        
    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def product_detail(request, product_id):
        try:
            product = ProductService.get_product(product_id)
        except ValueError:
            return JsonResponse({"error": "Product not found"}, status=404)

        if request.method == "GET":
            return JsonResponse(serialize_product(product))

        elif request.method in ["PUT", "PATCH"]:
            body = parse_json(request)
            if not body:
                return JsonResponse({"error": "Invalid JSON"}, status=400)
        
            try:
                updated = ProductService.update_product(product_id, body)
                return JsonResponse(serialize_product(updated), safe=False)
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=400)

        elif request.method == "DELETE":
            try:
                ProductService.get_product(product_id)
            except ValueError:
                return JsonResponse({"error": "Product not found"}, status=404)
            
            ProductService.delete_product(product_id)
            return JsonResponse({"message": "Deleted successfully"})

        return JsonResponse({"error": "Method not allowed"}, status=405)

# ----------
# BULK UPLOAD
# ----------
@csrf_exempt
def bulk_upload(request):
        if request.method != "POST":
            return JsonResponse({"error": "Method not allowed"}, status=405)
        
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({"error": "No file uploaded"}, status=400)
        
        print(request.FILES)
        print("FILES:", request.FILES)
        print("METHOD:", request.method)
        # reads gives raw bytes, then decode into string, splitlines
        decoded_file = file.read().decode('utf-8').splitlines()

        # converts into dictionary format, keys = row headers, values - row values
        reader = csv.DictReader(decoded_file)

        success = []
        errors = []

        for idx, row in enumerate(reader, start=1):
            try:
                data = {
                    "name": row.get("name"),
                    "description": row.get("description", ""),
                    "category": row.get("category"),
                    "brand": row.get("brand"),
                    "quantity": int(row.get("quantity", 0)),
                    "price": float(row.get("price", 0)),
                }

                product = ProductService.create_product(data)
                success.append(str(product.id))

            except Exception as e:
                errors.append({
                    "row": idx,
                    "error": str(e)
                })

        return JsonResponse({
            "message": "Bulk upload completed",
            "success_count": len(success),
            "error_count": len(errors),
            "errors": errors
        })