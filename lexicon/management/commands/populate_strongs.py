"""
Populate WordOccurrence.strongs_id by extracting Strong's numbers from the lemma field.

The OSHB lemma field encodes Strong's numbers with optional prefix morphemes:
  - Plain number:    '430'       → H430
  - With suffix:     '1254 a'    → H1254
  - With prefix:     'b/7225'    → H7225
  - Multi-prefix:    'c/d/776'   → H776
  - Number+:         '1008+'     → H1008
  - Bare prefix:     'l', 'b'    → None (no Strong's number)

The extracted number is prefixed with 'H' to match the Lexeme.strongs_id format.

Usage:
    python manage.py populate_strongs              # full update
    python manage.py populate_strongs --dry-run     # report only, no DB writes
    python manage.py populate_strongs --clear       # set all strongs_id to NULL first
"""

import csv
import io
import os
import re

import psycopg
from django.core.management.base import BaseCommand, CommandError


def extract_strongs(lemma: str) -> str | None:
    """Extract a Strong's ID (e.g. 'H7225') from an OSHB lemma value.

    Returns None for bare-prefix morphemes like 'l', 'b', 'm' that have
    no Strong's number.
    """
    # Take the last segment after splitting on '/' (strips prefix morphemes)
    number_part = lemma.split('/')[-1].strip()
    # Must contain at least one digit
    match = re.match(r'(\d+)', number_part)
    if not match:
        return None
    return 'H' + match.group(1)


class Command(BaseCommand):
    help = "Extract Strong's IDs from the lemma field and populate strongs_id."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report extraction results without writing to the database.',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Set all strongs_id to NULL before populating.',
        )

    def handle(self, *args, **options):
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            raise CommandError('DATABASE_URL not set')

        # 1. Fetch all word IDs + lemma values
        self.stdout.write('Fetching word occurrences...')
        with psycopg.connect(db_url) as conn:
            rows = conn.execute(
                "SELECT id, lemma FROM lexicon_wordoccurrence"
            ).fetchall()

        # Load valid Lexeme strongs_ids for validation
        with psycopg.connect(db_url) as conn:
            lex_ids = set(
                r[0] for r in conn.execute(
                    "SELECT strongs_id FROM lexicon_lexeme"
                ).fetchall()
            )

        total = len(rows)
        self.stdout.write(f'Found {total} word occurrences.')

        # 2. Extract Strong's IDs
        self.stdout.write('Extracting Strong\'s numbers from lemma field...')
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(['word_id', 'strongs_id'])

        matched = 0
        no_number = 0
        no_lexeme = 0

        for word_id, lemma in rows:
            sid = extract_strongs(lemma)
            if sid is None:
                no_number += 1
                continue
            if sid not in lex_ids:
                no_lexeme += 1
                continue
            matched += 1
            writer.writerow([word_id, sid])

        self.stdout.write(f'  Matched to Lexeme:   {matched:>7}')
        self.stdout.write(f'  No Strong\'s number:  {no_number:>7}  (bare prefixes like l, b, m)')
        self.stdout.write(f'  No matching Lexeme:  {no_lexeme:>7}')
        self.stdout.write(f'  Total:               {total:>7}')

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS('Dry run complete — no DB writes.'))
            return

        # 3. Bulk update via COPY into staging table + UPDATE join
        self.stdout.write('Loading into database...')
        buf.seek(0)

        with psycopg.connect(db_url, autocommit=True) as conn:
            conn.execute('BEGIN')

            if options['clear']:
                conn.execute('UPDATE lexicon_wordoccurrence SET strongs_id = NULL')
                self.stdout.write('Cleared all strongs_id values.')

            conn.execute(
                'CREATE TEMP TABLE strongs_stage ('
                '  word_id bigint,'
                '  strongs_id text'
                ')'
            )

            with conn.cursor() as cur:
                with cur.copy(
                    "COPY strongs_stage (word_id, strongs_id) "
                    "FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
                ) as copy:
                    copy.write(buf.getvalue().encode('utf-8'))

            updated = conn.execute(
                "UPDATE lexicon_wordoccurrence w "
                "SET strongs_id = s.strongs_id "
                "FROM strongs_stage s "
                "WHERE w.id = s.word_id"
            ).rowcount

            conn.commit()

        self.stdout.write(self.style.SUCCESS(
            f'Done — updated {updated} rows with strongs_id.'
        ))
