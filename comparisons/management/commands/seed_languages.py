from django.core.management.base import BaseCommand

from comparisons.models import Language

# (name, family, branch, iso_639_3, region)
LANGUAGES = [
    ("Bemba", "Niger-Congo", "Bantu", "bem", "Zambia, DR Congo"),
    ("Lozi", "Niger-Congo", "Bantu", "loz", "Zambia, Namibia"),
    ("Zulu", "Niger-Congo", "Bantu", "zul", "South Africa"),
    ("Shona", "Niger-Congo", "Bantu", "sna", "Zimbabwe, Mozambique"),
    ("Yoruba", "Niger-Congo", "Volta-Niger", "yor", "Nigeria, Benin"),
    ("Igbo", "Niger-Congo", "Volta-Niger", "ibo", "Nigeria"),
    ("Swahili", "Niger-Congo", "Bantu", "swh", "East Africa"),
    ("Lingala", "Niger-Congo", "Bantu", "lin", "DR Congo, Republic of Congo"),
    ("Tswana", "Niger-Congo", "Bantu", "tsn", "Botswana, South Africa"),
    ("Sotho", "Niger-Congo", "Bantu", "sot", "Lesotho, South Africa"),
    ("Xhosa", "Niger-Congo", "Bantu", "xho", "South Africa"),
    ("Twi", "Niger-Congo", "Kwa", "twi", "Ghana"),
    ("Wolof", "Niger-Congo", "Atlantic", "wol", "Senegal, Gambia"),
    ("Tonga", "Niger-Congo", "Bantu", "toi", "Zambia, Zimbabwe"),
    ("Chewa", "Niger-Congo", "Bantu", "nya", "Malawi, Zambia, Mozambique"),
]


class Command(BaseCommand):
    help = "Seed the Language table with initial Niger-Congo languages."

    def handle(self, *args, **options):
        created = 0
        for name, family, branch, iso_639_3, region in LANGUAGES:
            _, is_created = Language.objects.get_or_create(
                name=name,
                defaults={
                    "family": family,
                    "branch": branch,
                    "iso_639_3": iso_639_3,
                    "region": region,
                },
            )
            if is_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Languages created: {created}"))
