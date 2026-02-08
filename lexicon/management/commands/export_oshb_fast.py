import csv
import re
from pathlib import Path
from xml.etree import ElementTree as ET

from django.core.management.base import BaseCommand, CommandError

from lexicon.models import WordOccurrence


VERSE_RE = re.compile(r'^(?P<book>[^.]+)\.(?P<chapter>\d+)\.(?P<verse>\d+)')


class Command(BaseCommand):
    help = 'Export OSHB words and verses to CSV without DB lookups.'

    def add_arguments(self, parser):
        parser.add_argument('xml_dir', type=str, help='Directory containing OSIS XML files')
        parser.add_argument('words_csv', type=str, help='Output CSV path for words')
        parser.add_argument('verses_csv', type=str, help='Output CSV path for verses')

    def handle(self, *args, **options):
        xml_dir = Path(options['xml_dir']).expanduser()
        words_csv = Path(options['words_csv']).expanduser()
        verses_csv = Path(options['verses_csv']).expanduser()
        if not xml_dir.exists() or not xml_dir.is_dir():
            raise CommandError(f'Not a directory: {xml_dir}')

        xml_files = sorted(xml_dir.glob('*.xml'))
        if not xml_files:
            raise CommandError(f'No XML files found in {xml_dir}')

        def strip_tag(tag):
            return tag.split('}', 1)[-1]

        verse_rows = []
        seen_verses = set()

        words_csv.parent.mkdir(parents=True, exist_ok=True)
        verses_csv.parent.mkdir(parents=True, exist_ok=True)

        with words_csv.open('w', newline='', encoding='utf-8') as words_handle:
            word_writer = csv.writer(words_handle)
            word_writer.writerow([
                'verse_osis_id',
                'position',
                'language',
                'surface',
                'lemma',
                'morphology',
                'strongs_id',
                'source',
                'word_id',
                'part_of_speech',
                'parsing',
                'variant',
                'normalized',
            ])

            total = 0
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
                            if osis_id not in seen_verses:
                                match = VERSE_RE.match(osis_id)
                                if match:
                                    verse_rows.append([
                                        osis_id,
                                        match.group('book'),
                                        int(match.group('chapter')),
                                        int(match.group('verse')),
                                    ])
                                    seen_verses.add(osis_id)
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
                        word_writer.writerow([
                            current_osis,
                            position,
                            WordOccurrence.LANGUAGE_HEBREW,
                            surface,
                            lemma,
                            morph,
                            '',
                            'oshb',
                            word_id,
                            '',
                            '',
                            '',
                            '',
                        ])
                        total += 1
                        file_count += 1
                    if event == 'end':
                        elem.clear()

                self.stdout.write(f'{xml_file.name}: {file_count} words')

        with verses_csv.open('w', newline='', encoding='utf-8') as verses_handle:
            verse_writer = csv.writer(verses_handle)
            verse_writer.writerow(['osis_id', 'book_osis', 'chapter', 'verse'])
            verse_writer.writerows(verse_rows)

        self.stdout.write(self.style.SUCCESS(f'Exported OSHB words: {total}'))
        self.stdout.write(self.style.SUCCESS(f'Exported OSHB verses: {len(verse_rows)}'))
