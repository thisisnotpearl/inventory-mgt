from urllib import request

from products.services.services import ProductService
from products.repositories.stock_event_repo import StockEventRepository
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

def serialize_stock_event(event):
    return {
        "_id": str(event.id),
        "product_sku": event.product_sku,
        "product_name": event.product_name,
        "event_type": event.event_type,
        "expected_date": event.expected_date,
        "quantity_delta": event.quantity_delta,
        "unit_price": event.unit_price,
        "supplier": event.supplier,
        "notes": event.notes,
        "status": event.status,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }

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

@csrf_exempt
def generate_products(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    body = parse_json(request) or {}
    count = body.get("count", 50)
    scenario = body.get("scenario", "standard")
    
    try:
        result = ProductService.generate_and_save_products(count, scenario)
        return JsonResponse(result, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def generate_stock_events(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        result = ProductService.generate_and_save_stock_events()
        return JsonResponse(result, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def list_stock_events(request):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    status = request.GET.get("status")
    sku = request.GET.get("sku")
    
    try:
        if sku:
            events = StockEventRepository.get_by_product(sku)
        else:
            events = StockEventRepository.get_all(status)
        data = [serialize_stock_event(e) for e in events]
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ── Semantic Search (Week 7) ─────────────────────────────────────────
# These endpoints power the semantic search features in the dashboard.

@csrf_exempt
def compute_embeddings(request):
    """Pre-compute embedding vectors for all products in the database.
    
    This should be called once after adding/generating new products,
    so that semantic search has vectors to compare against.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        result = ProductService.compute_embeddings()
        return JsonResponse(result, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def semantic_search(request):
    """Search products by meaning instead of keywords.
    
    Usage: GET /api/v1/products/semantic-search/?q=construction+toys&top_k=10
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"error": "Query parameter 'q' is required"}, status=400)
    
    top_k = int(request.GET.get("top_k", 10))
    
    try:
        results = ProductService.semantic_search(query, top_k)
        return JsonResponse(results, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def similar_products(request, product_id):
    """Find products semantically similar to a given product.
    
    Usage: GET /api/v1/products/<id>/similar/?top_k=5
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    top_k = int(request.GET.get("top_k", 5))
    
    try:
        results = ProductService.find_similar_products(product_id, top_k)
        return JsonResponse(results, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def evaluate_search(request):
    """Run the search evaluation suite and return precision/recall metrics.
    
    Usage: GET /api/v1/products/evaluate-search/
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        results = ProductService.evaluate_search()
        return JsonResponse(results, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ── RAG Chatbot (Week 8) ─────────────────────────────────────────────

@csrf_exempt
def ingest_rag_docs(request):
    """Ingest text files into ChromaDB for RAG."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        result = ProductService.ingest_rag_documents()
        return JsonResponse(result, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def ask_expert(request):
    """Ask the RAG chatbot a question."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    body = parse_json(request) or {}
    query = body.get("q", "").strip()
    use_advanced = body.get("use_advanced", False)
    
    if not query:
        return JsonResponse({"error": "Query 'q' is required"}, status=400)
        
    try:
        result = ProductService.ask_expert(query, use_advanced=use_advanced)
        return JsonResponse(result, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def evaluate_rag(request):
    """Run the RAG evaluation suites."""
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        results = ProductService.evaluate_rag()
        return JsonResponse(results, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ── AI Agent (Week 9/10) ─────────────────────────────────────────────

@csrf_exempt
def ask_agent(request):
    """Ask the AI Sales Agent for a quote."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    body = parse_json(request) or {}
    query = body.get("q", "").strip()
    history = body.get("history", [])
    
    if not query:
        return JsonResponse({"error": "Query 'q' is required"}, status=400)
        
    try:
        # Convert steps to a serializable format
        result = ProductService.ask_sales_agent(query, history)
        
        # Action Tool and Tool inputs might be Pydantic objects or complex dicts
        # Let's clean them up for JSON serialization
        cleaned_steps = []
        for step in result.get("steps", []):
            cleaned_steps.append({
                "tool": step["tool"],
                "tool_input": step["tool_input"],
                "result": step["result"]
            })
            
        return JsonResponse({
            "answer": result["answer"],
            "steps": cleaned_steps
        }, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)