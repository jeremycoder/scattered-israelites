from django.contrib import admin

from .models import Book, Lexeme, Verse, WordOccurrence


@admin.register(Lexeme)
class LexemeAdmin(admin.ModelAdmin):
    list_display = ('strongs_id', 'language', 'lemma', 'transliteration', 'gloss')
    list_filter = ('language',)
    search_fields = ('strongs_id', 'lemma', 'transliteration', 'gloss')


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('canonical_order', 'osis_id', 'name', 'testament')
    list_filter = ('testament',)
    search_fields = ('osis_id', 'name')


@admin.register(Verse)
class VerseAdmin(admin.ModelAdmin):
    list_display = ('osis_id', 'book', 'chapter', 'verse')
    list_filter = ('book',)
    search_fields = ('osis_id',)


@admin.register(WordOccurrence)
class WordOccurrenceAdmin(admin.ModelAdmin):
    list_display = ('verse', 'position', 'language', 'surface', 'lemma', 'strongs_id')
    list_filter = ('language', 'source')
    search_fields = ('surface', 'lemma', 'strongs_id', 'word_id')
