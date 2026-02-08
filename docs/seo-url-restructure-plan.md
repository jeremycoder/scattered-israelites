# SEO-Friendly URL Restructure: Verse & Word Pages

## Context

The Scattered Israelites Bible reader currently uses OSIS abbreviations in URLs (`/bible/Gen/1/`) and only has chapter-level pages. The goal is to make the site search-engine-friendly by:
1. Using full, hyphenated book names in URLs (`/bible/genesis/1/`)
2. Adding individual **verse pages** (~23,000 pages) at `/bible/genesis/1/1/`
3. Adding individual **word pages** (~306,785 pages) at `/bible/genesis/1/1/bereshit/`
4. Enriching word pages with morphology, transliteration, lexicon data, and verse context

**Key data constraint:** All 306,785 `WordOccurrence` rows have `strongs_id=NULL`, so Lexeme transliteration can't be used. A custom Hebrew→ASCII transliteration function is required.

**Prerequisite:** Populate `strongs_id` on all WordOccurrence rows before starting this work. The `lemma` field contains embedded Strong's numbers (e.g. "b/7225", "1254 a") that need to be extracted and mapped.

## Files to Create

| File | Purpose |
|------|---------|
| `lexicon/transliterate.py` | Pure-Python Hebrew→ASCII transliteration (no Django imports) |
| `lexicon/tests/test_transliterate.py` | Unit tests for transliteration |
| `lexicon/management/commands/populate_slugs.py` | Bulk-compute slugs for 66 books + 306K words |
| `templates/reader/verse_view.html` | Full-page verse detail with word links |
| `templates/reader/word_view.html` | Full-page word study with morphology, context, lexicon |

## Files to Modify

| File | Changes |
|------|---------|
| `lexicon/models.py` | Add `slug` field to `Book` (SlugField, unique) and `WordOccurrence` (CharField + unique constraint per verse) |
| `reader/urls.py` | New patterns using `<slug:book_slug>`, add verse/word routes |
| `reader/views.py` | Update lookups from `osis_id` → `slug`; add `verse_view`, `word_view` |
| `templates/base.html` | Add `{% block meta %}` for SEO tags |
| `templates/reader/book_list.html` | Links use `book.slug` |
| `templates/reader/chapter_list.html` | Links use `book.slug` |
| `templates/reader/chapter_view.html` | Links use `book.slug`; verse numbers link to verse pages |
| `templates/reader/partials/verse_list.html` | Verse numbers link to verse pages; words show slug for linking |
| `templates/reader/partials/word_detail.html` | Add "View full page →" link to word page |

## URL Structure (New)

### Frontend (`/bible/` prefix from `config/urls.py`)
| URL | View | Example |
|-----|------|---------|
| `/bible/` | `book_list` | Book grid |
| `/bible/<book_slug>/` | `chapter_list` | `/bible/genesis/` `/bible/1-samuel/` |
| `/bible/<book_slug>/<ch>/` | `chapter_view` | `/bible/genesis/1/` |
| `/bible/<book_slug>/<ch>/<vs>/` | `verse_view` | `/bible/genesis/1/1/` |
| `/bible/<book_slug>/<ch>/<vs>/<word_slug>/` | `word_view` | `/bible/genesis/1/1/bereshit/` |
| `/bible/htmx/word/<pk>/` | `word_detail_partial` | HTMX slide-in panel |
| `/bible/htmx/<book_slug>/<ch>/` | `verse_list_partial` | HTMX chapter swap |

### API (unchanged — keeps `osis_id`)
No changes to API URLs.

## Hebrew Transliteration (`lexicon/transliterate.py`)

Pure-Python module (same pattern as `morph_parser.py`). Two functions:

- `transliterate_hebrew(text: str) -> str` — converts pointed Hebrew to Latin
- `hebrew_to_slug(text: str) -> str` — calls transliterate, then lowercases + strips to `[a-z0-9-]`

**Algorithm:**
1. Strip morpheme separators (`/`)
2. Strip cantillation marks (U+0591–U+05AF)
3. Process character by character: buffer each consonant, check lookahead for dagesh (U+05BC) and shin/sin dots (U+05C1/U+05C2)
4. Map consonants: `א→(empty)` `בּ→b` `ב→v` `ג→g` `ד→d` `ה→h` `ו→v` `ז→z` `ח→ch` `ט→t` `י→y` `כּ→k` `כ/ך→kh` `ל→l` `מ/ם→m` `נ/ן→n` `ס→s` `ע→(empty)` `פּ→p` `פ/ף→f` `צ/ץ→ts` `ק→q` `ר→r` `שׁ→sh` `שׂ→s` `ש→sh` `ת→t`
5. Map vowels: `sheva→e` `hataf-segol→e` `hataf-patah→a` `hataf-qamats→o` `hiriq→i` `tsere→e` `segol→e` `patah→a` `qamats→a` `holam→o` `qubuts→u`
6. Post-process: lowercase, collapse hyphens, strip non-alphanumeric except hyphens

**Expected output:** `בְּ/רֵאשִׁ֖ית` → `bereshit`, `בָּרָ֣א` → `bara`, `אֱלֹהִ֑ים` → `elohim`, `הַ/שָּׁמַ֖יִם` → `hashamayim`

## Model Changes

### Book — add `slug`
```python
slug = models.SlugField(max_length=64, unique=True, blank=True)
```
Populated via `django.utils.text.slugify(book.name)`: "Genesis"→`genesis`, "1 Samuel"→`1-samuel`, "Song of Songs"→`song-of-songs`

### WordOccurrence — add `slug`
```python
slug = models.CharField(max_length=128, blank=True)

class Meta:
    constraints = [
        models.UniqueConstraint(fields=['verse', 'slug'], name='unique_word_slug_per_verse'),
    ]
```
Populated via `hebrew_to_slug(word.surface)`. Duplicates within a verse get suffix: `et`, `et-2`, `et-3`.
Fallback: `word-{position}` if transliteration produces empty string.

### Migration strategy
1. Migration: add both slug fields (blank=True, no constraints yet)
2. Run `python3 manage.py populate_slugs`
3. Migration: add unique constraint on Book.slug + UniqueConstraint on (verse, slug)

## Management Command (`populate_slugs`)

**Book slugs** (66 rows): Django ORM, `slugify(book.name)`

**Word slugs** (306K rows): Batch approach using proven CSV → COPY pattern:
1. Fetch all `(id, verse_id, position, surface)` via raw psycopg
2. Group by verse_id, for each verse compute slugs with deduplication (suffix `-2`, `-3` for collisions)
3. Fallback to `word-{position}` if transliteration produces empty string
4. COPY slug updates into temp staging table, UPDATE join back

Options: `--dry-run`, `--clear`, `--books-only`

## New Views

### `verse_view(request, book_slug, chapter, verse_num)`
- Lookup: `Book` by slug, `Verse` by (book, chapter, verse)
- Fetch words with `select_related('hebrew_analysis')`
- Build gloss map (single Lexeme query)
- Prev/next verse navigation
- SEO: `<title>Genesis 1:1 — Scattered Israelites Bible</title>`, `<meta name="description" ...>`

### `word_view(request, book_slug, chapter, verse_num, word_slug)`
- Lookup: Book by slug → Verse → WordOccurrence by (verse, slug)
- Fetch: analysis, lexeme (via strongs_id), morphemes
- Fetch verse words for context display (highlight current word)
- SEO: `<title>בְּרֵאשִׁית (bereshit) — Genesis 1:1 Word Study</title>`

### Word page content sections:
1. Large Hebrew surface + transliteration + gloss
2. Verse in context (all words shown, current highlighted)
3. Morphology table (POS, binyan, conjugation, person, gender, number, state...)
4. Lexicon entry (Strong's, lemma, transliteration, gloss, definition)
5. Word construction / morphemes (if populated in `HebrewMorpheme` table)

## Implementation Order

1. **Transliteration module** — `lexicon/transliterate.py` + tests → run tests
2. **Model changes** — add slug fields → `makemigrations` → `migrate`
3. **Slug population** — `populate_slugs` command → run it
4. **Enforce constraints** — add unique constraints → `makemigrations` → `migrate`
5. **Update existing views/URLs** — switch from `osis_id` to `book_slug`
6. **New views** — `verse_view`, `word_view`
7. **New templates** — `verse_view.html`, `word_view.html`
8. **Update existing templates** — use `book.slug`, add verse/word links, SEO meta
9. **Update word_detail_partial** — add "View full page →" link

## Verification

1. `python3 manage.py test lexicon.tests.test_transliterate` — all transliteration tests pass
2. `python3 manage.py populate_slugs` — completes without errors
3. `python3 manage.py check` — no issues
4. `python3 manage.py runserver 8100` then:
   - `/bible/` — book grid, links use full names
   - `/bible/genesis/` — chapter list
   - `/bible/genesis/1/` — interlinear chapter view, HTMX panel still works
   - `/bible/genesis/1/1/` — verse page with word links
   - `/bible/genesis/1/1/bereshit/` — word page with morphology, context, lexicon
   - `/bible/1-samuel/` — multi-word book name works
   - `/bible/song-of-songs/` — hyphenated slug works
5. View page source — verify `<title>` and `<meta name="description">` present on verse/word pages
