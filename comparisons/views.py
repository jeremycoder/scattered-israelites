from collections import OrderedDict

from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render
from django.utils.text import slugify

from .models import LexicalComparison


def comparison_list(request):
    qs = (
        LexicalComparison.objects
        .filter(status=LexicalComparison.STATUS_ACCEPTED, is_removed=False)
        .select_related('language')
        .order_by('hebrew_word', 'language__name')
    )

    # Group by hebrew_word into unique entries
    grouped = OrderedDict()
    for comp in qs:
        key = comp.hebrew_word
        if key not in grouped:
            grouped[key] = {
                'hebrew_word': comp.hebrew_word,
                'hebrew_transliteration': comp.hebrew_transliteration,
                'hebrew_meaning': comp.hebrew_meaning,
                'slug': slugify(comp.hebrew_transliteration),
                'languages': [],
            }
        lang_name = comp.language.name
        if lang_name not in grouped[key]['languages']:
            grouped[key]['languages'].append(lang_name)

    entries = list(grouped.values())
    paginator = Paginator(entries, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'comparisons/comparison_list.html', {'page': page})


def comparison_detail(request, slug):
    qs = (
        LexicalComparison.objects
        .filter(
            status=LexicalComparison.STATUS_ACCEPTED,
            is_removed=False,
        )
        .select_related('language', 'lexeme')
        .order_by('language__name')
    )

    # Find comparisons whose transliteration slugifies to the given slug
    matches = [c for c in qs if slugify(c.hebrew_transliteration) == slug]
    if not matches:
        raise Http404

    first = matches[0]
    definition = (first.lexeme.gloss or first.lexeme.definition) if first.lexeme else ''
    context = {
        'hebrew_word': first.hebrew_word,
        'hebrew_transliteration': first.hebrew_transliteration,
        'hebrew_meaning': first.hebrew_meaning,
        'definition': definition,
        'comparisons': matches,
    }
    return render(request, 'comparisons/comparison_detail.html', context)
