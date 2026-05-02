from langchain_core.tools import tool
import json

@tool
def get_product_info(product_name_or_id: str) -> str:
    """
    Search for a product in the database by its name, description, or ID.
    Returns the product's SKU, exact name, and base price. 
    Use this tool FIRST when a user asks for a quote for an item.
    """
    from products.services.embedding_service import EmbeddingService
    
    try:
        # We use semantic search so it finds "Lego" even if they ask for "building blocks"
        results = EmbeddingService.semantic_search(product_name_or_id, top_k=1, threshold=0.10)
        if not results:
            return json.dumps({"error": f"No product found matching '{product_name_or_id}'"})
            
        product = results[0]
        return json.dumps({
            "id": product["id"],
            "sku": product["sku"],
            "name": product["name"],
            "price": product["price"]
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def check_inventory(product_id: str) -> str:
    """
    Check the live inventory stock level for a specific product ID.
    Always call this before calculating a quote to ensure we have enough stock.
    """
    from products.models.models import Product
    
    try:
        # Verify it's a valid ID before querying
        if len(product_id) != 24: # MongoDB ObjectIds are 24 chars
            # Fallback in case the LLM passes a SKU instead of the ID
            product = Product.objects(sku=product_id, is_deleted=False).first()
        else:
            product = Product.objects(id=product_id, is_deleted=False).first()
            
        if not product:
            return json.dumps({"error": "Product not found."})
            
        return json.dumps({
            "id": str(product.id),
            "name": product.name,
            "quantity_in_stock": product.quantity
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def calculate_quote(product_id: str, quantity: int, requested_discount_pct: float = 0.0) -> str:
    """
    Calculates the total quote for a given quantity of a product, applying standard discounts
    and any requested manual discounts.
    """
    from products.models.models import Product
    
    try:
        # 1. Fetch Product
        if len(product_id) != 24:
            product = Product.objects(sku=product_id, is_deleted=False).first()
        else:
            product = Product.objects(id=product_id, is_deleted=False).first()
            
        if not product:
            return json.dumps({"error": "Product not found."})
            
        # 2. Check Stock
        if quantity > product.quantity:
            return json.dumps({"error": f"Insufficient stock. We only have {product.quantity} units available."})
            
        # 3. Apply Hard-coded Business Rules
        auto_discount = 0.0
        if quantity >= 50:
            auto_discount = 10.0  # 10% off for bulk
            
        # 4. POLICY ENFORCEMENT (Success Boundaries)
        # If the LLM tries to grant a massive discount, the Python code forcefully blocks it.
        total_requested_discount = auto_discount + requested_discount_pct
        if total_requested_discount > 20.0:
            return json.dumps({
                "error": "POLICY_VIOLATION",
                "message": f"Requested total discount ({total_requested_discount}%) exceeds the absolute maximum allowed policy limit of 20%. The quote has been rejected. Apologize to the user and offer a maximum of 20% discount."
            })
            
        # 5. Math
        base_total = product.price * quantity
        discount_amount = base_total * (total_requested_discount / 100)
        final_total = base_total - discount_amount
        
        return json.dumps({
            "product": product.name,
            "quantity": quantity,
            "base_price_per_unit": product.price,
            "base_total": base_total,
            "discount_applied_pct": total_requested_discount,
            "discount_amount": discount_amount,
            "final_total": final_total,
            "status": "APPROVED"
        })
        
    except Exception as e:
        return json.dumps({"error": str(e)})
