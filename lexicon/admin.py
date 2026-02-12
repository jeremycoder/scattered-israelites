from django.contrib import admin

from .models import Book, Lexeme, TranslationBatch, TranslationFlag, Verse, WordOccurrence, WordTranslation


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


@admin.register(TranslationBatch)
class TranslationBatchAdmin(admin.ModelAdmin):
    list_display = ('verse', 'language_code', 'model_name', 'created_at')
    list_filter = ('language_code',)
    search_fields = ('verse__osis_id', 'model_name', 'notes')
    readonly_fields = ('created_at',)


@admin.register(TranslationFlag)
class TranslationFlagAdmin(admin.ModelAdmin):
    list_display = ('book', 'chapter', 'verse', 'position', 'surface', 'strongs_id', 'flag_type', 'is_resolved')
    list_filter = ('flag_type', 'is_resolved', 'book')
    search_fields = ('surface', 'strongs_id', 'note', 'sources_consulted')
    readonly_fields = ('created_at',)


@admin.register(WordTranslation)
class WordTranslationAdmin(admin.ModelAdmin):
    list_display = ('word', 'language_code', 'language_name', 'phrase', 'source', 'batch')
    list_filter = ('language_code',)
    search_fields = ('phrase', 'literal', 'word__surface')
