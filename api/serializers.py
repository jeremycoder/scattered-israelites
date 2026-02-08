from rest_framework import serializers

from lexicon.models import Lexeme


class LexemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lexeme
        fields = [
            'strongs_id',
            'language',
            'lemma',
            'transliteration',
            'gloss',
            'definition',
        ]
