"""
Met à jour les centres de démo en base pour illustrer la diversité :
- prélèvement à domicile (selon le type d'établissement)
- numéros WhatsApp / téléphone distincts par centre
- délais d'offre (PrestataireActe.delai) répartis sur tout le catalogue de choix

Usage :
  python manage.py diversify_demo_centers
  python manage.py diversify_demo_centers --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from healthcare.models import OrganismeDeSante, PrestataireActe


DELAI_CYCLE = [k for k, _ in PrestataireActe.DELAI_CHOICES if k]


def _type_label(org: OrganismeDeSante) -> str:
    t = org.type_organisme
    return (t.name or "").lower() if t else ""


class Command(BaseCommand):
    help = "Diversifie prélèvement domicile, contacts et délais des offres pour la démo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche le plan sans écrire en base.",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        orgs = list(
            OrganismeDeSante.objects.filter(is_active=True)
            .select_related("type_organisme")
            .order_by("pk")
        )
        if not orgs:
            self.stdout.write(self.style.WARNING("Aucun organisme actif."))
            return

        # Profils contacts : suffixes uniques pour wa.me / tests multi-structures
        wa_bases = (
            "221770100001",
            "221770100002",
            "221770100003",
            "221770100004",
            "221770100005",
            "221770100006",
            "221770100007",
            "221770100008",
        )

        org_updates = []
        for i, org in enumerate(orgs):
            tl = _type_label(org)
            # Domicile : labos, hôpitaux, centres de santé ; quelques cliniques ; jamais pharmacie seule
            domicile = (
                "laboratoire" in tl
                or "hôpital" in tl
                or "hopital" in tl
                or "centre de santé" in tl
                or "centre de sante" in tl
                or ("clinique" in tl and i % 3 != 0)
            )
            if "pharmacie" in tl:
                domicile = False

            suffix = wa_bases[i % len(wa_bases)]
            whatsapp = f"+{suffix}"
            # Téléphone fixe différent du mobile pour le fallback « Appeler »
            phone = f"+221 33 8{(i % 9) + 1}0 00 {(i % 90):02d}"

            org.prises_sang_domicile = domicile
            org.whatsapp_number = whatsapp
            org.contact_phone = phone
            org_updates.append(org)

            self.stdout.write(
                f"  [{org.pk}] {org.name[:50]} — domicile={domicile} WA={whatsapp}"
            )

        pas = list(
            PrestataireActe.objects.filter(organisme__is_active=True).select_related(
                "organisme"
            )
        )
        for idx, pa in enumerate(sorted(pas, key=lambda x: (x.organisme_id, x.pk))):
            pa.delai = DELAI_CYCLE[idx % len(DELAI_CYCLE)]

        self.stdout.write(f"\n{len(org_updates)} organismes, {len(pas)} offres à mettre à jour.")

        if dry:
            self.stdout.write(self.style.WARNING("Dry-run : aucune écriture."))
            return

        with transaction.atomic():
            OrganismeDeSante.objects.bulk_update(
                org_updates,
                ["prises_sang_domicile", "whatsapp_number", "contact_phone"],
                batch_size=100,
            )
            PrestataireActe.objects.bulk_update(pas, ["delai"], batch_size=500)

        self.stdout.write(self.style.SUCCESS("OK — diversité appliquée."))
