import os
from pathlib import Path

import psycopg
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Fast-load OSHB words/verses via COPY into Postgres.'

    def add_arguments(self, parser):
        parser.add_argument('words_csv', type=str, help='CSV path for words')
        parser.add_argument('verses_csv', type=str, help='CSV path for verses')
        parser.add_argument(
            '--allow-nonempty',
            action='store_true',
            help='Allow import even if Verse/WordOccurrence are not empty.',
        )

    def handle(self, *args, **options):
        words_csv = Path(options['words_csv']).expanduser()
        verses_csv = Path(options['verses_csv']).expanduser()
        if not words_csv.exists():
            raise CommandError(f'Words CSV not found: {words_csv}')
        if not verses_csv.exists():
            raise CommandError(f'Verses CSV not found: {verses_csv}')

        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            raise CommandError('DATABASE_URL not set')

        with psycopg.connect(db_url, autocommit=True) as conn:
            conn.execute('BEGIN')

            if not options['allow_nonempty']:
                verse_count = conn.execute('SELECT COUNT(*) FROM lexicon_verse').fetchone()[0]
                word_count = conn.execute('SELECT COUNT(*) FROM lexicon_wordoccurrence').fetchone()[0]
                if verse_count or word_count:
                    raise CommandError(
                        'Verse or WordOccurrence not empty. Use --allow-nonempty to proceed.'
                    )

            conn.execute('TRUNCATE TABLE lexicon_wordoccurrence, lexicon_verse RESTART IDENTITY')

            conn.execute('CREATE TEMP TABLE verse_stage (osis_id text, book_osis text, chapter int, verse int)')
            conn.execute('CREATE TEMP TABLE word_stage ('
                         'verse_osis_id text, position int, language text, surface text, lemma text, '
                         'morphology text, strongs_id text, source text, word_id text, part_of_speech text, '
                         'parsing text, variant text, normalized text)')

            with conn.cursor() as cur:
                with verses_csv.open('rb') as handle:
                    with cur.copy(
                        'COPY verse_stage (osis_id, book_osis, chapter, verse) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)'
                    ) as copy:
                        while chunk := handle.read(65536):
                            copy.write(chunk)
                with words_csv.open('rb') as handle:
                    with cur.copy(
                        'COPY word_stage (verse_osis_id, position, language, surface, lemma, morphology, strongs_id, '
                        'source, word_id, part_of_speech, parsing, variant, normalized) '
                        'FROM STDIN WITH (FORMAT CSV, HEADER TRUE)'
                    ) as copy:
                        while chunk := handle.read(65536):
                            copy.write(chunk)

            conn.execute(
                'INSERT INTO lexicon_verse (book_id, chapter, verse, osis_id) '
                'SELECT b.id, v.chapter, v.verse, v.osis_id '
                'FROM verse_stage v '
                'JOIN lexicon_book b ON b.osis_id = v.book_osis'
            )

            conn.execute(
                'INSERT INTO lexicon_wordoccurrence '
                '(verse_id, position, language, surface, lemma, morphology, strongs_id, source, word_id, '
                'part_of_speech, parsing, variant, normalized) '
                'SELECT v.id, w.position, w.language, '
                'COALESCE(w.surface, \'\'), COALESCE(w.lemma, \'\'), COALESCE(w.morphology, \'\'), '
                'NULLIF(w.strongs_id, \'\'), '
                'COALESCE(w.source, \'\'), COALESCE(w.word_id, \'\'), '
                'COALESCE(w.part_of_speech, \'\'), COALESCE(w.parsing, \'\'), '
                'COALESCE(w.variant, \'\'), COALESCE(w.normalized, \'\') '
                'FROM word_stage w '
                'JOIN lexicon_verse v ON v.osis_id = w.verse_osis_id'
            )

            conn.commit()

        self.stdout.write(self.style.SUCCESS('OSHB COPY import completed'))
