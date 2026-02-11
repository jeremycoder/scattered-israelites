from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from comparisons.models import ContributorProfile, LexicalComparison, Vote


@receiver(post_save, sender=LexicalComparison)
def update_accepted_count(sender, instance, **kwargs):
    """When a comparison is accepted, update the creator's accepted_contributions count."""
    if instance.status == LexicalComparison.STATUS_ACCEPTED and instance.created_by_id:
        profile, _ = ContributorProfile.objects.get_or_create(user_id=instance.created_by_id)
        profile.accepted_contributions = LexicalComparison.objects.filter(
            created_by_id=instance.created_by_id,
            status=LexicalComparison.STATUS_ACCEPTED,
            is_removed=False,
        ).count()
        profile.save(update_fields=["accepted_contributions"])
        _maybe_auto_promote(profile)


def _maybe_auto_promote(profile):
    """Auto-promote new → regular at 3 accepted entries."""
    if (
        profile.trust_level == ContributorProfile.TRUST_NEW
        and profile.accepted_contributions >= 3
    ):
        profile.trust_level = ContributorProfile.TRUST_REGULAR
        profile.save(update_fields=["trust_level"])


@receiver(post_save, sender=Vote)
def recalculate_confidence_score(sender, instance, **kwargs):
    """Recalculate the comparison's confidence_score from active votes."""
    comparison = instance.comparison
    score = (
        Vote.objects.filter(comparison=comparison, is_active=True)
        .aggregate(total=models.Sum("weight"))["total"]
        or 0
    )
    LexicalComparison.objects.filter(pk=comparison.pk).update(confidence_score=score)

    # Auto-dispute: if score drops below -5 and currently accepted
    if score < -5:
        LexicalComparison.objects.filter(
            pk=comparison.pk,
            status=LexicalComparison.STATUS_ACCEPTED,
        ).update(status=LexicalComparison.STATUS_DISPUTED)
