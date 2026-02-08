from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from lexicon.bible import BOOKS_BY_OSIS, MORPHGNT_BOOK_MAP
from lexicon.models import Book, Verse, WordOccurrence


class Command(BaseCommand):
    help = 'Import Greek word occurrences from MorphGNT SBLGNT.'

    def add_arguments(self, parser):
        parser.add_argument('txt_dir', type=str, help='Directory containing MorphGNT .txt files')
        parser.add_argument(
            '--allow-nonempty',
            action='store_true',
            help='Allow import even if WordOccurrence table is not empty.',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Batch size for bulk inserts.',
        )

    def handle(self, *args, **options):
        txt_dir = Path(options['txt_dir']).expanduser()
        if not txt_dir.exists() or not txt_dir.is_dir():
            raise CommandError(f'Not a directory: {txt_dir}')

        if WordOccurrence.objects.exists() and not options['allow_nonempty']:
            raise CommandError(
                'WordOccurrence table is not empty. Use --allow-nonempty to proceed.'
            )

        batch_size = options['batch_size']
        books_cache = {}
        verses_cache = {}
        to_create = []
        total = 0

        def get_book(osis_id):
            if osis_id in books_cache:
                return books_cache[osis_id]
            info = BOOKS_BY_OSIS.get(osis_id)
            if not info:
                raise CommandError(f'Unknown OSIS book id: {osis_id}')
            name, testament, order = info
            book, _ = Book.objects.get_or_create(
                osis_id=osis_id,
                defaults={
                    'name': name,
                    'testament': testament,
                    'canonical_order': order,
                },
            )
            books_cache[osis_id] = book
            return book

        def get_verse(osis_id, book, chapter, verse_num):
            if osis_id in verses_cache:
                return verses_cache[osis_id]
            verse, _ = Verse.objects.get_or_create(
                osis_id=osis_id,
                defaults={
                    'book': book,
                    'chapter': chapter,
                    'verse': verse_num,
                },
            )
            verses_cache[osis_id] = verse
            return verse

        txt_files = sorted(txt_dir.glob('*-morphgnt.txt'))
        if not txt_files:
            raise CommandError(f'No MorphGNT files found in {txt_dir}')

        with transaction.atomic():
            for txt_file in txt_files:
                parts = txt_file.name.split('-')
                if len(parts) < 3:
                    raise CommandError(f'Unexpected file name: {txt_file.name}')
                abbr = parts[1]
                osis_id = MORPHGNT_BOOK_MAP.get(abbr)
                if not osis_id:
                    raise CommandError(f'Unknown MorphGNT book abbreviation: {abbr}')
                book = get_book(osis_id)

                current_ref = None
                position = 0
                with txt_file.open(encoding='utf-8') as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        cols = line.split()
                        if len(cols) < 7:
                            continue
                        bcv, pos, parse, text, word, norm, lemma = cols[:7]
                        chapter = int(bcv[2:4])
                        verse_num = int(bcv[4:6])
                        verse_id = f'{osis_id}.{chapter}.{verse_num}'
                        if verse_id != current_ref:
                            current_ref = verse_id
                            position = 0
                        position += 1
                        verse = get_verse(verse_id, book, chapter, verse_num)
                        to_create.append(
                            WordOccurrence(
                                verse=verse,
                                position=position,
                                language=WordOccurrence.LANGUAGE_GREEK,
                                surface=text,
                                lemma=lemma,
                                morphology=parse,
                                source='morphgnt',
                                part_of_speech=pos,
                                parsing=parse,
                                variant=word,
                                normalized=norm,
                            )
                        )
                        if len(to_create) >= batch_size:
                            WordOccurrence.objects.bulk_create(to_create, batch_size=batch_size)
                            total += len(to_create)
                            to_create.clear()

            if to_create:
                WordOccurrence.objects.bulk_create(to_create, batch_size=batch_size)
                total += len(to_create)

        self.stdout.write(self.style.SUCCESS(f'Imported MorphGNT words: {total}'))
