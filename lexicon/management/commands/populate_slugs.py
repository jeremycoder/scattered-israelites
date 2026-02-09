"""
Populate slug fields on Book and WordOccurrence.

Book slugs use Django's slugify (e.g. "1 Samuel" → "1-samuel").
Word slugs use Hebrew→ASCII transliteration of the surface text.
Duplicates within a verse get suffixed: "et", "et-2", "et-3".

Usage:
    python manage.py populate_slugs              # full load
    python manage.py populate_slugs --dry-run     # report only
    python manage.py populate_slugs --books-only  # only Book slugs
    python manage.py populate_slugs --clear       # reset slugs first
"""

import csv
import io
import os
from collections import defaultdict

import psycopg
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from lexicon.transliterate import hebrew_to_slug


class Command(BaseCommand):
    help = 'Populate slug fields on Book and WordOccurrence.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Compute and report without writing to DB.',
        )
        parser.add_argument(
            '--books-only', action='store_true',
            help='Only populate Book slugs (fast).',
        )
        parser.add_argument(
            '--clear', action='store_true',
            help='Reset all slugs to empty string first.',
        )

    def handle(self, *args, **options):
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            raise CommandError('DATABASE_URL not set')

        self._populate_books(db_url, options)

        if not options['books_only']:
            self._populate_words(db_url, options)

    def _populate_books(self, db_url, options):
        """Populate Book.slug using Django's slugify."""
        self.stdout.write('Populating Book slugs...')

        with psycopg.connect(db_url) as conn:
            books = conn.execute('SELECT id, name FROM lexicon_book').fetchall()

        slugs = [(book_id, slugify(name)) for book_id, name in books]

        for book_id, slug in slugs:
            self.stdout.write(f'  {book_id}: {slug}')

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(
                f'Dry run: {len(slugs)} book slugs computed.'
            ))
            return

        with psycopg.connect(db_url, autocommit=True) as conn:
            conn.execute('BEGIN')
            if options['clear']:
                conn.execute("UPDATE lexicon_book SET slug = ''")
            for book_id, slug in slugs:
                conn.execute(
                    'UPDATE lexicon_book SET slug = %s WHERE id = %s',
                    (slug, book_id),
                )
            conn.commit()

        self.stdout.write(self.style.SUCCESS(
            f'Updated {len(slugs)} book slugs.'
        ))

    def _populate_words(self, db_url, options):
        """Populate WordOccurrence.slug via CSV→COPY→UPDATE."""
        self.stdout.write('Fetching word occurrences...')

        with psycopg.connect(db_url) as conn:
            rows = conn.execute(
                'SELECT id, verse_id, position, surface '
                'FROM lexicon_wordoccurrence '
                'ORDER BY verse_id, position'
            ).fetchall()

        total = len(rows)
        self.stdout.write(f'Found {total} words.')

        # Group by verse and compute slugs with deduplication
        self.stdout.write('Computing word slugs...')
        by_verse = defaultdict(list)
        for word_id, verse_id, position, surface in rows:
            by_verse[verse_id].append((word_id, position, surface))

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(['word_id', 'slug'])

        slug_count = 0
        empty_count = 0

        for verse_id, words in by_verse.items():
            seen = {}
            for word_id, position, surface in words:
                base = hebrew_to_slug(surface)
                if not base:
                    base = f'word-{position}'
                    empty_count += 1

                count = seen.get(base, 0) + 1
                seen[base] = count
                if count == 1:
                    slug = base
                else:
                    slug = f'{base}-{count}'

                writer.writerow([word_id, slug])
                slug_count += 1

        self.stdout.write(f'  Computed: {slug_count}')
        self.stdout.write(f'  Empty transliterations (fallback): {empty_count}')

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(
                f'Dry run: {slug_count} word slugs computed.'
            ))
            return

        # Bulk update via COPY into staging table
        self.stdout.write('Loading into database...')
        buf.seek(0)

        with psycopg.connect(db_url, autocommit=True) as conn:
            conn.execute('BEGIN')

            if options['clear']:
                conn.execute("UPDATE lexicon_wordoccurrence SET slug = ''")

            conn.execute(
                'CREATE TEMP TABLE slug_stage ('
                '  word_id bigint,'
                '  slug text'
                ')'
            )

            with conn.cursor() as cur:
                with cur.copy(
                    "COPY slug_stage (word_id, slug) "
                    "FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
                ) as copy:
                    copy.write(buf.getvalue().encode('utf-8'))

            updated = conn.execute(
                'UPDATE lexicon_wordoccurrence w '
                'SET slug = s.slug '
                'FROM slug_stage s '
                'WHERE w.id = s.word_id'
            ).rowcount

            conn.commit()

        self.stdout.write(self.style.SUCCESS(
            f'Done — updated {updated} word slugs.'
        ))
