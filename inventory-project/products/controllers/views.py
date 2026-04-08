from django.shortcuts import render
from products.services.services import ProductService
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import csv

# GET all / POST create
@csrf_exempt
def products(request):
    if request.method == "GET":
        products = ProductService.get_all_products()
        data = []
        for p in products:
            product_dict = p.to_mongo().to_dict()
            product_dict['_id'] = str(product_dict['_id'])  # Convert ObjectId to string
            data.append(product_dict)
        return JsonResponse(data, safe=False)
    # safe=False allows us to return a list of dictionaries as JSON response without needing to wrap it in another dictionary. By default, JsonResponse expects a dictionary, so if we want to return a list directly, we need to set safe=False.

    if request.method == "POST":
        body = json.loads(request.body)
        product = ProductService.create_product(body)
        product_dict = product.to_mongo().to_dict()
        product_dict['_id'] = str(product_dict['_id'])  # Convert ObjectId to string
        return JsonResponse(product_dict, safe=False)

@csrf_exempt
def product_detail(request, product_id):
    if request.method == "GET":
        try:
            product = ProductService.get_product(product_id)
            product_dict = product.to_mongo().to_dict()
            product_dict['_id'] = str(product_dict['_id'])  # Convert ObjectId to string
            return JsonResponse(product_dict, safe=False)
        except ValueError:
            return JsonResponse({"error": "Product not found"}, status=404)
        

    if request.method == "PUT":
        body = json.loads(request.body)
        product = ProductService.update_product(product_id, body)
        if not product:
            return JsonResponse({"error": "Product not found"}, status=404)
        product_dict = product.to_mongo().to_dict()
        product_dict['_id'] = str(product_dict['_id'])  # Convert ObjectId to string
        return JsonResponse(product_dict, safe=False)

    if request.method == "PATCH":
        body = json.loads(request.body)
        product = ProductService.update_product(product_id, body)
        if not product:
            return JsonResponse({"error": "Product not found"}, status=404)
        product_dict = product.to_mongo().to_dict()
        product_dict['_id'] = str(product_dict['_id'])  # Convert ObjectId to string
        return JsonResponse(product_dict, safe=False)

    if request.method == "DELETE":
        try:
            ProductService.get_product(product_id)
        except ValueError:
            return JsonResponse({"error": "Product not found"}, status=404)
        ProductService.delete_product(product_id)
        return JsonResponse({"message": "Deleted successfully"})

    

@csrf_exempt
def bulk_upload(request):
        if request.method != "POST":
            return JsonResponse({"error": "Invalid request method"}, status=405)
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({"error": "No file uploaded"}, status=400)

        decoded_file = file.read().decode('utf-8').splitlines()
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