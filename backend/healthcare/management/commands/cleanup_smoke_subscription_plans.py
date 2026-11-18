"""Supprime les plans d'abonnement créés par les scripts smoke (slug smoke-*)."""

from django.core.management.base import BaseCommand

from healthcare.subscription_admin import cleanup_smoke_subscription_plans


class Command(BaseCommand):
    help = "Réaffecte les structures et supprime les plans d'abonnement Smoke de test."

    def handle(self, *args, **options):
        n = cleanup_smoke_subscription_plans()
        self.stdout.write(self.style.SUCCESS(f"{n} plan(s) Smoke supprimé(s)."))
