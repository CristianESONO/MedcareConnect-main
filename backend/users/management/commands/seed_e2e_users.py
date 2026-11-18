"""Comptes de test Playwright à mot de passe défini via MEDCARE_E2E_PASSWORD."""

from django.core.management.base import BaseCommand

from healthcare.models import OrganismeDeSante, SubscriptionPlan, TypeOrganisme
from users.models import PatientProfile, User


class Command(BaseCommand):
    help = "Crée les comptes testpatient / prestataire pour le serveur E2E Playwright."

    def handle(self, *args, **options):
        import os
        from django.core.management.base import CommandError
        from django.db import connection
        if connection.vendor != 'sqlite' and os.environ.get('ALLOW_DEMO_IMPORT') != '1':
            raise CommandError('Refus : cette commande crée des comptes de test ; elle ne doit pas tourner sur la base de production.')
        password = os.environ.get("MEDCARE_E2E_PASSWORD")
        if not password:
            raise CommandError("Définissez MEDCARE_E2E_PASSWORD pour créer les comptes E2E.")
        plan, _ = SubscriptionPlan.objects.get_or_create(
            slug="e2e-plan",
            defaults={"name": "Plan E2E"},
        )
        typ, _ = TypeOrganisme.objects.get_or_create(
            slug="clinique-e2e",
            defaults={"name": "Clinique E2E", "order": 1},
        )

        patient, _ = User.objects.get_or_create(
            username="testpatient",
            defaults={
                "email": "testpatient@e2e.local",
                "user_type": "patient",
            },
        )
        patient.user_type = "patient"
        patient.set_password(password)
        patient.save()
        PatientProfile.objects.get_or_create(user=patient, defaults={"city": "Dakar"})

        prest, _ = User.objects.get_or_create(
            username="polyclinique_de_libe",
            defaults={
                "email": "presta@e2e.local",
                "user_type": "prestataire",
            },
        )
        prest.user_type = "prestataire"
        prest.set_password(password)
        prest.save()

        OrganismeDeSante.objects.update_or_create(
            user=prest,
            defaults={
                "name": "Polyclinique E2E",
                "address": "Dakar",
                "subscription_plan": plan,
                "type_organisme": typ,
                "is_active": True,
                "is_verified": True,
            },
        )

        admin, _ = User.objects.get_or_create(
            username="qa_superadmin",
            defaults={
                "email": "admin@e2e.local",
                "user_type": "admin",
                "is_superuser": True,
                "is_staff": True,
            },
        )
        admin.user_type = "admin"
        admin.is_superuser = True
        admin.is_staff = True
        admin.set_password(password)
        admin.save()

        self.stdout.write(
            self.style.SUCCESS(
                "Comptes E2E prêts (testpatient, polyclinique_de_libe, qa_superadmin)."
            )
        )
