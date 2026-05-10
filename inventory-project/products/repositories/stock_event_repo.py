from products.models.stock_event import StockEvent

class StockEventRepository:

    @staticmethod
    def bulk_create(events_data: list[dict]):
        docs = []
        for event_dict in events_data:
            doc = StockEvent(**event_dict)
            docs.append(doc)
        if docs:
            StockEvent.objects.insert(docs)
        return docs, []

    @staticmethod
    def get_all(status: str = None) -> list[StockEvent]:
        if status and status != "All":
            return list(StockEvent.objects(status=status))
        return list(StockEvent.objects.all())

    @staticmethod
    def get_by_product(sku: str) -> list[StockEvent]:
        return list(StockEvent.objects(product_sku=sku))
