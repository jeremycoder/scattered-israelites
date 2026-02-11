import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from comparisons.models import ContributorProfile, Language, LexicalComparison

User = get_user_model()


class Command(BaseCommand):
    help = "Import lexical comparisons from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str, help="Path to comparisons JSON file")
        parser.add_argument(
            "--owner-username",
            type=str,
            default="",
            help="Username of the owner (will get/create ContributorProfile with trust_level=owner)",
        )

    def handle(self, *args, **options):
        json_path = Path(options["json_path"]).expanduser()
        if not json_path.exists():
            raise CommandError(f"File not found: {json_path}")

        with json_path.open(encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            entries = [data]
        elif isinstance(data, list):
            entries = data
        else:
            raise CommandError("JSON must be an object or array of objects.")

        # Resolve owner
        owner_user = None
        owner_username = options["owner_username"]
        if owner_username:
            try:
                owner_user = User.objects.get(username=owner_username)
            except User.DoesNotExist:
                raise CommandError(f"User not found: {owner_username}")
        else:
            # Use the first superuser as default owner
            owner_user = User.objects.filter(is_superuser=True).first()

        if owner_user:
            profile, _ = ContributorProfile.objects.get_or_create(user=owner_user)
            if profile.trust_level != ContributorProfile.TRUST_OWNER:
                profile.trust_level = ContributorProfile.TRUST_OWNER
                profile.save(update_fields=["trust_level"])
                self.stdout.write(f"Set {owner_user.username} as owner.")

        total_created = 0
        total_skipped = 0
        total_errors = 0

        for entry in entries:
            required = ("hebrew_word", "hebrew_meaning", "language", "nc_word", "nc_meaning")
            missing = [f for f in required if f not in entry]
            if missing:
                self.stderr.write(self.style.ERROR(
                    f"Missing field(s) {missing} in entry: {entry}"
                ))
                total_errors += 1
                continue

            # Look up language
            lang_name = entry["language"]
            try:
                language = Language.objects.get(name=lang_name)
            except Language.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Language not found: {lang_name}"))
                total_errors += 1
                continue

            with transaction.atomic():
                _obj, created = LexicalComparison.objects.get_or_create(
                    hebrew_word=entry["hebrew_word"],
                    language=language,
                    nc_word=entry["nc_word"],
                    is_removed=False,
                    defaults={
                        "hebrew_transliteration": entry.get("hebrew_transliteration", ""),
                        "hebrew_root": entry.get("hebrew_root", ""),
                        "hebrew_meaning": entry["hebrew_meaning"],
                        "nc_transliteration": entry.get("nc_transliteration", ""),
                        "nc_meaning": entry["nc_meaning"],
                        "nc_usage_example": entry.get("nc_usage_example", ""),
                        "category": entry.get("category", "cognate"),
                        "semantic_domain": entry.get("semantic_domain", ""),
                        "notes": entry.get("notes", ""),
                        "source_type": entry.get("source_type", ""),
                        "source_reference": entry.get("source_reference", ""),
                        "status": entry.get("status", "accepted"),
                        "created_by": owner_user,
                    },
                )

            if created:
                total_created += 1
            else:
                total_skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"Import complete. Created: {total_created}, "
            f"Skipped (existing): {total_skipped}, Errors: {total_errors}"
        ))
