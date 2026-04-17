from django.core.management.base import BaseCommand
from products.models.models import Product
 
 
class Command(BaseCommand):
    help = "Backfills missing or empty brand field on Product documents with 'Unknown'"
 
    def handle(self, *args, **kwargs):
        self.stdout.write("Starting brand field migration...")
 
        missing = Product.objects(brand__exists=False).update(set__brand="Unknown")
        empty   = Product.objects(brand="").update(set__brand="Unknown")
        total   = missing + empty
 
        self.stdout.write(f"  Fixed missing brand : {missing} document(s)")
        self.stdout.write(f"  Fixed empty brand   : {empty} document(s)")
        self.stdout.write(
            self.style.SUCCESS(f"Migration complete. {total} document(s) updated.")
        )