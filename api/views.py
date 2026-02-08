from rest_framework import viewsets

from lexicon.models import Lexeme

from .serializers import LexemeSerializer


class LexemeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Lexeme.objects.all()
    serializer_class = LexemeSerializer
    lookup_field = 'strongs_id'
