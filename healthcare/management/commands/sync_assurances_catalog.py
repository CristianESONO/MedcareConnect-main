"""Synchronise le référentiel Assurance depuis healthcare/data/catalog_assurances.py."""

from django.core.management.base import BaseCommand

from healthcare.data.catalog_loader import load_assurances_from_docs


class Command(BaseCommand):
    help = "Crée ou met à jour les assurances du catalogue officiel (sans toucher aux PEC)."

    def handle(self, *args, **options):
        mapping = load_assurances_from_docs()
        self.stdout.write(
            self.style.SUCCESS(f"{len(mapping)} assurances synchronisées.")
        )
