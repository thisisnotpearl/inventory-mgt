import os
import json
from groq import Groq
from products.services.schemas import ProductSchema, StockEventSchema, SCENARIO_HINTS, VALID_CATEGORIES
from pydantic import ValidationError

class AIService:

    @staticmethod
    def generate_products(count: int = 50, scenario: str = "standard") -> dict:
        hint = SCENARIO_HINTS.get(scenario, SCENARIO_HINTS["standard"])
        cats = ", ".join(VALID_CATEGORIES)
        prompt = f"Generate exactly {count} unique toy-store products for this scenario: {hint}. Return a JSON object with a single key 'products' containing an array of objects. Fields: name, description, category (must be from {cats}), quantity, price, brand."
        
        raw, usage = AIService._call_groq(prompt)
        valid, errors = AIService._validate(raw, ProductSchema)
        return {"valid": valid, "errors": errors, "usage": usage}

    @staticmethod
    def generate_stock_events(sku_list: list) -> dict:
        sku_text = ", ".join([p["sku"] for p in sku_list])
        prompt = f"Generate exactly 10 realistic future stock events for a toy-store warehouse using these SKUs: {sku_text}. Return a JSON object with a single key 'events' containing an array of objects. Fields: product_sku, product_name, event_type, expected_date, quantity_delta, unit_price, supplier, notes."
        
        raw, usage = AIService._call_groq(prompt)
        valid, errors = AIService._validate(raw, StockEventSchema)
        return {"valid": valid, "errors": errors, "usage": usage}

    @staticmethod
    def _call_groq(prompt: str, temperature: float = 0.9) -> tuple[list, dict]:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY not found in environment.")
            
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a data generator. Return JSON object with a single array key containing the items."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=temperature
        )
        
        data = json.loads(response.choices[0].message.content)
        items = list(data.values())[0] if isinstance(data, dict) else data
        usage = response.usage
        
        usage_dict = {
            "prompt_tokens": usage.prompt_tokens if hasattr(usage, 'prompt_tokens') else 0,
            "completion_tokens": usage.completion_tokens if hasattr(usage, 'completion_tokens') else 0,
            "total_tokens": usage.total_tokens if hasattr(usage, 'total_tokens') else 0,
            "cost_usd": 0.0  # Groq is free
        }
        return items, usage_dict

    @staticmethod
    def _validate(raw: list[dict], schema_class) -> tuple[list, list]:
        valid = []
        errors = []
        for item in raw:
            try:
                validated = schema_class(**item)
                valid.append(validated.model_dump())
            except ValidationError as e:
                errors.append({"raw": item, "error": str(e)})
        return valid, errors
