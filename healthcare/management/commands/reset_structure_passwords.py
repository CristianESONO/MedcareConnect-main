"""Réinitialise le mot de passe de tous les comptes prestataires (structures)."""

from django.core.management.base import BaseCommand

from healthcare.models import OrganismeDeSante

DEFAULT_PASSWORD = "medcare2024"


class Command(BaseCommand):
    help = (
        "Définit le même mot de passe pour tous les utilisateurs liés à une "
        "OrganismeDeSante (comptes prestataires / structures)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help=f"Mot de passe à appliquer (défaut : {DEFAULT_PASSWORD}).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche les comptes concernés sans modifier les mots de passe.",
        )

    def handle(self, *args, **options):
        password = options["password"]
        dry_run = options["dry_run"]

        organismes = (
            OrganismeDeSante.objects.select_related("user")
            .filter(user__isnull=False)
            .order_by("name")
        )
        count = 0
        for org in organismes:
            user = org.user
            if user is None:
                continue
            if dry_run:
                self.stdout.write(f"  {org.name} → {user.username}")
            else:
                user.set_password(password)
                user.save(update_fields=["password"])
            count += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[dry-run] {count} compte(s) structure seraient mis à jour."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{count} compte(s) structure mis à jour (mot de passe : {password})."
                )
            )
