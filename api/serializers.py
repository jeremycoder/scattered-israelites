from rest_framework import serializers

from lexicon.models import (
    Book,
    HebrewMorphAnalysis,
    Lexeme,
    Verse,
    WordOccurrence,
)


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


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['osis_id', 'name', 'testament', 'canonical_order']


class HebrewMorphAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = HebrewMorphAnalysis
        fields = [
            'part_of_speech',
            'subtype',
            'binyan',
            'conjugation',
            'person',
            'gender',
            'number',
            'state',
            'definiteness',
            'suffix_person',
            'suffix_gender',
            'suffix_number',
            'raw_morph_code',
        ]


class WordOccurrenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WordOccurrence
        fields = [
            'id',
            'position',
            'language',
            'surface',
            'lemma',
            'morphology',
            'strongs_id',
            'part_of_speech',
        ]


class ChapterWordSerializer(serializers.ModelSerializer):
    hebrew_analysis = HebrewMorphAnalysisSerializer(read_only=True)

    class Meta:
        model = WordOccurrence
        fields = [
            'id',
            'position',
            'language',
            'surface',
            'lemma',
            'morphology',
            'strongs_id',
            'part_of_speech',
            'hebrew_analysis',
        ]


class ChapterVerseSerializer(serializers.ModelSerializer):
    words = ChapterWordSerializer(source='wordoccurrence_set', many=True, read_only=True)

    class Meta:
        model = Verse
        fields = ['id', 'chapter', 'verse', 'osis_id', 'words']


class WordDetailSerializer(serializers.ModelSerializer):
    hebrew_analysis = HebrewMorphAnalysisSerializer(read_only=True)
    lexeme = serializers.SerializerMethodField()
    verse_ref = serializers.CharField(source='verse.osis_id', read_only=True)

    class Meta:
        model = WordOccurrence
        fields = [
            'id',
            'position',
            'language',
            'surface',
            'lemma',
            'morphology',
            'strongs_id',
            'part_of_speech',
            'verse_ref',
            'hebrew_analysis',
            'lexeme',
        ]

    def get_lexeme(self, obj):
        if obj.strongs_id:
            try:
                lex = Lexeme.objects.get(strongs_id=obj.strongs_id)
                return LexemeSerializer(lex).data
            except Lexeme.DoesNotExist:
                pass
        return None
