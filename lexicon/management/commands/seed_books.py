from django.core.management.base import BaseCommand

from lexicon.bible import BOOKS
from lexicon.models import Book


class Command(BaseCommand):
    help = 'Seed the Book table with standard OSIS books.'

    def handle(self, *args, **options):
        created = 0
        for osis_id, name, testament, order in BOOKS:
            _, is_created = Book.objects.get_or_create(
                osis_id=osis_id,
                defaults={
                    'name': name,
                    'testament': testament,
                    'canonical_order': order,
                },
            )
            if is_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Books created: {created}'))
