from pydantic import BaseModel, Field

VALID_CATEGORIES = [
    "Action Figures", "Board Games", "Building Blocks", "Educational Toys",
    "Outdoor Toys", "Puzzles", "Remote Control", "Stuffed Animals",
    "Arts & Crafts", "Science Kits",
]

SCENARIO_HINTS = {
    "standard": "Normal stock mix across all toy categories",
    "holiday_rush": "Christmas/Diwali — high stock, premium gift-sets",
    "summer_sale": "Clearance — low prices, outdoor & water toys",
    "back_to_school": "Educational toys, science kits, art supplies",
    "clearance": "End-of-season — rock-bottom prices, minimal stock",
}

class ProductSchema(BaseModel):
    name:        str    = Field(..., min_length=2, max_length=100)
    description: str    = Field(..., min_length=10, max_length=500)
    category:    str    = Field(...)
    quantity:    int    = Field(..., ge=0)
    price:       float  = Field(..., gt=0)
    brand:       str    = Field(..., min_length=2)

class StockEventSchema(BaseModel):
    product_sku:    str   = Field(...)
    product_name:   str   = Field(...)
    event_type:     str   = Field(...)
    expected_date:  str   = Field(...)
    quantity_delta: int   = Field(...)
    unit_price:     float = Field(default=0.0)
    supplier:       str   = Field(default="")
    notes:          str   = Field(default="")
