"""
Commande de gestion pour vérifier l'exactitude des adresses et coordonnées des structures de santé.
Conforme aux spécifications MedCare Connect :
- --dry-run par défaut (mode audit/simulation sans modification en base).
- --apply pour corriger automatiquement les régions manquantes des structures de Dakar.
- Liste les structures sans coordonnées GPS.
- Liste les structures hors zone Dakar (coordonnées en dehors de la région de Dakar).
- Liste les structures sans région rattachée.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from healthcare.models import OrganismeDeSante, Region


# Bounding box approximative de la région de Dakar (presqu'île + banlieue jusqu'à Diamniadio/Rufisque)
DAKAR_LAT_MIN = 14.50
DAKAR_LAT_MAX = 14.92
DAKAR_LNG_MIN = -17.60
DAKAR_LNG_MAX = -17.10


class Command(BaseCommand):
    help = "Vérifie les adresses, coordonnées GPS et régions des structures de santé (audit)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=True,
            help="Mode simulation par défaut : affiche l'audit sans modifier la base de données.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            default=False,
            help="Applique la correction des régions manquantes (rattachement à Dakar pour les structures de Dakar).",
        )

    def handle(self, *args, **options):
        dry_run = not options.get("apply")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"=== AUDIT DES ADRESSES ET COORDONNÉES DES STRUCTURES ({'SIMULATION / DRY-RUN' if dry_run else 'APPLICATION RÉELLE'}) ==="
            )
        )

        orgs = list(OrganismeDeSante.objects.select_related("region", "type_organisme").order_by("name"))
        total = len(orgs)

        sans_coords = []
        hors_dakar = []
        sans_region = []
        coords_valides = []

        for org in orgs:
            lat = org.latitude
            lng = org.longitude

            # Vérification coordonnées
            if lat is None or lng is None or (lat == 0 and lng == 0):
                sans_coords.append(org)
            else:
                # Vérifier si déclaré à Dakar mais avec des coordonnées en dehors de Dakar
                is_dakar_declared = (
                    (org.city and "dakar" in org.city.lower())
                    or (org.region and "dakar" in org.region.name.lower())
                    or (org.address and "dakar" in org.address.lower())
                )
                if is_dakar_declared:
                    if not (DAKAR_LAT_MIN <= lat <= DAKAR_LAT_MAX and DAKAR_LNG_MIN <= lng <= DAKAR_LNG_MAX):
                        hors_dakar.append((org, lat, lng))
                    else:
                        coords_valides.append(org)
                else:
                    coords_valides.append(org)

            # Vérification région
            if org.region is None:
                sans_region.append(org)

        # Rapport
        self.stdout.write(f"\nTotal des structures inspectées : {total}")
        self.stdout.write(self.style.SUCCESS(f"Structures avec coordonnées GPS valides : {len(coords_valides)}"))

        # 1. Structures sans coordonnées
        if sans_coords:
            self.stdout.write(self.style.WARNING(f"\n[!] STRUCTURES SANS COORDONNÉES GPS ({len(sans_coords)}) :"))
            for org in sans_coords:
                quartier_str = f" ({org.quartier})" if org.quartier else ""
                self.stdout.write(f"  - [{org.pk}] {org.name} — Ville : {org.city or 'N/A'}{quartier_str} — Adresse : {org.address or 'N/A'}")
        else:
            self.stdout.write(self.style.SUCCESS("\n[✓] Aucune structure sans coordonnées GPS."))

        # 2. Structures hors zone Dakar
        if hors_dakar:
            self.stdout.write(self.style.ERROR(f"\n[!] STRUCTURES DAKAROISES HORS ZONE DAKAR ({len(hors_dakar)}) :"))
            for org, lat, lng in hors_dakar:
                self.stdout.write(f"  - [{org.pk}] {org.name} — Coordonnées actuelles : ({lat}, {lng})")
        else:
            self.stdout.write(self.style.SUCCESS("\n[✓] Aucune structure dakaroise avec des coordonnées hors zone."))

        # 3. Structures sans région rattachée
        if sans_region:
            self.stdout.write(self.style.WARNING(f"\n[!] STRUCTURES SANS RÉGION RATTACHÉE ({len(sans_region)}) :"))
            for org in sans_region:
                self.stdout.write(f"  - [{org.pk}] {org.name} — Ville : {org.city or 'N/A'} — Quartier : {org.quartier or 'N/A'}")
        else:
            self.stdout.write(self.style.SUCCESS("\n[✓] Toutes les structures ont une région rattachée."))

        # Action d'application si demandée
        if not dry_run and sans_region:
            reg_dakar = Region.objects.filter(slug__iexact="dakar").first()
            if reg_dakar:
                fixed_count = 0
                with transaction.atomic():
                    for org in sans_region:
                        if org.city and "dakar" in org.city.lower():
                            org.region = reg_dakar
                            org.save(update_fields=["region"])
                            fixed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"\n[APPLY] {fixed_count} structure(s) de Dakar rattachée(s) avec succès à la région Dakar.")
                )
        elif dry_run and sans_region:
            self.stdout.write(
                self.style.NOTICE("\n(Info : pour rattacher automatiquement les structures de Dakar sans région, exécutez avec --apply)")
            )
