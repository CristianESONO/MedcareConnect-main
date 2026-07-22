from django.core.management.base import BaseCommand

from healthcare.organisme_types import sync_organisme_types, type_organisme_queryset


class Command(BaseCommand):
    help = "Synchronise la liste des types d'établissement (inscription prestataire)."

    def handle(self, *args, **options):
        stats = sync_organisme_types()
        total = type_organisme_queryset().count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Types synchronisés — créés: {stats['created']}, "
                f"mis à jour: {stats['updated']}, fusionnés: {stats['merged']}, "
                f"total: {total}"
            )
        )
        for row in type_organisme_queryset():
            self.stdout.write(f"  {row.order:3d} · {row.name}")
