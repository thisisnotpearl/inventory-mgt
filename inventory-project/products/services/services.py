from bson import ObjectId
from categories.models.models import Category
from products.repositories.repository import ProductRepository
from products.services.ai_service import AIService
from products.services.embedding_service import EmbeddingService
from products.repositories.stock_event_repo import StockEventRepository

class ProductService:

    @staticmethod
    def create_product(data):
        brand = data.get("brand", "").strip()
        if not brand:
            raise ValueError("Brand is required")

        name = data.get("name", "").strip()
        if not name:
            raise ValueError("Product name is required")

        try:
            quantity = int(data.get("quantity", 0))
            price = float(data.get("price", 0))
        except (TypeError, ValueError):
            raise ValueError("Invalid quantity or price format")
        
        try:
            quantity = int(data.get("quantity", 0))
            price = float(data.get("price", 0))
        except (TypeError, ValueError):
            raise ValueError("Invalid quantity or price format")
        
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")

        if price <= 0:
            raise ValueError("Price must be greater than zero")
        
        if "category" in data:
            category = Category.objects.get(id=ObjectId(data["category"]))
            data["category"] = category
        
        return ProductRepository.create({
            "name": name,
            "description": data.get("description", "").strip(),
            "category": data.get("category"),
            "brand": brand,
            "quantity": quantity,
            "price": price
        })
        
        
    @staticmethod
    def get_all_products():
        return ProductRepository.get_all()

    @staticmethod
    def get_product(product_id):
        product = ProductRepository.get_by_id(product_id)
        if not product:
            raise ValueError("Product not found")
        return product

    @staticmethod
    def update_product(product_id, data):
        if "category" in data:
            category_id = data["category"]

            try:
                category = Category.objects.get(id=ObjectId(category_id))
                data["category"] = category 
            except:
                raise ValueError("Invalid category ID")
            
        return ProductRepository.update(product_id, data)

    @staticmethod
    def delete_product(product_id):
        return ProductRepository.delete(product_id)
    
    @staticmethod
    def get_products_by_category(category_id):
        from categories.repositories.repository import CategoryRepository
        if not CategoryRepository.get_by_id(category_id):
            raise ValueError("Category not found")
        return ProductRepository.get_by_category(category_id)

    @staticmethod
    def generate_and_save_products(count: int = 50, scenario: str = "standard"):
        result = AIService.generate_products(count, scenario)
        valid_items = result.get("valid", [])
        ai_errors = result.get("errors", [])
        usage = result.get("usage", {})
        
        saved = 0
        save_errors = []
        for item in valid_items:
            try:
                # Get or create category
                category_title = item.get("category")
                cat = Category.objects(title=category_title).first()
                if not cat:
                    cat = Category(title=category_title)
                    cat.save()
                
                ProductRepository.create({
                    "name": item.get("name"),
                    "description": item.get("description"),
                    "category": cat,
                    "brand": item.get("brand"),
                    "quantity": item.get("quantity"),
                    "price": item.get("price")
                })
                saved += 1
            except Exception as e:
                save_errors.append(str(e))
                
        return {
            "saved": saved,
            "ai_errors": ai_errors,
            "save_errors": save_errors,
            "usage": usage
        }

    @staticmethod
    def generate_and_save_stock_events():
        products = ProductRepository.get_all()
        sku_list = [{"sku": p.sku, "name": p.name} for p in products if p.sku][:15]
        
        if not sku_list:
            raise ValueError("No products found in the database. Generate products first.")
            
        result = AIService.generate_stock_events(sku_list)
        valid_events = result.get("valid", [])
        ai_errors = result.get("errors", [])
        usage = result.get("usage", {})
        
        saved_docs, save_errors = StockEventRepository.bulk_create(valid_events)
        
        return {
            "saved": len(saved_docs),
            "ai_errors": ai_errors,
            "save_errors": save_errors,
            "usage": usage
        }

    # ── Semantic Search (Week 7) ──────────────────────────────────────
    # These methods delegate to EmbeddingService for the actual vector math
    # but live here so controllers only ever call ProductService.

    @staticmethod
    def compute_embeddings():
        """Pre-compute embeddings for all products in the database."""
        return EmbeddingService.compute_all_embeddings()

    @staticmethod
    def semantic_search(query: str, top_k: int = 10):
        """Search products by meaning using vector similarity."""
        return EmbeddingService.semantic_search(query, top_k)

    @staticmethod
    def find_similar_products(product_id: str, top_k: int = 5):
        """Given one product, find the most similar ones."""
        return EmbeddingService.find_similar_products(product_id, top_k)

    @staticmethod
    def evaluate_search():
        """Run the evalset against semantic search and return quality metrics."""
        from products.services.search_eval import evaluate_search
        return evaluate_search(EmbeddingService.semantic_search)

    # ── RAG (Week 8) ──────────────────────────────────────────────────
    
    @staticmethod
    def ingest_rag_documents():
        """Load text files and store them in ChromaDB."""
        from products.services.rag_service import RAGService
        return RAGService.ingest_documents()

    @staticmethod
    def ask_expert(query: str, use_advanced: bool = False):
        """Ask the RAG chatbot a question."""
        from products.services.rag_service import RAGService
        if use_advanced:
            return RAGService.ask_expert_with_stock(query)
        return RAGService.ask_expert(query)

    @staticmethod
    def evaluate_rag():
        """Run the RAG retrieval and generation evaluation suites."""
        from products.services.rag_eval import RAGEvaluator
        retrieval = RAGEvaluator.run_retrieval_eval()
        generation = RAGEvaluator.run_generation_eval()
        return {
            "retrieval_eval": retrieval,
            "generation_eval": generation
        }

    # ── AI Agent (Week 9/10) ──────────────────────────────────────────
    
    @staticmethod
    def ask_sales_agent(user_input: str, chat_history: list = None):
        """Passes the user's message to the LangChain Agent for a quote."""
        from products.services.agent_service import AgentService
        return AgentService.run_agent(user_input, chat_history)