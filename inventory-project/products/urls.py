from django.urls import path
from products.controllers import views

urlpatterns = [
    path("", views.products),   # GET /api/v1/products/ 
                                # POST /api/v1/products/
                                                                

    path("bulk/", views.bulk_upload),  # POST /api/v1/products/bulk/
    
    path("generate/", views.generate_products),
    path("generate-events/", views.generate_stock_events),
    path("stock-events/", views.list_stock_events),

    # ── Semantic Search (Week 7) ─────────────────────────────────────
    # These MUST come before the <str:product_id> catch-all route below,
    # otherwise Django would try to treat "semantic-search" as a product ID.
    path("compute-embeddings/", views.compute_embeddings),   # POST — pre-compute vectors
    path("semantic-search/", views.semantic_search),          # GET  — search by meaning
    path("evaluate-search/", views.evaluate_search),          # GET  — run quality metrics

    # ── RAG Chatbot (Week 8) ─────────────────────────────────────────
    path("rag/ingest/", views.ingest_rag_docs),               # POST — chunk and embed files
    path("rag/ask/", views.ask_expert),                       # POST — ask the chatbot
    path("rag/evaluate/", views.evaluate_rag),                # GET  — run eval suites

    # ── AI Agent (Week 9/10) ─────────────────────────────────────────
    path("agent/quote/", views.ask_agent),                    # POST — ask the sales agent

    path("<str:product_id>/", views.product_detail),    # GET /api/v1/products/<id>/
                                                        # PUT /api/v1/products/<id>/
                                                        # PATCH /api/v1/products/<id>/
                                                        # DELETE /api/v1/products/<id>/
    path("<str:product_id>/similar/", views.similar_products),  # GET — find similar products
]