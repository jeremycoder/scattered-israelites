from django.shortcuts import get_object_or_404, render

from lexicon.models import Book, HebrewMorphAnalysis, Lexeme, Verse, WordOccurrence

# Torah / Nevi'im / Ketuvim grouping by OSIS ID
TORAH_IDS = {'Gen', 'Exod', 'Lev', 'Num', 'Deut'}
NEVIIM_IDS = {
    'Josh', 'Judg', '1Sam', '2Sam', '1Kgs', '2Kgs',   # Former Prophets
    'Isa', 'Jer', 'Ezek',                                # Major Prophets
    'Hos', 'Joel', 'Amos', 'Obad', 'Jonah', 'Mic',      # Twelve
    'Nah', 'Hab', 'Zeph', 'Hag', 'Zech', 'Mal',
}
KETUVIM_IDS = {
    'Ps', 'Prov', 'Job',
    'Song', 'Ruth', 'Lam', 'Eccl', 'Esth',
    'Dan', 'Ezra', 'Neh', '1Chr', '2Chr',
}


def book_list(request):
    ot_books = Book.objects.filter(testament='ot')
    torah_books = [b for b in ot_books if b.osis_id in TORAH_IDS]
    neviim_books = [b for b in ot_books if b.osis_id in NEVIIM_IDS]
    ketuvim_books = [b for b in ot_books if b.osis_id in KETUVIM_IDS]
    nt_books = Book.objects.filter(testament='nt')
    return render(request, 'reader/book_list.html', {
        'torah_books': torah_books,
        'neviim_books': neviim_books,
        'ketuvim_books': ketuvim_books,
        'nt_books': nt_books,
    })


def chapter_list(request, book_slug):
    book = get_object_or_404(Book, slug=book_slug)
    chapters = (
        Verse.objects.filter(book=book)
        .values_list('chapter', flat=True)
        .distinct()
        .order_by('chapter')
    )
    return render(request, 'reader/chapter_list.html', {
        'book': book,
        'chapters': list(chapters),
    })


def _get_chapter_context(book, chapter):
    """Shared context builder for chapter view."""
    verses_qs = (
        Verse.objects.filter(book=book, chapter=chapter)
        .prefetch_related('wordoccurrence_set__hebrew_analysis')
        .order_by('verse')
    )

    verses = []
    all_strongs = set()
    for v in verses_qs:
        words = list(v.wordoccurrence_set.all())
        for w in words:
            if w.strongs_id:
                all_strongs.add(w.strongs_id)
        verses.append(type('Verse', (), {
            'verse': v.verse, 'words': words, 'osis_id': v.osis_id,
        })())

    glosses = dict(
        Lexeme.objects.filter(strongs_id__in=all_strongs)
        .values_list('strongs_id', 'gloss')
    )

    all_chapters = list(
        Verse.objects.filter(book=book)
        .values_list('chapter', flat=True)
        .distinct()
        .order_by('chapter')
    )
    idx = all_chapters.index(chapter) if chapter in all_chapters else -1
    prev_chapter = all_chapters[idx - 1] if idx > 0 else None
    next_chapter = all_chapters[idx + 1] if idx < len(all_chapters) - 1 else None

    return {
        'book': book,
        'chapter': chapter,
        'verses': verses,
        'glosses': glosses,
        'prev_chapter': prev_chapter,
        'next_chapter': next_chapter,
    }


def chapter_view(request, book_slug, chapter):
    book = get_object_or_404(Book, slug=book_slug)
    ctx = _get_chapter_context(book, chapter)
    return render(request, 'reader/chapter_view.html', ctx)


def verse_view(request, book_slug, chapter, verse_num):
    book = get_object_or_404(Book, slug=book_slug)
    verse = get_object_or_404(Verse, book=book, chapter=chapter, verse=verse_num)
    words = list(
        WordOccurrence.objects
        .filter(verse=verse)
        .select_related('hebrew_analysis')
        .order_by('position')
    )

    strongs_ids = [w.strongs_id for w in words if w.strongs_id]
    glosses = dict(
        Lexeme.objects.filter(strongs_id__in=strongs_ids)
        .values_list('strongs_id', 'gloss')
    )

    all_verses = list(
        Verse.objects.filter(book=book, chapter=chapter)
        .values_list('verse', flat=True)
        .order_by('verse')
    )
    idx = all_verses.index(verse_num) if verse_num in all_verses else -1
    prev_verse = all_verses[idx - 1] if idx > 0 else None
    next_verse = all_verses[idx + 1] if idx < len(all_verses) - 1 else None

    gloss_preview = [glosses.get(w.strongs_id, '').split(';')[0].strip()
                     for w in words if w.strongs_id and glosses.get(w.strongs_id)]
    meta_description = (
        f'{book.name} {chapter}:{verse_num} — Hebrew interlinear with '
        f'morphology and glosses. {", ".join(gloss_preview[:6])}'
    )

    return render(request, 'reader/verse_view.html', {
        'book': book,
        'chapter': chapter,
        'verse_num': verse_num,
        'verse': verse,
        'words': words,
        'glosses': glosses,
        'prev_verse': prev_verse,
        'next_verse': next_verse,
        'meta_description': meta_description[:200],
    })


def word_view(request, book_slug, chapter, verse_num, word_slug):
    book = get_object_or_404(Book, slug=book_slug)
    verse = get_object_or_404(Verse, book=book, chapter=chapter, verse=verse_num)
    word = get_object_or_404(
        WordOccurrence.objects.select_related(
            'hebrew_analysis',
            'hebrew_translation',
            'hebrew_lexical',
        ),
        verse=verse,
        slug=word_slug,
    )

    analysis = None
    try:
        analysis = word.hebrew_analysis
    except HebrewMorphAnalysis.DoesNotExist:
        pass

    translation = getattr(word, 'hebrew_translation', None)
    lexical_info = getattr(word, 'hebrew_lexical', None)

    gloss = ''
    definition = ''
    transliteration = ''
    lexeme = None
    if word.strongs_id:
        try:
            lexeme = Lexeme.objects.get(strongs_id=word.strongs_id)
            gloss = lexeme.gloss
            definition = lexeme.definition
            transliteration = lexeme.transliteration
        except Lexeme.DoesNotExist:
            pass

    # All words in this verse for context display
    verse_words = list(
        WordOccurrence.objects.filter(verse=verse).order_by('position')
    )
    strongs_ids = [w.strongs_id for w in verse_words if w.strongs_id]
    glosses = dict(
        Lexeme.objects.filter(strongs_id__in=strongs_ids)
        .values_list('strongs_id', 'gloss')
    )

    # Morphemes (if populated)
    morphemes = list(word.hebrew_morphemes.all().order_by('slot_order'))

    # SEO
    meta_title = f'{word.surface} — {book.name} {chapter}:{verse_num} Hebrew Word Study'
    short_gloss = gloss.split(';')[0].strip() if gloss else ''
    meta_description = (
        f'{word.surface}'
        + (f' ({transliteration})' if transliteration else '')
        + (f' — {short_gloss}' if short_gloss else '')
        + f'. {book.name} {chapter}:{verse_num} word #{word.position}.'
        + (f' {analysis.part_of_speech}' if analysis else '')
        + (f', {analysis.binyan}' if analysis and analysis.binyan else '')
        + '.'
    )

    return render(request, 'reader/word_view.html', {
        'book': book,
        'chapter': chapter,
        'verse_num': verse_num,
        'word': word,
        'analysis': analysis,
        'translation': translation,
        'lexical_info': lexical_info,
        'gloss': gloss,
        'definition': definition,
        'transliteration': transliteration,
        'lexeme': lexeme,
        'morphemes': morphemes,
        'verse_words': verse_words,
        'glosses': glosses,
        'meta_title': meta_title,
        'meta_description': meta_description[:200],
    })
