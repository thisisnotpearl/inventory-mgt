# Architecture

## Overview
A RESTful Inventory Management System built with Django REST Framework and MongoDB via MongoEngine. The system follows hexagonal (ports & adapters) architecture to keep business logic independent of HTTP and database concerns, perfectly facilitating complex integrations like our AI-driven scenario simulation.

## Layer structure

```text
HTTP Request
    ↓
controllers/        → receives HTTP, calls service, returns JSON
    ↓
services/           → all business logic, validation, and AI integrations live here
    ↓
repositories/       → all MongoDB reads and writes live here
    ↓
models/             → MongoEngine document schema definitions
    ↓
MongoDB
```

### controllers/
- Owns: parsing request, calling service, returning JsonResponse
- Must not: contain any business logic or query MongoDB directly
- Example: `views.py`

### services/
- Owns: validation rules (Pydantic), business decisions, orchestration, API calls to Groq/LLMs, embedding computation and vector similarity search.
- Must not: know anything about HTTP or MongoDB queries
- Example: `ai_service.py`, `embedding_service.py`, `search_eval.py`, `schemas.py`, `services.py`

### repositories/
- Owns: all MongoEngine queries (save, find, delete)
- Must not: contain business logic
- Example: `stock_event_repo.py`

### models/
- Owns: MongoEngine Document class + field definitions
- Must not: contain business logic methods
- Example: `stock_event.py`


## Project structure

```text
interneers-invmgt/
├── inventory-project/
│   ├── config/             → Django settings, urls, wsgi
│   ├── products/           → product domain
│   │   ├── controllers/    → views.py (API endpoints)
│   │   ├── services/       → ai_service.py (Groq), embedding_service.py (vectors), search_eval.py, schemas.py, services.py
│   │   ├── repositories/   → stock_event_repo.py, repository.py
│   │   └── models/         → stock_event.py, models.py (includes embedding field)
│   ├── categories/         → category domain
│   ├── dashboard.py        → Streamlit UI (Decoupled Dashboard)
│   └── manage.py
├── docker-compose.yml      → runs MongoDB locally
├── requirements.txt
├── .env                    → secrets (GROQ_API_KEY)
└── .env.example
```

## Design decisions

### Why hexagonal architecture?
Problem: If views talk directly to MongoDB, you can't test business logic without a real database running, and you can't cleanly integrate external services (like LLMs).

Decision: Strict layers where the service layer has zero knowledge of HTTP or MongoDB. Controllers depend on services, services depend on repository interfaces. AI logic (`ai_service.py`) and data validation (`schemas.py`) perfectly slot into the service layer without contaminating the database layers.

Trade-off: More files and folders than a standard Django project. Worth it because every service method can be unit tested by mocking the repository.

### Why MongoDB over Django's default SQLite/Postgres?
Problem: Product attributes vary — electronics have voltage specs, food items have expiry dates. A fixed SQL schema requires constant migrations for new fields.

Decision: MongoDB's flexible documents let each product carry only the fields it needs without schema migrations.

Trade-off: No Django ORM, no makemigrations. MongoEngine replaces the ORM but has less community support than Django ORM.

### Why Groq and Pydantic for AI Integration?
Problem: LLMs produce unpredictable, unstructured strings. Trying to save raw LLM output into a rigid MongoDB schema will crash the application.

Decision: Use Groq (via Llama 3) for extremely fast, free token generation. Then immediately pipe the raw JSON through strict **Pydantic schemas** (`ProductSchema`, `StockEventSchema`). If the LLM hallucinates an invalid category or a negative price, Pydantic catches it in the service layer *before* it ever touches the repository.

### Why soft deletes?
Problem: Hard-deleting a product loses its stock history and breaks any audit references pointing to that ID.

Decision: Products get `is_deleted=True` + `deleted_at` timestamp. All queries filter on `is_deleted=False` automatically in the repository layer.

### Why sentence-transformers for Semantic Search?
Problem: Keyword search (`str.contains`) fails when users search for concepts like "construction toys" — it returns nothing because the word "construction" doesn't appear in "Lego Castle".

Decision: Use the `all-MiniLM-L6-v2` model from `sentence-transformers` to convert every product's name + description into a 384-dimensional vector (embedding). User queries are converted with the same model, and cosine similarity finds the closest products by *meaning*, not character matching.

Why this model?
- 384 dimensions (compact, fast to compare)
- ~90 MB download (won't eat RAM)
- ~14,000 sentences/sec on CPU
- Trained on 1B+ sentence pairs
- For our inventory size (100–500 products), it delivers the same quality as the larger `all-mpnet-base-v2` (768D) at 5× the speed.

Why store embeddings in the Product document?
- Computing embeddings takes ~50ms per product. With 500 products and on-the-fly computation, every search would take 25 seconds.
- Pre-computing and storing them in a `ListField(FloatField())` makes search instant (<100ms).
- Trade-off: Each product document grows by ~3 KB. Acceptable for our scale.

### Search Quality (measured via evalset)
We maintain 8 hand-crafted test cases in `search_eval.py` covering every toy category.  Each test case specifies relevant and irrelevant keywords, and we measure:

- **Precision** — "Of the results returned, how many were correct?" 
- **Recall** — "Of all correct products, how many did we find?"
- **F1 Score** — Harmonic mean of precision and recall.

Accuracy depends on the products in the database. With AI-generated toy-store data (50+ products across 10 categories), typical results are:

| Metric | Score |
|--------|-------|
| Avg Precision | 60–80% |
| Avg Recall | 40–65% |
| F1 Score | 50–70% |

These are measured by running `GET /api/v1/products/evaluate-search/` which executes all 8 test queries, compares results against expected keywords, and returns per-query + aggregate scores. The scores will vary depending on how many products exist in the database and how diverse their descriptions are.

### Why Retrieval-Augmented Generation (RAG)? (Week 8)
Problem: LLMs like Llama 3 hallucinate answers when asked about specific company policies or product manuals they weren't trained on.

Decision: We implemented RAG using LangChain and ChromaDB. 
1. **Ingestion**: We chunk text documents (e.g., `return_policy.txt`) into 500-character segments with 50-character overlap to preserve context.
2. **Storage**: Chunks are embedded using `sentence-transformers` and stored in a local `ChromaDB` vector database (ideal for scaling document retrieval vs. storing in MongoDB).
3. **Retrieval & Generation**: When a user asks a question, LangChain searches ChromaDB for the top 3 most relevant chunks, injects them into a strict prompt template, and sends it to Groq. The LLM is forced to answer *only* using that context ("Grounded AI").

### Advanced RAG: Combining Vector and Document Stores
We also implemented an Advanced Mode (`ask_expert_with_stock`) that combines standard document RAG with a live database query.
- It fetches Policy/Manual context from ChromaDB.
- It parses the user query and fetches live stock levels from MongoDB.
- Both contexts are passed to the LLM, allowing it to answer complex queries like *"What is the return policy for the Lego Castle, and do we have it in stock?"*

### AI Sales Agent (Week 9 & 10)
Problem: LLMs cannot take actions or perform deterministic math. We needed an AI that could calculate quotes and apply discounts without being tricked.

Decision: We implemented the ReAct pattern using LangChain's `create_tool_calling_agent`.
1. **Tool Creation**: We built three `@tool` Python functions: `get_product_info`, `check_inventory`, and `calculate_quote`.
2. **Deterministic Overrides**: The `calculate_quote` tool mathematically computes the invoice and enforces a hard limit: if the LLM passes a requested discount > 20%, the Python function rejects the quote and returns a `POLICY_VIOLATION` error to the LLM. 
3. **Execution**: The Agent thinks ("I need to find the product ID"), acts (calls `get_product_info`), observes the result, and loops until the goal is completed.

## What I'd do differently in production
- Set up automated archiving of soft-deleted records.
- Unify standard HTTP payload validation and AI validation using Pydantic across the board.
- Use a dedicated vector database (e.g., Pinecone, Weaviate, or MongoDB Atlas Vector Search) instead of storing embeddings in the same document — better for scale and ANN (Approximate Nearest Neighbor) performance.
- Auto-recompute embeddings when products are created or updated via a post-save signal.
