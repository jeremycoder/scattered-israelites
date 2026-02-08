import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from lexicon.models import Lexeme


class Command(BaseCommand):
    help = 'Import Strong’s lexemes from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to strongs.csv')
        parser.add_argument(
            '--allow-nonempty',
            action='store_true',
            help='Allow import even if Lexeme table is not empty.',
        )

    def handle(self, *args, **options):
        csv_path = Path(options['csv_path']).expanduser()
        if not csv_path.exists():
            raise CommandError(f'File not found: {csv_path}')

        if Lexeme.objects.exists() and not options['allow_nonempty']:
            raise CommandError(
                'Lexeme table is not empty. Use --allow-nonempty to proceed.'
            )

        created = 0
        to_create = []
        with csv_path.open(newline='', encoding='utf-8') as handle:
            reader = csv.DictReader(handle)
            required = {'number', 'lemma', 'xlit', 'description'}
            if not required.issubset(reader.fieldnames or set()):
                raise CommandError(
                    f'CSV missing required headers: {sorted(required)}'
                )

            with transaction.atomic():
                for row in reader:
                    strongs_id = (row.get('number') or '').strip()
                    if not strongs_id:
                        continue
                    language = 'hebrew' if strongs_id.startswith('H') else 'greek'
                    to_create.append(
                        Lexeme(
                            strongs_id=strongs_id,
                            language=language,
                            lemma=(row.get('lemma') or '').strip(),
                            transliteration=(row.get('xlit') or '').strip(),
                            gloss=(row.get('description') or '').strip(),
                        )
                    )
                created = len(to_create)
                Lexeme.objects.bulk_create(to_create, batch_size=1000)

        self.stdout.write(
            self.style.SUCCESS(f'Imported lexemes. Created: {created}')
        )
