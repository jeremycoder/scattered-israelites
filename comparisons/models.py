import uuid

from django.conf import settings
from django.db import models


class Language(models.Model):
    name = models.CharField(max_length=128, unique=True)
    alt_names = models.TextField(blank=True, help_text="Comma-separated alternative names")
    family = models.CharField(max_length=128, blank=True, default="Niger-Congo")
    branch = models.CharField(max_length=128, blank=True)
    iso_639_3 = models.CharField(max_length=3, blank=True, verbose_name="ISO 639-3")
    region = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ContributorProfile(models.Model):
    TRUST_NEW = "new"
    TRUST_REGULAR = "regular"
    TRUST_TRUSTED = "trusted"
    TRUST_ADMIN = "admin"
    TRUST_OWNER = "owner"
    TRUST_CHOICES = [
        (TRUST_NEW, "New (weight 1)"),
        (TRUST_REGULAR, "Regular (weight 2)"),
        (TRUST_TRUSTED, "Trusted (weight 3)"),
        (TRUST_ADMIN, "Admin (weight 5)"),
        (TRUST_OWNER, "Owner (weight 10)"),
    ]
    TRUST_WEIGHTS = {
        TRUST_NEW: 1,
        TRUST_REGULAR: 2,
        TRUST_TRUSTED: 3,
        TRUST_ADMIN: 5,
        TRUST_OWNER: 10,
    }

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contributor_profile",
    )
    display_name = models.CharField(max_length=150, blank=True)
    bio = models.TextField(blank=True)
    languages_spoken = models.ManyToManyField(Language, blank=True)
    trust_level = models.CharField(max_length=16, choices=TRUST_CHOICES, default=TRUST_NEW)
    accepted_contributions = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return self.display_name or self.user.username

    @property
    def trust_weight(self):
        return self.TRUST_WEIGHTS.get(self.trust_level, 1)


class Invitation(models.Model):
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
    )
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_invitations",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        status = "accepted" if self.accepted_at else "pending"
        return f"{self.email} ({status})"


class LexicalComparison(models.Model):
    CATEGORY_COGNATE = "cognate"
    CATEGORY_SEMANTIC = "semantic"
    CATEGORY_PHRASE = "phrase"
    CATEGORY_PHONETIC = "phonetic"
    CATEGORY_GRAMMATICAL = "grammatical"
    CATEGORY_OTHER = "other"
    CATEGORY_CHOICES = [
        (CATEGORY_COGNATE, "Cognate"),
        (CATEGORY_SEMANTIC, "Semantic parallel"),
        (CATEGORY_PHRASE, "Phrasal parallel"),
        (CATEGORY_PHONETIC, "Phonetic similarity"),
        (CATEGORY_GRAMMATICAL, "Grammatical parallel"),
        (CATEGORY_OTHER, "Other"),
    ]

    STATUS_DRAFT = "draft"
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_DISPUTED = "disputed"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PENDING, "Pending review"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_DISPUTED, "Disputed"),
        (STATUS_REJECTED, "Rejected"),
    ]

    # Hebrew side
    lexeme = models.ForeignKey(
        "lexicon.Lexeme",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comparisons",
        help_text="Optional link to Strong's lexeme",
    )
    hebrew_word = models.CharField(max_length=128, help_text="Hebrew form (pointed)")
    hebrew_transliteration = models.CharField(max_length=128, blank=True)
    hebrew_root = models.CharField(max_length=32, blank=True)
    hebrew_meaning = models.CharField(max_length=255)

    # Niger-Congo side
    language = models.ForeignKey(Language, on_delete=models.PROTECT, related_name="comparisons")
    nc_word = models.CharField(max_length=128, verbose_name="Niger-Congo word")
    nc_transliteration = models.CharField(max_length=128, blank=True, verbose_name="NC transliteration")
    nc_meaning = models.CharField(max_length=255, verbose_name="NC meaning")
    nc_usage_example = models.TextField(blank=True, verbose_name="NC usage example")

    # Classification
    category = models.CharField(max_length=16, choices=CATEGORY_CHOICES, default=CATEGORY_COGNATE)
    semantic_domain = models.CharField(max_length=128, blank=True)
    notes = models.TextField(blank=True)

    # Evidence
    source_type = models.CharField(max_length=64, blank=True, help_text="e.g. oral tradition, published research")
    source_reference = models.TextField(blank=True)

    # Status / moderation
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_locked = models.BooleanField(default=False, help_text="Locked entries cannot receive votes")
    confidence_score = models.IntegerField(default=0, help_text="Denormalized sum of active vote weights")

    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_comparisons",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_removed = models.BooleanField(default=False, help_text="Soft delete")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["hebrew_word", "language", "nc_word"],
                condition=models.Q(is_removed=False),
                name="unique_comparison_not_removed",
            ),
        ]
        verbose_name = "Lexical Comparison"

    def __str__(self):
        return f"{self.hebrew_word} ↔ {self.nc_word} ({self.language})"


class ComparisonRevision(models.Model):
    comparison = models.ForeignKey(
        LexicalComparison,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    revision_number = models.PositiveIntegerField()
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    data = models.JSONField(help_text="Snapshot of the comparison fields at this revision")
    change_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["comparison", "revision_number"]
        unique_together = [("comparison", "revision_number")]

    def __str__(self):
        return f"Rev {self.revision_number} of {self.comparison}"


class Vote(models.Model):
    AGREE = 1
    DISAGREE = -1
    VALUE_CHOICES = [
        (AGREE, "Agree (+1)"),
        (DISAGREE, "Disagree (-1)"),
    ]

    comparison = models.ForeignKey(
        LexicalComparison,
        on_delete=models.CASCADE,
        related_name="votes",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comparison_votes",
    )
    value = models.SmallIntegerField(choices=VALUE_CHOICES)
    weight = models.SmallIntegerField(
        help_text="trust_weight × value, stamped at vote time",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["comparison", "user"],
                name="one_vote_per_user_per_comparison",
            ),
        ]

    def __str__(self):
        label = "+" if self.value == self.AGREE else "-"
        return f"{self.user} {label} on {self.comparison}"


class Flag(models.Model):
    REASON_INACCURATE = "inaccurate"
    REASON_DUPLICATE = "duplicate"
    REASON_SPAM = "spam"
    REASON_OFFENSIVE = "offensive"
    REASON_OTHER = "other"
    REASON_CHOICES = [
        (REASON_INACCURATE, "Inaccurate"),
        (REASON_DUPLICATE, "Duplicate"),
        (REASON_SPAM, "Spam"),
        (REASON_OFFENSIVE, "Offensive"),
        (REASON_OTHER, "Other"),
    ]

    RESOLUTION_PENDING = "pending"
    RESOLUTION_UPHELD = "upheld"
    RESOLUTION_DISMISSED = "dismissed"
    RESOLUTION_CHOICES = [
        (RESOLUTION_PENDING, "Pending"),
        (RESOLUTION_UPHELD, "Upheld"),
        (RESOLUTION_DISMISSED, "Dismissed"),
    ]

    comparison = models.ForeignKey(
        LexicalComparison,
        on_delete=models.CASCADE,
        related_name="flags",
    )
    raised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="raised_flags",
    )
    reason = models.CharField(max_length=16, choices=REASON_CHOICES)
    explanation = models.TextField(blank=True)

    resolution = models.CharField(
        max_length=16,
        choices=RESOLUTION_CHOICES,
        default=RESOLUTION_PENDING,
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_flags",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Flag({self.reason}) on {self.comparison}"
