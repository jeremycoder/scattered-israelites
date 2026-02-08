import csv

from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from lexicon.models import (
    Book,
    HebrewMorphAnalysis,
    Lexeme,
    Verse,
    WordOccurrence,
)

from .serializers import (
    BookSerializer,
    ChapterVerseSerializer,
    LexemeSerializer,
    WordDetailSerializer,
)


class LexemeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Lexeme.objects.all()
    serializer_class = LexemeSerializer
    lookup_field = 'strongs_id'


class BookViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    lookup_field = 'osis_id'


class BookChaptersView(APIView):
    def get(self, request, osis_id):
        book = get_object_or_404(Book, osis_id=osis_id)
        chapters = (
            Verse.objects.filter(book=book)
            .values_list('chapter', flat=True)
            .distinct()
            .order_by('chapter')
        )
        return Response({'book': osis_id, 'chapters': list(chapters)})


class ChapterVersesView(generics.ListAPIView):
    serializer_class = ChapterVerseSerializer

    def get_queryset(self):
        book = get_object_or_404(Book, osis_id=self.kwargs['osis_id'])
        chapter = int(self.kwargs['chapter'])
        return (
            Verse.objects.filter(book=book, chapter=chapter)
            .prefetch_related('wordoccurrence_set__hebrew_analysis')
            .order_by('verse')
        )


class WordDetailView(generics.RetrieveAPIView):
    serializer_class = WordDetailSerializer
    queryset = WordOccurrence.objects.select_related('verse', 'hebrew_analysis')


class ExportBookJSONView(APIView):
    def get(self, request, osis_id):
        book = get_object_or_404(Book, osis_id=osis_id)
        verses = (
            Verse.objects.filter(book=book)
            .prefetch_related('wordoccurrence_set__hebrew_analysis')
            .order_by('chapter', 'verse')
        )

        # Build gloss map for entire book
        strongs_ids = set(
            WordOccurrence.objects.filter(verse__book=book)
            .exclude(strongs_id__isnull=True)
            .exclude(strongs_id='')
            .values_list('strongs_id', flat=True)
        )
        gloss_map = dict(
            Lexeme.objects.filter(strongs_id__in=strongs_ids)
            .values_list('strongs_id', 'gloss')
        )

        data = {
            'book': book.name,
            'osis_id': book.osis_id,
            'testament': book.get_testament_display(),
            'attribution': {
                'source': 'Open Scriptures Hebrew Bible',
                'url': 'https://hb.openscriptures.org',
                'license': 'CC BY 4.0',
            },
            'verses': [],
        }

        for v in verses:
            verse_data = {
                'reference': v.osis_id,
                'chapter': v.chapter,
                'verse': v.verse,
                'words': [],
            }
            for w in v.wordoccurrence_set.all():
                word_data = {
                    'position': w.position,
                    'surface': w.surface,
                    'lemma': w.lemma,
                    'morphology': w.morphology,
                    'strongs_id': w.strongs_id,
                    'gloss': gloss_map.get(w.strongs_id, ''),
                }
                try:
                    analysis = w.hebrew_analysis
                    word_data['analysis'] = {
                        'part_of_speech': analysis.part_of_speech,
                        'binyan': analysis.binyan,
                        'conjugation': analysis.conjugation,
                        'person': analysis.person,
                        'gender': analysis.gender,
                        'number': analysis.number,
                        'state': analysis.state,
                    }
                except HebrewMorphAnalysis.DoesNotExist:
                    pass
                verse_data['words'].append(word_data)
            data['verses'].append(verse_data)

        response = JsonResponse(data, json_dumps_params={'ensure_ascii': False, 'indent': 2})
        response['Content-Disposition'] = f'attachment; filename="{osis_id}.json"'
        return response


class ExportBookCSVView(APIView):
    def get(self, request, osis_id):
        book = get_object_or_404(Book, osis_id=osis_id)

        # Build gloss map
        strongs_ids = set(
            WordOccurrence.objects.filter(verse__book=book)
            .exclude(strongs_id__isnull=True)
            .exclude(strongs_id='')
            .values_list('strongs_id', flat=True)
        )
        gloss_map = dict(
            Lexeme.objects.filter(strongs_id__in=strongs_ids)
            .values_list('strongs_id', 'gloss')
        )

        def rows():
            yield CSV_HEADER
            words = (
                WordOccurrence.objects.filter(verse__book=book)
                .select_related('verse', 'hebrew_analysis')
                .order_by('verse__chapter', 'verse__verse', 'position')
            )
            for w in words.iterator():
                analysis_pos = ''
                analysis_binyan = ''
                try:
                    a = w.hebrew_analysis
                    analysis_pos = a.part_of_speech
                    analysis_binyan = a.binyan or ''
                except HebrewMorphAnalysis.DoesNotExist:
                    pass
                yield [
                    w.verse.osis_id,
                    w.verse.chapter,
                    w.verse.verse,
                    w.position,
                    w.surface,
                    w.lemma,
                    w.morphology,
                    w.strongs_id or '',
                    gloss_map.get(w.strongs_id, ''),
                    analysis_pos,
                    analysis_binyan,
                ]

        def stream():
            import io
            writer = csv.writer(buf := io.StringIO())
            for row in rows():
                writer.writerow(row)
                yield buf.getvalue()
                buf.seek(0)
                buf.truncate(0)

        response = StreamingHttpResponse(stream(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{osis_id}.csv"'
        return response


CSV_HEADER = [
    'reference',
    'chapter',
    'verse',
    'position',
    'surface',
    'lemma',
    'morphology',
    'strongs_id',
    'gloss',
    'part_of_speech',
    'binyan',
]
