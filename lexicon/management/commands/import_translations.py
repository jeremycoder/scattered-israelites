import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from lexicon.models import Book, TranslationBatch, Verse, WordOccurrence, WordTranslation


class Command(BaseCommand):
    help = 'Import contextual word translations from a JSON file.'

    def add_arguments(self, parser):
        parser.add_argument('json_path', type=str, help='Path to translations JSON file')
        parser.add_argument('--prompt', type=str, default='', help='The prompt sent to the AI model')
        parser.add_argument('--model', type=str, default='', help='AI model name (e.g. sonar-pro)')

    def handle(self, *args, **options):
        json_path = Path(options['json_path']).expanduser()
        if not json_path.exists():
            raise CommandError(f'File not found: {json_path}')

        prompt_text = options['prompt']
        model_name = options['model']

        with json_path.open(encoding='utf-8') as f:
            data = json.load(f)

        # Accept single object or array
        if isinstance(data, dict):
            entries = [data]
        elif isinstance(data, list):
            entries = data
        else:
            raise CommandError('JSON must be an object or array of objects.')

        total_created = 0
        total_updated = 0
        total_skipped = 0
        total_errors = 0
        total_batches = 0

        for entry in entries:
            # Validate required fields
            missing = False
            for field in ('book', 'chapter', 'verse', 'language_code', 'language_name', 'words'):
                if field not in entry:
                    self.stderr.write(self.style.ERROR(f'Missing field "{field}" in entry: {entry}'))
                    total_errors += 1
                    missing = True
            if missing:
                continue

            book_name = entry['book']
            chapter = entry['chapter']
            verse_num = entry['verse']
            lang_code = entry['language_code']
            lang_name = entry['language_name']
            words_data = entry['words']

            # Look up the verse
            try:
                book = Book.objects.get(name=book_name)
            except Book.DoesNotExist:
                self.stderr.write(self.style.ERROR(
                    f'Book not found: "{book_name}"'
                ))
                total_errors += 1
                continue

            try:
                verse = Verse.objects.get(book=book, chapter=chapter, verse=verse_num)
            except Verse.DoesNotExist:
                self.stderr.write(self.style.ERROR(
                    f'Verse not found: {book_name} {chapter}:{verse_num}'
                ))
                total_errors += 1
                continue

            # Build a lookup of word occurrences by position
            word_occurrences = {
                wo.position: wo
                for wo in WordOccurrence.objects.filter(verse=verse)
            }

            with transaction.atomic():
                # Create audit-trail batch for this verse+language
                batch = TranslationBatch.objects.create(
                    verse=verse,
                    language_code=lang_code,
                    language_name=lang_name,
                    prompt=prompt_text,
                    raw_response=entry,
                    model_name=model_name,
                )
                total_batches += 1

                for wd in words_data:
                    position = wd.get('position')
                    phrase = wd.get('phrase', '')

                    if not position or not phrase:
                        self.stderr.write(self.style.WARNING(
                            f'  Skipping word (missing position or phrase): {wd}'
                        ))
                        total_skipped += 1
                        continue

                    wo = word_occurrences.get(position)
                    if wo is None:
                        self.stderr.write(self.style.WARNING(
                            f'  No WordOccurrence at position {position} in {book_name} {chapter}:{verse_num}'
                        ))
                        total_skipped += 1
                        continue

                    _obj, created = WordTranslation.objects.update_or_create(
                        word=wo,
                        language_code=lang_code,
                        defaults={
                            'language_name': lang_name,
                            'phrase': phrase,
                            'literal': wd.get('literal', ''),
                            'source': wd.get('source', ''),
                            'batch': batch,
                        },
                    )

                    if created:
                        total_created += 1
                    else:
                        total_updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Import complete. Batches: {total_batches}, Created: {total_created}, '
            f'Updated: {total_updated}, Skipped: {total_skipped}, Errors: {total_errors}'
        ))
