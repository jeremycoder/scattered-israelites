from django.contrib import admin

from comparisons.models import (
    ComparisonRevision,
    ContributorProfile,
    Flag,
    Invitation,
    Language,
    LexicalComparison,
    Vote,
)


# ── Inlines ──────────────────────────────────────────────────────────

class ComparisonRevisionInline(admin.TabularInline):
    model = ComparisonRevision
    extra = 0
    readonly_fields = ("revision_number", "edited_by", "data", "change_summary", "created_at")
    can_delete = False


class VoteInline(admin.TabularInline):
    model = Vote
    extra = 0
    readonly_fields = ("user", "value", "weight", "created_at")
    fields = ("user", "value", "weight", "is_active", "created_at")


class FlagInline(admin.TabularInline):
    model = Flag
    extra = 0
    readonly_fields = ("raised_by", "reason", "explanation", "created_at")
    fields = ("raised_by", "reason", "explanation", "resolution", "resolved_by", "created_at")


# ── Model Admins ─────────────────────────────────────────────────────

@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ("name", "family", "branch", "iso_639_3", "region")
    list_filter = ("family",)
    search_fields = ("name", "alt_names", "iso_639_3")


@admin.register(ContributorProfile)
class ContributorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "trust_level", "accepted_contributions")
    list_editable = ("trust_level",)
    list_filter = ("trust_level",)
    search_fields = ("user__username", "display_name")
    raw_id_fields = ("user",)
    filter_horizontal = ("languages_spoken",)


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "invited_by", "created_at", "accepted_at")
    list_filter = ("accepted_at",)
    search_fields = ("email",)
    readonly_fields = ("token", "created_at")
    raw_id_fields = ("invited_by", "accepted_by")


@admin.register(LexicalComparison)
class LexicalComparisonAdmin(admin.ModelAdmin):
    list_display = (
        "hebrew_word",
        "nc_word",
        "language",
        "category",
        "status",
        "is_locked",
        "confidence_score",
        "created_by",
        "created_at",
    )
    list_editable = ("status", "is_locked")
    list_filter = ("status", "category", "language", "is_locked", "is_removed")
    search_fields = (
        "hebrew_word",
        "hebrew_transliteration",
        "hebrew_meaning",
        "nc_word",
        "nc_transliteration",
        "nc_meaning",
    )
    raw_id_fields = ("lexeme", "created_by")
    readonly_fields = ("confidence_score", "created_at", "updated_at")
    inlines = [ComparisonRevisionInline, VoteInline, FlagInline]

    fieldsets = (
        ("Hebrew side", {
            "fields": (
                "lexeme",
                "hebrew_word",
                "hebrew_transliteration",
                "hebrew_root",
                "hebrew_meaning",
            ),
        }),
        ("Niger-Congo side", {
            "fields": (
                "language",
                "nc_word",
                "nc_transliteration",
                "nc_meaning",
                "nc_usage_example",
            ),
        }),
        ("Classification", {
            "fields": ("category", "semantic_domain", "notes"),
        }),
        ("Evidence", {
            "fields": ("source_type", "source_reference"),
        }),
        ("Moderation", {
            "fields": ("status", "is_locked", "confidence_score"),
        }),
        ("Audit", {
            "fields": ("created_by", "created_at", "updated_at", "is_removed"),
        }),
    )

    actions = ["make_accepted", "make_rejected", "lock_entries", "unlock_entries"]

    @admin.action(description="Accept selected comparisons")
    def make_accepted(self, request, queryset):
        updated = queryset.update(status=LexicalComparison.STATUS_ACCEPTED)
        self.message_user(request, f"{updated} comparison(s) accepted.")

    @admin.action(description="Reject selected comparisons")
    def make_rejected(self, request, queryset):
        updated = queryset.update(status=LexicalComparison.STATUS_REJECTED)
        self.message_user(request, f"{updated} comparison(s) rejected.")

    @admin.action(description="Lock selected comparisons")
    def lock_entries(self, request, queryset):
        updated = queryset.update(is_locked=True)
        self.message_user(request, f"{updated} comparison(s) locked.")

    @admin.action(description="Unlock selected comparisons")
    def unlock_entries(self, request, queryset):
        updated = queryset.update(is_locked=False)
        self.message_user(request, f"{updated} comparison(s) unlocked.")


@admin.register(ComparisonRevision)
class ComparisonRevisionAdmin(admin.ModelAdmin):
    list_display = ("comparison", "revision_number", "edited_by", "created_at")
    list_filter = ("created_at",)
    readonly_fields = ("comparison", "revision_number", "edited_by", "data", "change_summary", "created_at")
    raw_id_fields = ("comparison", "edited_by")


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("comparison", "user", "value", "weight", "is_active", "created_at")
    list_editable = ("is_active",)
    list_filter = ("is_active", "value")
    search_fields = ("user__username", "comparison__hebrew_word", "comparison__nc_word")
    raw_id_fields = ("comparison", "user")

    actions = ["deactivate_votes", "activate_votes"]

    @admin.action(description="Deactivate selected votes")
    def deactivate_votes(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} vote(s) deactivated.")

    @admin.action(description="Activate selected votes")
    def activate_votes(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} vote(s) activated.")


@admin.register(Flag)
class FlagAdmin(admin.ModelAdmin):
    list_display = ("comparison", "raised_by", "reason", "resolution", "created_at")
    list_filter = ("reason", "resolution")
    search_fields = ("comparison__hebrew_word", "comparison__nc_word", "explanation")
    raw_id_fields = ("comparison", "raised_by", "resolved_by")
    readonly_fields = ("created_at",)
