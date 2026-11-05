from django.core.management.base import BaseCommand
from django.utils.text import slugify
from healthcare.models import Region

SENEGAL_14_REGIONS = [
    "Dakar",
    "Diourbel",
    "Fatick",
    "Kaffrine",
    "Kaolack",
    "Kédougou",
    "Kolda",
    "Louga",
    "Matam",
    "Saint-Louis",
    "Sédhiou",
    "Tambacounda",
    "Thiès",
    "Ziguinchor",
]


class Command(BaseCommand):
    help = "Synchronise les 14 régions administratives officielles du Sénégal dans la base de données."

    def handle(self, *args, **options):
        created_count = 0
        existing_count = 0
        for name in SENEGAL_14_REGIONS:
            slug = slugify(name)
            region, created = Region.objects.get_or_create(
                name=name,
                defaults={"slug": slug}
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  + Région créée : {name}"))
            else:
                existing_count += 1

        total = Region.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSynchronisation terminée : {created_count} créée(s), "
                f"{existing_count} déjà existante(s). Total en base : {total}/14."
            )
        )
