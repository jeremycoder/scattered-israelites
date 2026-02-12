from django.db import models


class Lexeme(models.Model):
    LANGUAGE_HEBREW = 'hebrew'
    LANGUAGE_GREEK = 'greek'
    LANGUAGE_CHOICES = [
        (LANGUAGE_HEBREW, 'Hebrew'),
        (LANGUAGE_GREEK, 'Greek'),
    ]

    strongs_id = models.CharField(max_length=10, primary_key=True)
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES)
    lemma = models.CharField(max_length=128)
    transliteration = models.CharField(max_length=128, blank=True)
    gloss = models.TextField(blank=True)
    definition = models.TextField(blank=True)

    class Meta:
        ordering = ['strongs_id']

    def __str__(self) -> str:
        return f'{self.strongs_id} {self.lemma}'


class Book(models.Model):
    TESTAMENT_OLD = 'ot'
    TESTAMENT_NEW = 'nt'
    TESTAMENT_CHOICES = [
        (TESTAMENT_OLD, 'Old Testament'),
        (TESTAMENT_NEW, 'New Testament'),
    ]

    osis_id = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=64, unique=True)
    testament = models.CharField(max_length=2, choices=TESTAMENT_CHOICES)
    canonical_order = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ['canonical_order']

    def __str__(self) -> str:
        return self.name


class Verse(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    chapter = models.PositiveSmallIntegerField()
    verse = models.PositiveSmallIntegerField()
    osis_id = models.CharField(max_length=32, unique=True)

    class Meta:
        ordering = ['book__canonical_order', 'chapter', 'verse']
        unique_together = [('book', 'chapter', 'verse')]

    def __str__(self) -> str:
        return self.osis_id


class WordOccurrence(models.Model):
    LANGUAGE_HEBREW = Lexeme.LANGUAGE_HEBREW
    LANGUAGE_GREEK = Lexeme.LANGUAGE_GREEK
    LANGUAGE_CHOICES = Lexeme.LANGUAGE_CHOICES

    verse = models.ForeignKey(Verse, on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField()
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES)
    surface = models.TextField(blank=True)
    lemma = models.TextField(blank=True)
    morphology = models.CharField(max_length=64, blank=True)
    strongs_id = models.CharField(max_length=10, blank=True, null=True)
    source = models.CharField(max_length=32)
    word_id = models.CharField(max_length=64, blank=True)
    part_of_speech = models.CharField(max_length=32, blank=True)
    parsing = models.CharField(max_length=64, blank=True)
    variant = models.CharField(max_length=64, blank=True)
    normalized = models.TextField(blank=True)
    slug = models.CharField(max_length=128, blank=True, default='')

    class Meta:
        ordering = ['verse__book__canonical_order', 'verse__chapter', 'verse__verse', 'position']
        indexes = [
            models.Index(fields=['strongs_id']),
            models.Index(fields=['lemma']),
            models.Index(fields=['language']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['verse', 'slug'],
                name='unique_word_slug_per_verse',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.verse.osis_id}#{self.position} {self.surface}'


class HebrewMorphAnalysis(models.Model):
    """
    One-to-one with WordOccurrence, for detailed Biblical Hebrew morphology.
    """

    word = models.OneToOneField(
        "WordOccurrence",
        on_delete=models.CASCADE,
        related_name="hebrew_analysis",
    )

    # Core POS info
    part_of_speech = models.CharField(max_length=32)          # verb, noun, adjective, pronoun, etc.
    subtype = models.CharField(max_length=32, blank=True, null=True)

    # Verb features
    binyan = models.CharField(max_length=16, blank=True, null=True)        # Qal, Niphal, Piel, etc.
    conjugation = models.CharField(max_length=32, blank=True, null=True)   # qatal, yiqtol, wayyiqtol, etc.
    person = models.PositiveSmallIntegerField(blank=True, null=True)       # 1,2,3
    gender = models.CharField(max_length=16, blank=True, null=True)        # masculine, feminine, common
    number = models.CharField(max_length=16, blank=True, null=True)        # singular, plural, dual
    aspect = models.CharField(max_length=16, blank=True, null=True)        # optional: perfective, etc.
    voice = models.CharField(max_length=16, blank=True, null=True)         # active, passive, middle/reflexive
    mood = models.CharField(max_length=16, blank=True, null=True)          # indicative, jussive, cohortative, imperative
    polarity = models.CharField(max_length=16, blank=True, null=True)      # affirmative, negative
    negation_particle = models.CharField(max_length=16, blank=True, null=True)

    # Nominal features
    state = models.CharField(max_length=16, blank=True, null=True)         # absolute, construct
    definiteness = models.CharField(max_length=16, blank=True, null=True)  # definite, indefinite, proper, pronominal

    # Suffix pronoun features, if present
    suffix_person = models.PositiveSmallIntegerField(blank=True, null=True)
    suffix_gender = models.CharField(max_length=16, blank=True, null=True)
    suffix_number = models.CharField(max_length=16, blank=True, null=True)

    # You can optionally store OSHB/WTM raw code for reference
    raw_morph_code = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        verbose_name = "Hebrew Morphological Analysis"
        verbose_name_plural = "Hebrew Morphological Analyses"

    def __str__(self) -> str:
        return f"{self.word} ({self.part_of_speech})"


class HebrewLexicalInfo(models.Model):
    """
    Hebrew lexical data tied to a specific occurrence.
    You already have Lexeme by Strong's; this lets you store lemma/root at the token level.
    """

    word = models.OneToOneField(
        "WordOccurrence",
        on_delete=models.CASCADE,
        related_name="hebrew_lexical",
    )

    lemma = models.CharField(max_length=128)                 # pointed lemma
    lemma_unpointed = models.CharField(max_length=128)       # consonantal
    root = models.CharField(max_length=16)                   # e.g. "ראה"
    root_consonants = models.CharField(max_length=32)        # e.g. "ר,א,ה" (or switch to JSONField)
    strongs = models.CharField(max_length=10, blank=True, null=True)  # redundant with WordOccurrence.strongs_id but convenient
    gloss_basic = models.CharField(max_length=255, blank=True, null=True)
    sense = models.CharField(max_length=255, blank=True, null=True)

    # Optional: link back to your Lexeme row if you like
    lexeme = models.ForeignKey(
        "Lexeme",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="hebrew_occurrences",
    )

    class Meta:
        verbose_name = "Hebrew Lexical Info"
        verbose_name_plural = "Hebrew Lexical Info"

    def __str__(self) -> str:
        return f"{self.word} – {self.lemma}"


class HebrewMorpheme(models.Model):
    """
    Fine-grained morpheme segmentation for a Hebrew word.
    Multiple rows per WordOccurrence.
    """

    word = models.ForeignKey(
        "WordOccurrence",
        on_delete=models.CASCADE,
        related_name="hebrew_morphemes",
    )

    slot_order = models.PositiveSmallIntegerField()          # 0,1,2,... left to right
    slot = models.CharField(max_length=32)                   # preformative_conjunction, verbal_prefix, base, suffix, etc.
    type = models.CharField(max_length=32)                   # conjunction, preposition, article, root_plus_pattern, suffix_pronoun, etc.

    form = models.CharField(max_length=64)                   # pointed morpheme
    unpointed = models.CharField(max_length=64)              # consonantal

    root = models.CharField(max_length=16, blank=True, null=True)
    binyan = models.CharField(max_length=16, blank=True, null=True)

    person = models.PositiveSmallIntegerField(blank=True, null=True)
    gender = models.CharField(max_length=16, blank=True, null=True)
    number = models.CharField(max_length=16, blank=True, null=True)

    gloss = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["word", "slot_order"]
        verbose_name = "Hebrew Morpheme"
        verbose_name_plural = "Hebrew Morphemes"

    def __str__(self) -> str:
        return f"{self.word} [{self.slot_order}] {self.form}"


class HebrewTranslation(models.Model):
    """
    Simple English rendering attached to a specific Hebrew word occurrence.
    """

    word = models.OneToOneField(
        "WordOccurrence",
        on_delete=models.CASCADE,
        related_name="hebrew_translation",
    )

    phrase = models.CharField(max_length=255)                     # e.g. "and he saw"
    literal = models.CharField(max_length=255, blank=True, null=True)  # e.g. "and-he-saw"

    class Meta:
        verbose_name = "Hebrew Translation"
        verbose_name_plural = "Hebrew Translations"

    def __str__(self) -> str:
        return f"{self.word} → {self.phrase}"


class TranslationBatch(models.Model):
    """
    Audit trail for a batch of AI-generated translations for a single verse+language.
    Stores the raw response, prompt used, and model name so every translation
    can be traced back to its origin.
    """

    verse = models.ForeignKey(Verse, on_delete=models.CASCADE, related_name='translation_batches')
    language_code = models.CharField(max_length=10, db_index=True)
    language_name = models.CharField(max_length=50)
    prompt = models.TextField(blank=True)
    raw_response = models.JSONField()
    model_name = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Translation Batch"
        verbose_name_plural = "Translation Batches"

    def __str__(self) -> str:
        return f"{self.verse} [{self.language_code}] — {self.created_at:%Y-%m-%d %H:%M}"


class TranslationFlag(models.Model):
    """
    Flags words where the AI-assisted translation is uncertain, divergent
    across major English versions, or involves a rare/hapax legomenon.
    Displayed publicly for transparency and human review.
    """

    FLAG_DIVERGENT = 'divergent'
    FLAG_RARE = 'rare'
    FLAG_UNCERTAIN = 'uncertain'
    FLAG_CHOICES = [
        (FLAG_DIVERGENT, 'Divergent — major translations disagree'),
        (FLAG_RARE, 'Rare — hapax legomenon or very low frequency'),
        (FLAG_UNCERTAIN, 'Uncertain — meaning debated among scholars'),
    ]

    word_occurrence = models.ForeignKey(
        'WordOccurrence',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='translation_flags',
    )
    book = models.ForeignKey('Book', on_delete=models.CASCADE, related_name='translation_flags')
    chapter = models.PositiveSmallIntegerField()
    verse = models.PositiveSmallIntegerField()
    position = models.PositiveSmallIntegerField()
    surface = models.CharField(max_length=128)
    strongs_id = models.CharField(max_length=10, blank=True)
    flag_type = models.CharField(max_length=16, choices=FLAG_CHOICES)
    note = models.TextField(help_text='Explanation of what is uncertain or divergent')
    sources_consulted = models.TextField(
        blank=True,
        help_text='References checked (Strong\'s, BDB, translations, etc.)',
    )
    resolution = models.TextField(
        blank=True,
        help_text='How this was resolved after human review',
    )
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['book__canonical_order', 'chapter', 'verse', 'position']
        verbose_name = 'Translation Flag'
        verbose_name_plural = 'Translation Flags'

    def __str__(self):
        return f'{self.book} {self.chapter}:{self.verse} #{self.position} {self.surface} [{self.flag_type}]'


class WordTranslation(models.Model):
    """
    Contextual translation of a Hebrew word in a specific language.
    Multiple translations per word (one per language).
    """

    word = models.ForeignKey(
        "WordOccurrence",
        on_delete=models.CASCADE,
        related_name="translations",
    )
    language_code = models.CharField(max_length=10, db_index=True)  # 'en', 'es', 'fr'
    language_name = models.CharField(max_length=50)                 # 'English', 'Spanish'
    phrase = models.CharField(max_length=255)                       # "in the beginning"
    literal = models.CharField(max_length=255, blank=True)          # "in-beginning-of"
    source = models.TextField(blank=True)                            # audit trail citation
    batch = models.ForeignKey(
        'TranslationBatch',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='translations',
    )

    class Meta:
        unique_together = [('word', 'language_code')]
        ordering = ['language_code']
        verbose_name = "Word Translation"
        verbose_name_plural = "Word Translations"

    def __str__(self) -> str:
        return f"{self.word} [{self.language_code}] → {self.phrase}"

