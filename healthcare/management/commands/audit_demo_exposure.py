from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from cart.models import DevisPart
from messaging.models import Conversation

MOTS = ("demo", "test", "smoke")


def est_test(u):
    return u.email.lower().endswith("@test.com") or any(m in u.username.lower() for m in MOTS)


class Command(BaseCommand):
    help = "Signale les fiches de démo exposées et les conversations réelles chez des comptes de test."

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError(f"Base inattendue : {connection.vendor}")
        Org = DevisPart._meta.get_field("organisme").related_model
        erreurs, avertissements = [], []
        for o in Org.objects.filter(is_active=True).select_related("user"):
            if o.user and est_test(o.user):
                erreurs.append(f"structure ACTIVE {o.pk} {o.name} détenue par le compte de test {o.user.username}")
            if o.contact_phone == "+221770000000":
                avertissements.append(f"structure active {o.pk} {o.name} avec le numéro de démo")
        for c in Conversation.objects.select_related("patient", "prestataire"):
            if est_test(c.prestataire) and not est_test(c.patient):
                erreurs.append(f"conversation {c.pk} : patient réel {c.patient.username} chez le compte de test {c.prestataire.username}")
        for a in avertissements:
            self.stdout.write("AVERTISSEMENT " + a)
        for e in erreurs:
            self.stdout.write("ERREUR " + e)
        if erreurs:
            raise CommandError(f"{len(erreurs)} problème(s) détecté(s)")
        self.stdout.write("OK : aucune exposition détectée")
