"""
Embedding Service  —  the brain behind semantic search.

This service converts product text into 384-dimensional vectors using the
all-MiniLM-L6-v2 model from sentence-transformers, then uses cosine
similarity to find products that are semantically related to a query —
even when they share zero keywords.

It lives in the *services* layer because it contains business logic
(similarity thresholds, search ranking).  It never touches MongoDB
directly; it calls ProductRepository for that.
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from products.repositories.repository import ProductRepository


class EmbeddingService:
    """
    Handles everything related to converting product text into numerical
    vectors and finding products by meaning instead of keywords.
    """

    # ── Model loading ──────────────────────────────────────────────────
    # We use "lazy loading" — the heavy model file (~90 MB) is only
    # downloaded and loaded into memory the FIRST time someone actually
    # triggers a search.  After that it stays cached in this class variable
    # so subsequent calls are instant.
    _model = None

    @staticmethod
    def _get_model():
        """
        Load the sentence-transformer model once and cache it.

        Why all-MiniLM-L6-v2?
        - It outputs 384-dimensional vectors (compact, fast to compare).
        - It was trained on over 1 billion sentence pairs.
        - It's only ~90 MB — won't eat up your RAM.
        - It encodes ~14,000 sentences per second on CPU.
        """
        if EmbeddingService._model is None:
            EmbeddingService._model = SentenceTransformer("all-MiniLM-L6-v2")
        return EmbeddingService._model

    # ── Single text → vector ───────────────────────────────────────────

    @staticmethod
    def compute_embedding(text: str) -> list[float]:
        """
        Convert any piece of text into a list of 384 numbers (floats).

        These numbers represent the *meaning* of the text.  Two texts with
        similar meanings will produce similar numbers, even if they share
        zero words.

        Example:
            compute_embedding("Lego Castle")  → [0.03, -0.12, 0.45, ...]
            compute_embedding("Building Set") → [0.05, -0.10, 0.42, ...]
            # ^ These two lists will be very similar because the meanings
            #   of "Lego Castle" and "Building Set" overlap.
        """
        model = EmbeddingService._get_model()
        # model.encode returns a numpy array; we convert to a plain Python
        # list so it can be stored in MongoDB (which doesn't understand numpy).
        vector = model.encode(text)
        return vector.tolist()

    # ── Batch: compute embeddings for ALL products ─────────────────────

    @staticmethod
    def compute_all_embeddings() -> dict:
        """
        Loop through every product in the database, combine its name and
        description into one string, convert that string into a 384-number
        vector, and save the vector back to the product document.

        This is meant to be run once (or whenever new products are added)
        to "prepare" the database for semantic search.

        Returns a summary dict with counts of how many were processed.
        """
        model = EmbeddingService._get_model()
        products = ProductRepository.get_all()

        # Build a list of texts to encode in one batch (much faster than
        # encoding one product at a time because the model can process
        # them in parallel on the GPU / CPU).
        product_list = list(products)
        texts = []
        for p in product_list:
            # Combine name + description so the vector captures both.
            # If description is empty, we just use the name alone.
            combined = p.name
            if p.description:
                combined += " — " + p.description
            texts.append(combined)

        if not texts:
            return {"computed": 0, "total": 0}

        # Encode everything in one batch — this is where the heavy lifting
        # happens.  The model reads every text and returns a 2D numpy array
        # of shape (num_products, 384).
        embeddings = model.encode(texts, show_progress_bar=True)

        # Save each embedding back to its product in MongoDB
        computed = 0
        for product, embedding_vector in zip(product_list, embeddings):
            ProductRepository.update_embedding(
                str(product.id),
                embedding_vector.tolist()
            )
            computed += 1

        return {"computed": computed, "total": len(product_list)}

    # ── Cosine similarity ──────────────────────────────────────────────

    @staticmethod
    def cosine_similarity(vec_a, vec_b) -> float:
        """
        Measure how similar two vectors are by looking at the angle
        between them, not the distance.

        Returns a number between -1 and 1:
            1.0  = identical meaning
            0.0  = completely unrelated
           -1.0  = opposite meaning (rare in practice)

        Why cosine and not plain distance?
        Because cosine ignores "magnitude" (the length of the vector) and
        only cares about "direction".  A short product description and a
        long one can still point in the same direction semantically.

        The formula:
                        A · B
            cos(θ) = ─────────
                      |A| × |B|
        """
        a = np.array(vec_a)
        b = np.array(vec_b)

        # Dot product: multiply matching positions, sum them up
        dot = np.dot(a, b)

        # Magnitude (length) of each vector
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        # Guard against division by zero (shouldn't happen, but just in case
        # a product has an all-zero embedding somehow)
        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot / (norm_a * norm_b))

    # ── Semantic search ────────────────────────────────────────────────

    @staticmethod
    def semantic_search(query: str, top_k: int = 10, threshold: float = 0.25) -> list[dict]:
        """
        The main search function.  Given a text query (like "construction
        toys"), find the top_k most semantically similar products.

        How it works, step by step:
        1. Convert the query into a 384-number vector.
        2. Fetch all products that have pre-computed embeddings.
        3. Calculate cosine similarity between the query vector and each
           product's vector.
        4. Filter out anything below the threshold (default 0.25 — meaning
           at least 25% similar).
        5. Sort by similarity (highest first) and return the top_k.

        Args:
            query:     The user's search text, e.g. "gifts for toddlers"
            top_k:     Maximum number of results to return (default 10)
            threshold: Minimum similarity score to include a result (0–1)

        Returns:
            A list of dicts, each containing the product info + its
            similarity score, sorted from most to least similar.
        """
        # Step 1 — Turn the query into numbers
        query_vector = EmbeddingService.compute_embedding(query)

        # Step 2 — Get all products that have embeddings
        products = ProductRepository.get_products_with_embeddings()

        # Step 3 — Compare the query against every product
        results = []
        for product in products:
            similarity = EmbeddingService.cosine_similarity(
                query_vector, product.embedding
            )

            # Step 4 — Only keep products above the similarity threshold
            if similarity >= threshold:
                results.append({
                    "id": str(product.id),
                    "sku": product.sku,
                    "name": product.name,
                    "description": product.description or "",
                    "brand": product.brand,
                    "category": product.category.title if product.category else "—",
                    "quantity": product.quantity,
                    "price": product.price,
                    "similarity": round(similarity, 4),
                })

        # Step 5 — Sort by similarity score (highest = best match first)
        results.sort(key=lambda x: x["similarity"], reverse=True)

        # Only return the top_k results
        return results[:top_k]

    # ── Find similar products ──────────────────────────────────────────

    @staticmethod
    def find_similar_products(product_id: str, top_k: int = 5) -> list[dict]:
        """
        Given one product, find the most similar products in the database.

        This is the "Find Similar" feature — like Amazon's "Customers who
        viewed this also viewed..." except we're using semantic similarity
        of descriptions, not purchase history.

        How it works:
        1. Fetch the target product's pre-computed embedding.
        2. Compare it against every OTHER product's embedding.
        3. Return the top_k most similar ones (excluding the product itself).
        """
        from products.models.models import Product

        target = Product.objects(id=product_id).first()
        if not target or not target.embedding:
            return []

        # Get all other products that have embeddings
        all_products = ProductRepository.get_products_with_embeddings()

        results = []
        for product in all_products:
            # Skip the product we're comparing against (itself)
            if str(product.id) == product_id:
                continue

            similarity = EmbeddingService.cosine_similarity(
                target.embedding, product.embedding
            )

            results.append({
                "id": str(product.id),
                "sku": product.sku,
                "name": product.name,
                "description": product.description or "",
                "brand": product.brand,
                "category": product.category.title if product.category else "—",
                "quantity": product.quantity,
                "price": product.price,
                "similarity": round(similarity, 4),
            })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]
