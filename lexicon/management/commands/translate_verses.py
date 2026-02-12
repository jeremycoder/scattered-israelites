"""
Management command to translate Hebrew Bible verses word-by-word using Perplexity AI.

Extracts Hebrew words from the database, sends them to Perplexity for translation,
saves the JSON response files, and optionally imports them into the database.

Usage:
    python3 manage.py translate_verses exodus 10 12
    python3 manage.py translate_verses exodus 10 10 --dry-run
    python3 manage.py translate_verses exodus 10 12 --import --fix-yhwh
    python3 manage.py translate_verses exodus 10 12 --skip-existing
"""

import json
import os
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from lexicon.models import Book, Verse, WordOccurrence

# Map of language codes to language names
LANGUAGE_NAMES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'pt': 'Portuguese',
}

# Short prefix map derived from OSIS IDs (lowercase) for file naming
# This matches the existing file naming convention (gen_, exo_, etc.)
OSIS_TO_PREFIX = {
    'Gen': 'gen',
    'Exod': 'exo',
    'Lev': 'lev',
    'Num': 'num',
    'Deut': 'deut',
    'Josh': 'josh',
    'Judg': 'judg',
    'Ruth': 'ruth',
    '1Sam': '1sam',
    '2Sam': '2sam',
    '1Kgs': '1kgs',
    '2Kgs': '2kgs',
    '1Chr': '1chr',
    '2Chr': '2chr',
    'Ezra': 'ezra',
    'Neh': 'neh',
    'Esth': 'esth',
    'Job': 'job',
    'Ps': 'ps',
    'Prov': 'prov',
    'Eccl': 'eccl',
    'Song': 'song',
    'Isa': 'isa',
    'Jer': 'jer',
    'Lam': 'lam',
    'Ezek': 'ezek',
    'Dan': 'dan',
    'Hos': 'hos',
    'Joel': 'joel',
    'Amos': 'amos',
    'Obad': 'obad',
    'Jonah': 'jonah',
    'Mic': 'mic',
    'Nah': 'nah',
    'Hab': 'hab',
    'Zeph': 'zeph',
    'Hag': 'hag',
    'Zech': 'zech',
    'Mal': 'mal',
}

TRANSLATION_SCHEMA = {
    "type": "object",
    "required": ["book", "chapter", "verse", "language_code", "language_name", "words"],
    "properties": {
        "book": {"type": "string"},
        "chapter": {"type": "integer", "minimum": 1},
        "verse": {"type": "integer", "minimum": 1},
        "language_code": {"type": "string"},
        "language_name": {"type": "string"},
        "words": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["position", "surface", "phrase"],
                "properties": {
                    "position": {"type": "integer", "minimum": 1},
                    "surface": {"type": "string"},
                    "phrase": {"type": "string"},
                    "literal": {"type": "string"},
                    "source": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}


def build_prompt(book_name, chapter, verse_num, words_data, language_code, language_name):
    """Build the translation prompt for Perplexity AI."""
    words_json = json.dumps(words_data, ensure_ascii=False, indent=2)
    return (
        f"Translate the following Hebrew Bible verse ({book_name} {chapter}:{verse_num}) "
        f"word-by-word into {language_name}.\n\n"
        f"Here are the Hebrew words with their positions, surface forms, Strong's numbers, "
        f"and morphology codes:\n\n{words_json}\n\n"
        f"For each word, provide:\n"
        f"- position: the exact position number given above\n"
        f"- surface: the exact Hebrew surface form given above (copy it exactly)\n"
        f"- phrase: a contextual {language_name} translation of this word in context\n"
        f"- literal: a hyphenated morpheme-by-morpheme gloss "
        f"(e.g. 'and-he-saw', 'in-beginning-of')\n"
        f"- source: Strong's number plus brief comparison of how KJV, ESV, and NASB "
        f"render this word\n\n"
        f"Return valid JSON matching this exact schema:\n"
        f"- book: \"{book_name}\"\n"
        f"- chapter: {chapter}\n"
        f"- verse: {verse_num}\n"
        f"- language_code: \"{language_code}\"\n"
        f"- language_name: \"{language_name}\"\n"
        f"- words: array of word objects as described above\n\n"
        f"Important:\n"
        f"- Preserve the exact Hebrew surface forms\n"
        f"- Every position from the input must appear in the output\n"
        f"- Use the divine name YHWH (not 'the LORD') when translating the Tetragrammaton\n"
        f"- Be precise with morpheme glosses in the literal field"
    )


def _ssl_context():
    """Build an SSL context using certifi (macOS Python often lacks system certs)."""
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except ImportError:
        pass  # Fall back to system defaults
    return ctx


def call_perplexity(prompt, model, api_key):
    """Call the Perplexity AI chat completions API and return the parsed JSON."""
    url = 'https://api.perplexity.ai/chat/completions'
    payload = {
        'model': model,
        'messages': [
            {
                'role': 'system',
                'content': (
                    'You are a Biblical Hebrew scholar specializing in word-by-word '
                    'translation. You always return valid JSON matching the requested schema. '
                    'Never include markdown formatting or code fences in your response.'
                ),
            },
            {
                'role': 'user',
                'content': prompt,
            },
        ],
        'response_format': {
            'type': 'json_schema',
            'json_schema': {
                'name': 'verse_translation',
                'strict': True,
                'schema': TRANSLATION_SCHEMA,
            },
        },
        'temperature': 0.1,
        'max_tokens': 4096,
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
    )

    with urllib.request.urlopen(req, timeout=120, context=_ssl_context()) as resp:
        body = json.loads(resp.read().decode('utf-8'))

    content = body['choices'][0]['message']['content']
    return json.loads(content)


def fix_yhwh_in_entry(entry):
    """Replace 'the LORD' with 'YHWH' in phrase fields."""
    for word in entry.get('words', []):
        phrase = word.get('phrase', '')
        if 'the LORD' in phrase:
            word['phrase'] = phrase.replace('the LORD', 'YHWH')
        if 'the Lord' in phrase:
            word['phrase'] = word['phrase'].replace('the Lord', 'YHWH')


class Command(BaseCommand):
    help = 'Translate Hebrew Bible verses word-by-word using Perplexity AI.'

    def add_arguments(self, parser):
        parser.add_argument('book', type=str, help='Book name or slug (e.g. exodus, Exodus)')
        parser.add_argument('start_chapter', type=int, help='First chapter (inclusive)')
        parser.add_argument('end_chapter', type=int, help='Last chapter (inclusive)')
        parser.add_argument(
            '--language', type=str, default='en',
            help='Language code (default: en)',
        )
        parser.add_argument(
            '--model', type=str, default='sonar-pro',
            help='Perplexity model (default: sonar-pro)',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be sent without calling the API',
        )
        parser.add_argument(
            '--import', action='store_true', dest='do_import',
            help='Import translations into the database after saving files',
        )
        parser.add_argument(
            '--fix-yhwh', action='store_true',
            help='Replace "the LORD" with "YHWH" in phrase fields',
        )
        parser.add_argument(
            '--skip-existing', action='store_true',
            help='Skip verses that already have a JSON file in data/',
        )
        parser.add_argument(
            '--delay', type=float, default=1.0,
            help='Delay in seconds between API requests (default: 1.0)',
        )

    def handle(self, *args, **options):
        book_input = options['book']
        start_ch = options['start_chapter']
        end_ch = options['end_chapter']
        language = options['language']
        model = options['model']
        dry_run = options['dry_run']
        do_import = options['do_import']
        do_fix_yhwh = options['fix_yhwh']
        skip_existing = options['skip_existing']
        delay = options['delay']

        # Resolve book
        book = self._resolve_book(book_input)
        file_prefix = OSIS_TO_PREFIX.get(book.osis_id, book.slug)
        language_name = LANGUAGE_NAMES.get(language, language.title())

        # Validate chapter range
        if start_ch > end_ch:
            raise CommandError(f'start_chapter ({start_ch}) must be <= end_chapter ({end_ch})')

        # Get API key (not needed for dry run)
        api_key = None
        if not dry_run:
            api_key = os.environ.get('PERPLEXITY_API_KEY', '')
            if not api_key:
                raise CommandError(
                    'PERPLEXITY_API_KEY environment variable is not set. '
                    'Add it to your .env file or export it.'
                )

        # Data directory
        data_dir = Path(settings.BASE_DIR) / 'data'
        data_dir.mkdir(exist_ok=True)

        # Gather all verses in range
        verses = (
            Verse.objects
            .filter(book=book, chapter__gte=start_ch, chapter__lte=end_ch)
            .order_by('chapter', 'verse')
        )

        if not verses.exists():
            raise CommandError(
                f'No verses found for {book.name} chapters {start_ch}-{end_ch}'
            )

        total_verses = verses.count()
        self.stdout.write(
            f'Found {total_verses} verses in {book.name} '
            f'chapters {start_ch}-{end_ch}'
        )

        translated = 0
        skipped = 0
        errors = 0
        saved_files = []

        for verse in verses:
            file_path = data_dir / f'{file_prefix}_{verse.chapter}_{verse.verse}_{language}.json'

            # Skip existing
            if skip_existing and file_path.exists():
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(f'  Skipping {book.name} {verse.chapter}:{verse.verse} '
                                       f'(file exists)')
                )
                continue

            # Extract Hebrew words
            words = (
                WordOccurrence.objects
                .filter(verse=verse)
                .order_by('position')
            )

            if not words.exists():
                self.stderr.write(self.style.WARNING(
                    f'  No words found for {book.name} {verse.chapter}:{verse.verse}, skipping'
                ))
                skipped += 1
                continue

            word_list = [
                {
                    'position': w.position,
                    'surface': w.surface,
                    'strongs': w.strongs_id or '',
                    'morph': w.morphology or '',
                }
                for w in words
            ]

            # Build prompt
            prompt = build_prompt(
                book.name, verse.chapter, verse.verse,
                word_list, language, language_name,
            )

            if dry_run:
                self.stdout.write(self.style.SUCCESS(
                    f'\n--- {book.name} {verse.chapter}:{verse.verse} ---'
                ))
                self.stdout.write(f'Words: {len(word_list)}')
                self.stdout.write(f'File: {file_path}')
                self.stdout.write(f'Prompt ({len(prompt)} chars):\n{prompt[:500]}...\n')
                translated += 1
                continue

            # Call Perplexity API
            self.stdout.write(
                f'  Translating {book.name} {verse.chapter}:{verse.verse} '
                f'({len(word_list)} words)...',
                ending='',
            )

            try:
                result = call_perplexity(prompt, model, api_key)
            except urllib.error.HTTPError as e:
                error_body = ''
                try:
                    error_body = e.read().decode('utf-8')
                except Exception:
                    pass
                self.stderr.write(self.style.ERROR(
                    f' API error {e.code}: {error_body[:200]}'
                ))
                errors += 1
                continue
            except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
                self.stderr.write(self.style.ERROR(f' Error: {e}'))
                errors += 1
                continue

            # Apply YHWH fix
            if do_fix_yhwh:
                fix_yhwh_in_entry(result)

            # Save as array (matching existing format)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump([result], f, ensure_ascii=False, indent=2)
                f.write('\n')

            saved_files.append(str(file_path))
            translated += 1
            self.stdout.write(self.style.SUCCESS(' saved'))

            # Rate limit delay
            if delay > 0:
                time.sleep(delay)

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Translated: {translated}, Skipped: {skipped}, Errors: {errors}'
        ))

        if saved_files:
            self.stdout.write(f'Saved {len(saved_files)} files to {data_dir}/')

        # Optional import
        if do_import and saved_files:
            self.stdout.write(self.style.NOTICE('\nImporting translations into database...'))
            for fp in saved_files:
                try:
                    call_command(
                        'import_translations', fp,
                        model=model,
                        prompt=f'Perplexity AI ({model}) word-by-word translation',
                    )
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'  Import error for {fp}: {e}'))

            self.stdout.write(self.style.SUCCESS('Import complete.'))

    def _resolve_book(self, book_input):
        """Look up a Book by slug, name, or OSIS ID (case-insensitive)."""
        normalized = book_input.lower().strip()
        try:
            return Book.objects.get(
                Q(slug=normalized) | Q(name__iexact=normalized) | Q(osis_id__iexact=normalized)
            )
        except Book.DoesNotExist:
            raise CommandError(
                f'Book not found: "{book_input}". Use a slug (e.g. exodus), '
                f'name (e.g. Exodus), or OSIS ID (e.g. Exod).'
            )
        except Book.MultipleObjectsReturned:
            raise CommandError(
                f'Multiple books matched "{book_input}". Please be more specific.'
            )
