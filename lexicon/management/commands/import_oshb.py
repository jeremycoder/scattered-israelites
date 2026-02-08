import re
from pathlib import Path
from xml.etree import ElementTree as ET

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from lexicon.bible import BOOKS_BY_OSIS
from lexicon.models import Book, Verse, WordOccurrence


VERSE_RE = re.compile(r'^(?P<book>[^.]+)\.(?P<chapter>\d+)\.(?P<verse>\d+)')


class Command(BaseCommand):
    help = 'Import Hebrew word occurrences from OSHB OSIS XML.'

    def add_arguments(self, parser):
        parser.add_argument('xml_dir', type=str, help='Directory containing OSIS XML files')
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
        xml_dir = Path(options['xml_dir']).expanduser()
        if not xml_dir.exists() or not xml_dir.is_dir():
            raise CommandError(f'Not a directory: {xml_dir}')

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

        def get_verse(osis_id):
            if osis_id in verses_cache:
                return verses_cache[osis_id]
            match = VERSE_RE.match(osis_id)
            if not match:
                raise CommandError(f'Unexpected OSIS verse id: {osis_id}')
            book_id = match.group('book')
            chapter = int(match.group('chapter'))
            verse_num = int(match.group('verse'))
            book = get_book(book_id)
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

        def strip_tag(tag):
            return tag.split('}', 1)[-1]

        xml_files = sorted(xml_dir.glob('*.xml'))
        if not xml_files:
            raise CommandError(f'No XML files found in {xml_dir}')

        for xml_file in xml_files:
            current_osis = None
            position = 0
            file_count = 0
            for event, elem in ET.iterparse(xml_file, events=('start', 'end')):
                tag = strip_tag(elem.tag)
                if event == 'start' and tag == 'verse':
                    osis_id = elem.get('osisID') or elem.get('sID')
                    if osis_id:
                        current_osis = osis_id
                        position = 0
                elif event == 'end' and tag == 'verse':
                    osis_id = elem.get('osisID') or elem.get('eID')
                    if osis_id and osis_id == current_osis:
                        current_osis = None
                elif event == 'end' and tag == 'w' and current_osis:
                    surface = ''.join(elem.itertext()).strip()
                    lemma = (elem.get('lemma') or '').strip()
                    morph = (elem.get('morph') or '').strip()
                    word_id = (elem.get('id') or '').strip()
                    if not surface and not lemma and not morph:
                        continue
                    position += 1
                    verse = get_verse(current_osis)
                    to_create.append(
                        WordOccurrence(
                            verse=verse,
                            position=position,
                            language=WordOccurrence.LANGUAGE_HEBREW,
                            surface=surface,
                            lemma=lemma,
                            morphology=morph,
                            source='oshb',
                            word_id=word_id,
                        )
                    )
                    if len(to_create) >= batch_size:
                        WordOccurrence.objects.bulk_create(to_create, batch_size=batch_size)
                        total += len(to_create)
                        file_count += len(to_create)
                        to_create.clear()
                if event == 'end':
                    elem.clear()

            if to_create:
                WordOccurrence.objects.bulk_create(to_create, batch_size=batch_size)
                total += len(to_create)
                file_count += len(to_create)
                to_create.clear()

            self.stdout.write(f'{xml_file.name}: {file_count} words')

        self.stdout.write(self.style.SUCCESS(f'Imported OSHB words: {total}'))
