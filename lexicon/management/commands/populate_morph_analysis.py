"""
Bulk-load HebrewMorphAnalysis rows from WordOccurrence morph codes.

Strategy: parse all morph codes in Python, write CSV to StringIO,
COPY into a temp staging table, then INSERT...SELECT into the real table.

Usage:
    python manage.py populate_morph_analysis          # full load
    python manage.py populate_morph_analysis --clear   # truncate first
    python manage.py populate_morph_analysis --dry-run  # parse only, no DB writes
"""

import csv
import io
import os
from collections import Counter

import psycopg
from django.core.management.base import BaseCommand, CommandError

from lexicon.morph_parser import parse_morph


# Column order in the staging CSV / table
CSV_COLUMNS = [
    'word_id',
    'part_of_speech',
    'subtype',
    'binyan',
    'conjugation',
    'person',
    'gender',
    'number_field',
    'state',
    'aspect',
    'voice',
    'mood',
    'polarity',
    'negation_particle',
    'definiteness',
    'suffix_person',
    'suffix_gender',
    'suffix_number',
    'raw_morph_code',
]


class Command(BaseCommand):
    help = 'Parse OSHB morph codes and bulk-load HebrewMorphAnalysis rows.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Truncate lexicon_hebrewmorphanalysis before loading.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse and report only — no database writes.',
        )

    def handle(self, *args, **options):
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            raise CommandError('DATABASE_URL not set')

        # 1. Fetch all word IDs + morph codes
        self.stdout.write('Fetching word occurrences...')
        with psycopg.connect(db_url) as conn:
            rows = conn.execute(
                "SELECT id, morphology FROM lexicon_wordoccurrence "
                "WHERE source = 'oshb' AND morphology != ''"
            ).fetchall()

        total = len(rows)
        self.stdout.write(f'Found {total} words with morph codes.')

        # 2. Parse each code
        self.stdout.write('Parsing morph codes...')
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(CSV_COLUMNS)

        error_counter = Counter()
        error_count = 0
        parsed_count = 0

        for word_id, morph_code in rows:
            result = parse_morph(morph_code)
            parsed_count += 1

            if result.parse_errors:
                error_count += 1
                for err in result.parse_errors:
                    error_counter[err] += 1

            writer.writerow([
                str(word_id),
                result.part_of_speech,
                result.subtype or '',
                result.binyan or '',
                result.conjugation or '',
                str(result.person) if result.person is not None else '',
                result.gender or '',
                result.number or '',
                result.state or '',
                result.aspect or '',
                result.voice or '',
                result.mood or '',
                result.polarity or '',
                result.negation_particle or '',
                result.definiteness or '',
                str(result.suffix_person) if result.suffix_person is not None else '',
                result.suffix_gender or '',
                result.suffix_number or '',
                morph_code,
            ])

        self.stdout.write(f'Parsed {parsed_count} codes, {error_count} with errors '
                          f'({error_count / max(total, 1) * 100:.2f}%).')

        if error_counter:
            self.stdout.write('Top parse errors:')
            for msg, count in error_counter.most_common(20):
                self.stdout.write(f'  {count:>5}  {msg}')

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS('Dry run complete — no DB writes.'))
            return

        # 3. COPY into staging table, then INSERT into real table
        self.stdout.write('Loading into database...')
        buf.seek(0)

        with psycopg.connect(db_url, autocommit=True) as conn:
            conn.execute('BEGIN')

            if options['clear']:
                conn.execute('TRUNCATE TABLE lexicon_hebrewmorphanalysis RESTART IDENTITY')
                self.stdout.write('Truncated lexicon_hebrewmorphanalysis.')

            conn.execute(
                'CREATE TEMP TABLE morph_stage ('
                '  word_id bigint,'
                '  part_of_speech text,'
                '  subtype text,'
                '  binyan text,'
                '  conjugation text,'
                '  person text,'
                '  gender text,'
                '  number_field text,'
                '  state text,'
                '  aspect text,'
                '  voice text,'
                '  mood text,'
                '  polarity text,'
                '  negation_particle text,'
                '  definiteness text,'
                '  suffix_person text,'
                '  suffix_gender text,'
                '  suffix_number text,'
                '  raw_morph_code text'
                ')'
            )

            with conn.cursor() as cur:
                with cur.copy(
                    'COPY morph_stage ('
                    '  word_id, part_of_speech, subtype, binyan, conjugation,'
                    '  person, gender, number_field, state, aspect, voice, mood,'
                    '  polarity, negation_particle, definiteness,'
                    '  suffix_person, suffix_gender, suffix_number, raw_morph_code'
                    ') FROM STDIN WITH (FORMAT CSV, HEADER TRUE)'
                ) as copy:
                    data = buf.getvalue().encode('utf-8')
                    copy.write(data)

            inserted = conn.execute(
                "INSERT INTO lexicon_hebrewmorphanalysis ("
                "  word_id, part_of_speech, subtype, binyan, conjugation,"
                "  person, gender, number, state, aspect, voice, mood,"
                "  polarity, negation_particle, definiteness,"
                "  suffix_person, suffix_gender, suffix_number, raw_morph_code"
                ") "
                "SELECT "
                "  s.word_id,"
                "  s.part_of_speech,"
                "  NULLIF(s.subtype, ''),"
                "  NULLIF(s.binyan, ''),"
                "  NULLIF(s.conjugation, ''),"
                "  CASE WHEN s.person = '' THEN NULL ELSE s.person::smallint END,"
                "  NULLIF(s.gender, ''),"
                "  NULLIF(s.number_field, ''),"
                "  NULLIF(s.state, ''),"
                "  NULLIF(s.aspect, ''),"
                "  NULLIF(s.voice, ''),"
                "  NULLIF(s.mood, ''),"
                "  NULLIF(s.polarity, ''),"
                "  NULLIF(s.negation_particle, ''),"
                "  NULLIF(s.definiteness, ''),"
                "  CASE WHEN s.suffix_person = '' THEN NULL ELSE s.suffix_person::smallint END,"
                "  NULLIF(s.suffix_gender, ''),"
                "  NULLIF(s.suffix_number, ''),"
                "  NULLIF(s.raw_morph_code, '')"
                " FROM morph_stage s"
            ).rowcount

            conn.commit()

        self.stdout.write(self.style.SUCCESS(
            f'Done — inserted {inserted} HebrewMorphAnalysis rows.'
        ))
