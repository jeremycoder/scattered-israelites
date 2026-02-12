from collections import OrderedDict
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from lexicon.models import Lexeme

from .forms import LexicalComparisonForm
from .models import ComparisonRevision, ContributorProfile, LexicalComparison


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


@login_required
def add_comparison(request):
    # Check contributor profile
    try:
        request.user.contributor_profile
    except ContributorProfile.DoesNotExist:
        return render(request, 'comparisons/add_comparison.html', {
            'no_profile': True,
        })

    # Build the redirect URL for after save (back to word page)
    back_url = request.GET.get('back', '')

    # Pre-fill Hebrew fields from GET params
    lexeme_id = request.GET.get('lexeme_id', '')
    lexeme = None
    if lexeme_id:
        lexeme = Lexeme.objects.filter(strongs_id=lexeme_id).first()

    initial = {
        'lexeme': lexeme.pk if lexeme else '',
        'hebrew_word': request.GET.get('hebrew_word', ''),
        'hebrew_transliteration': request.GET.get('hebrew_transliteration', ''),
        'hebrew_root': request.GET.get('hebrew_root', ''),
        'hebrew_meaning': request.GET.get('hebrew_meaning', ''),
    }

    if request.method == 'POST':
        form = LexicalComparisonForm(request.POST)
        if form.is_valid():
            comparison = form.save(commit=False)
            comparison.status = LexicalComparison.STATUS_PENDING
            comparison.created_by = request.user
            comparison.save()

            # Create initial revision
            ComparisonRevision.objects.create(
                comparison=comparison,
                revision_number=1,
                edited_by=request.user,
                data={
                    'hebrew_word': comparison.hebrew_word,
                    'nc_word': comparison.nc_word,
                    'nc_meaning': comparison.nc_meaning,
                    'language': str(comparison.language),
                    'category': comparison.category,
                },
                change_summary='Initial submission',
            )

            messages.success(
                request,
                f'Your comparison "{comparison}" has been submitted for review.'
            )
            if back_url:
                return redirect(back_url)
            return redirect('comparison-list')
    else:
        form = LexicalComparisonForm(initial=initial)

    context = {
        'form': form,
        'hebrew_word_display': initial['hebrew_word'],
        'hebrew_transliteration_display': initial['hebrew_transliteration'],
        'hebrew_meaning_display': initial['hebrew_meaning'],
        'back_url': back_url,
    }
    return render(request, 'comparisons/add_comparison.html', context)
