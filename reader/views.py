from django.shortcuts import get_object_or_404, render

from lexicon.models import Book, HebrewMorphAnalysis, Lexeme, Verse, WordOccurrence


def book_list(request):
    ot_books = Book.objects.filter(testament='ot')
    nt_books = Book.objects.filter(testament='nt')
    return render(request, 'reader/book_list.html', {
        'ot_books': ot_books,
        'nt_books': nt_books,
    })


def chapter_list(request, osis_id):
    book = get_object_or_404(Book, osis_id=osis_id)
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
    """Shared context builder for chapter view and verse list partial."""
    verses_qs = (
        Verse.objects.filter(book=book, chapter=chapter)
        .prefetch_related('wordoccurrence_set__hebrew_analysis')
        .order_by('verse')
    )

    # Build list of verses with their words attached
    verses = []
    all_strongs = set()
    for v in verses_qs:
        words = list(v.wordoccurrence_set.all())
        for w in words:
            if w.strongs_id:
                all_strongs.add(w.strongs_id)
        verses.append(type('Verse', (), {'verse': v.verse, 'words': words, 'osis_id': v.osis_id})())

    # Single query for all glosses
    glosses = dict(
        Lexeme.objects.filter(strongs_id__in=all_strongs)
        .values_list('strongs_id', 'gloss')
    )

    # Navigation: find prev/next chapters
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


def chapter_view(request, osis_id, chapter):
    book = get_object_or_404(Book, osis_id=osis_id)
    ctx = _get_chapter_context(book, chapter)
    return render(request, 'reader/chapter_view.html', ctx)


def verse_list_partial(request, osis_id, chapter):
    book = get_object_or_404(Book, osis_id=osis_id)
    ctx = _get_chapter_context(book, chapter)
    return render(request, 'reader/partials/verse_list.html', ctx)


def word_detail_partial(request, pk):
    word = get_object_or_404(
        WordOccurrence.objects.select_related('verse', 'hebrew_analysis'),
        pk=pk,
    )
    analysis = None
    try:
        analysis = word.hebrew_analysis
    except HebrewMorphAnalysis.DoesNotExist:
        pass

    gloss = ''
    definition = ''
    if word.strongs_id:
        try:
            lex = Lexeme.objects.get(strongs_id=word.strongs_id)
            gloss = lex.gloss
            definition = lex.definition
        except Lexeme.DoesNotExist:
            pass

    return render(request, 'reader/partials/word_detail.html', {
        'word': word,
        'analysis': analysis,
        'gloss': gloss,
        'definition': definition,
    })
