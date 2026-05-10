"""
Search Evaluation  —  how we measure if semantic search is actually good.

Building a search engine isn't enough.  You need to *prove* it works.
This file contains:

1. SEARCH_TEST_CASES — a hand-crafted list of queries and expected results.
   For each query, WE (the humans) decide which products should appear
   and which should NOT appear.

2. evaluate_search() — a function that runs every test case through the
   search function, compares the results against our expectations, and
   calculates precision and recall.

What are precision and recall?
- Precision = "Of the results the search returned, how many were correct?"
- Recall    = "Of all correct products that exist, how many did the search find?"

This file lives in the services layer because evaluation is business logic —
it decides whether the search quality meets our standards.
"""


# ── Test cases ─────────────────────────────────────────────────────────
# Each test case has:
#   - query: what the user would type in the search bar
#   - relevant_keywords: words that SHOULD appear in the top results
#     (we use keywords in names/descriptions because actual SKUs change
#      every time you regenerate AI data)
#   - irrelevant_keywords: words that should NOT appear in top results

SEARCH_TEST_CASES = [
    {
        "query": "construction toys",
        "relevant_keywords": ["block", "build", "lego", "construct", "brick", "stack"],
        "irrelevant_keywords": ["teddy", "plush", "stuffed", "bear"],
        "description": "Building/construction toys should rank highest",
    },
    {
        "query": "gifts for toddlers",
        "relevant_keywords": ["soft", "plush", "baby", "toddler", "rattle", "infant"],
        "irrelevant_keywords": ["puzzle 1000", "advanced", "teen", "adult"],
        "description": "Young-child-safe toys should rank highest",
    },
    {
        "query": "outdoor fun for summer",
        "relevant_keywords": ["outdoor", "water", "garden", "pool", "ball", "sport"],
        "irrelevant_keywords": ["puzzle", "board game", "indoor", "electronic"],
        "description": "Outdoor / summer toys should rank highest",
    },
    {
        "query": "educational science activities",
        "relevant_keywords": ["science", "experiment", "learn", "education", "stem", "kit"],
        "irrelevant_keywords": ["action figure", "doll", "car", "truck"],
        "description": "Science/learning kits should rank highest",
    },
    {
        "query": "creative arts and crafts",
        "relevant_keywords": ["art", "craft", "paint", "draw", "color", "creative"],
        "irrelevant_keywords": ["remote control", "racing", "electronic"],
        "description": "Arts & crafts products should rank highest",
    },
    {
        "query": "remote control vehicles",
        "relevant_keywords": ["remote", "control", "rc", "car", "drone", "vehicle"],
        "irrelevant_keywords": ["stuffed", "plush", "paint", "craft"],
        "description": "RC toys should rank highest",
    },
    {
        "query": "board games for family night",
        "relevant_keywords": ["board", "game", "family", "card", "strategy", "player"],
        "irrelevant_keywords": ["outdoor", "water", "gun", "ball"],
        "description": "Board/card games should rank highest",
    },
    {
        "query": "superhero action toys",
        "relevant_keywords": ["action", "hero", "figure", "super", "marvel", "batman"],
        "irrelevant_keywords": ["puzzle", "paint", "craft", "science"],
        "description": "Action figures / superhero toys should rank highest",
    },
]


def evaluate_search(search_function, top_k: int = 10) -> dict:
    """
    Run every test case through the given search function and measure
    how well it performs using precision and recall.

    Args:
        search_function: A callable that takes a query string and top_k int,
                        and returns a list of result dicts (each with 'name'
                        and 'description' keys).
        top_k:          How many results to request from the search function.

    Returns:
        A dict with:
        - per_query: detailed results for each test case
        - avg_precision: average precision across all queries
        - avg_recall: average recall across all queries
        - overall_score: harmonic mean of avg precision and recall (F1)

    How scoring works for each query:
    ─────────────────────────────────
    1. We run the search and get back top_k results.
    2. For each result, we check if its name or description contains ANY
       of the relevant_keywords → if yes, it's a "hit" (correct result).
    3. Precision = hits / total_results_returned
       "Of everything we showed the user, what fraction was actually good?"
    4. Recall = hits / len(relevant_keywords)
       "Of the relevant keyword categories, how many did we cover?"
       (This is an approximation since we don't know the true full set of
        relevant products, but it works well for measuring coverage.)
    """
    per_query = []
    total_precision = 0.0
    total_recall = 0.0
    evaluated = 0

    for case in SEARCH_TEST_CASES:
        query = case["query"]
        relevant = [kw.lower() for kw in case["relevant_keywords"]]
        irrelevant = [kw.lower() for kw in case["irrelevant_keywords"]]

        # Run the search
        try:
            results = search_function(query, top_k)
        except Exception as e:
            per_query.append({
                "query": query,
                "error": str(e),
                "precision": 0.0,
                "recall": 0.0,
            })
            continue

        if not results:
            per_query.append({
                "query": query,
                "results_count": 0,
                "hits": 0,
                "precision": 0.0,
                "recall": 0.0,
                "description": case["description"],
            })
            continue

        # Count hits: how many results contain at least one relevant keyword
        hits = 0
        irrelevant_hits = 0
        result_details = []

        for r in results:
            # Combine name + description into one searchable string
            text = (r.get("name", "") + " " + r.get("description", "")).lower()

            is_relevant = any(kw in text for kw in relevant)
            is_irrelevant = any(kw in text for kw in irrelevant)

            if is_relevant:
                hits += 1
            if is_irrelevant:
                irrelevant_hits += 1

            result_details.append({
                "name": r.get("name", ""),
                "similarity": r.get("similarity", 0),
                "is_relevant": is_relevant,
            })

        # Calculate metrics
        precision = hits / len(results) if results else 0.0
        # For recall, we check how many of the relevant keyword groups
        # were represented in the results
        keywords_found = sum(
            1 for kw in relevant
            if any(kw in (r.get("name", "") + " " + r.get("description", "")).lower() for r in results)
        )
        recall = keywords_found / len(relevant) if relevant else 0.0

        total_precision += precision
        total_recall += recall
        evaluated += 1

        per_query.append({
            "query": query,
            "description": case["description"],
            "results_count": len(results),
            "hits": hits,
            "irrelevant_hits": irrelevant_hits,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "top_3": result_details[:3],
        })

    # Average across all test cases
    avg_precision = total_precision / evaluated if evaluated else 0.0
    avg_recall = total_recall / evaluated if evaluated else 0.0

    # F1 score: the harmonic mean of precision and recall
    # It gives a single number that balances both metrics.
    # If either precision or recall is 0, F1 is 0.
    if avg_precision + avg_recall > 0:
        f1 = 2 * (avg_precision * avg_recall) / (avg_precision + avg_recall)
    else:
        f1 = 0.0

    return {
        "per_query": per_query,
        "avg_precision": round(avg_precision, 4),
        "avg_recall": round(avg_recall, 4),
        "f1_score": round(f1, 4),
        "queries_evaluated": evaluated,
        "model_used": "all-MiniLM-L6-v2",
    }
