"""
RAG Evaluation Suite

Tests the accuracy of the Retrieval-Augmented Generation pipeline.
Contains two suites:
1. Retrieval Evaluation: Checks if the vector DB fetches the correct chunks.
2. Generation Evaluation: Checks if the LLM answers correctly without hallucinating.
"""

from products.services.rag_service import RAGService

# ── 1. Retrieval Eval Suite ──────────────────────────────────────────
RETRIEVAL_TEST_CASES = [
    {
        "query": "What is the return policy for damaged items?",
        "expected_keyword_in_chunk": "damaged in transit or defective out of the box",
        "description": "Should retrieve the damaged items section of the return policy"
    },
    {
        "query": "How are stock deliveries scheduled for vendors?",
        "expected_keyword_in_chunk": "Warehouse Management System",
        "description": "Should retrieve the delivery scheduling FAQ"
    },
    {
        "query": "Does the Lego Castle have a warranty?",
        "expected_keyword_in_chunk": "1-year limited manufacturer warranty",
        "description": "Should retrieve the Lego Castle manual excerpt"
    }
]

# ── 2. Generation Eval Suite ─────────────────────────────────────────
GENERATION_TEST_CASES = [
    {
        "query": "What is the return policy for clearance items?",
        "expected_answer_contains": ["non-returnable", "strictly non-returnable"],
        "description": "LLM should correctly state clearance is non-returnable"
    },
    {
        "query": "What batteries do I need for the Remote Control Racing Car?",
        "expected_answer_contains": ["4x AA", "4 AA", "2x AAA", "2 AAA"],
        "description": "LLM should extract exact battery requirements"
    },
    {
        "query": "Who is the CEO of the Toy Store?",
        "expected_answer_contains": ["don't have enough information", "don't know", "cannot answer"],
        "description": "LLM must NOT hallucinate an answer outside the context"
    }
]


class RAGEvaluator:

    @staticmethod
    def run_retrieval_eval():
        """Tests if the vector search finds the right chunks."""
        results = []
        passed = 0

        for case in RETRIEVAL_TEST_CASES:
            try:
                chunks = RAGService.retrieve_relevant_chunks(case["query"], top_k=3)
                combined_text = " ".join([c["content"] for c in chunks]).lower()
                
                # Check if the expected string is somewhere in the top 3 chunks
                expected = case["expected_keyword_in_chunk"].lower()
                is_pass = expected in combined_text
                
                if is_pass:
                    passed += 1

                results.append({
                    "query": case["query"],
                    "passed": is_pass,
                    "expected": case["expected_keyword_in_chunk"],
                    "found_chunks": len(chunks)
                })
            except Exception as e:
                results.append({
                    "query": case["query"],
                    "passed": False,
                    "error": str(e)
                })

        score = (passed / len(RETRIEVAL_TEST_CASES)) * 100 if RETRIEVAL_TEST_CASES else 0
        return {"retrieval_score_pct": score, "details": results}


    @staticmethod
    def run_generation_eval():
        """Tests if the LLM answers correctly without hallucinating."""
        results = []
        passed = 0

        for case in GENERATION_TEST_CASES:
            try:
                response = RAGService.ask_expert(case["query"])
                answer = response["answer"].lower()
                
                # Check if ANY of the expected phrases are in the LLM's answer
                is_pass = any(phrase.lower() in answer for phrase in case["expected_answer_contains"])
                
                if is_pass:
                    passed += 1

                results.append({
                    "query": case["query"],
                    "passed": is_pass,
                    "llm_answer": response["answer"]
                })
            except Exception as e:
                results.append({
                    "query": case["query"],
                    "passed": False,
                    "error": str(e)
                })

        score = (passed / len(GENERATION_TEST_CASES)) * 100 if GENERATION_TEST_CASES else 0
        return {"generation_score_pct": score, "details": results}
