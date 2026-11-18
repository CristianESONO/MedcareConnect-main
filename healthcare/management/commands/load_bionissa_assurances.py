"""
Commande Django pour charger les conventions (Assurances et IPM)
spécifiques au Laboratoire BIONISSA sur le serveur.

Usage sur le serveur :
    python manage.py load_bionissa_assurances --dry-run
    python manage.py load_bionissa_assurances
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from healthcare.models import OrganismeDeSante, Assurance, PriseEnChargeAssurance


# Liste des 46 conventions validées pour Bionissa
# Format : (Nom officiel affiché, Segment, [Mots-clés / Alias de recherche])
BIONISSA_CONVENTIONS = [
    # ── Assurances privées & Courtage tiers-payant (12) ──
    ("AXA Assurances", Assurance.Segment.PRIVEE_IARD, ["axa", "axa ass"]),
    ("SANLAM Assurances", Assurance.Segment.PRIVEE_IARD, ["sanlam", "sanlam ass", "allianz / sanlam"]),
    ("SUNU Assurances", Assurance.Segment.PRIVEE_IARD, ["sunu", "sunu ass"]),
    ("NSIA Assurances", Assurance.Segment.PRIVEE_IARD, ["nsia", "nsia ass"]),
    ("WAFA Assurance", Assurance.Segment.PRIVEE_IARD, ["wafa", "wafa ass"]),
    ("AMSA Assurances", Assurance.Segment.PRIVEE_IARD, ["amsa", "amsa ass"]),
    ("CNART Assurances", Assurance.Segment.PRIVEE_IARD, ["cnart", "cnart ass"]),
    ("La Prévoyance Assurances (PA)", Assurance.Segment.PRIVEE_IARD, ["pa ass", "prévoyance assurances", "prevoyance assurances"]),
    ("ASCOMA Assurances", Assurance.Segment.PRIVEE_IARD, ["ascoma"]),
    ("OLEA Assurances", Assurance.Segment.PRIVEE_IARD, ["olea", "olea ass"]),
    ("Willis Towers Watson", Assurance.Segment.PRIVEE_IARD, ["willis towers watson", "wtw"]),
    ("WILLIS", Assurance.Segment.PRIVEE_IARD, ["willis"]),

    # ── Assurances santé digitales (1) ──
    ("Reliance Health", Assurance.Segment.DIGITALE, ["reliance", "reliance health"]),

    # ── Régimes publics / institutionnels (1) ──
    ("Caisse de Sécurité Sociale (CSS)", Assurance.Segment.REGIME_PUBLIC, ["css", "caisse de sécurité sociale", "caisse de securite sociale"]),

    # ── IPM, Mutuelles & Entreprises conventionnées (32) ──
    ("IPM SONATEL", Assurance.Segment.MUTUELLE, ["sonatel", "imp sonatel", "ipm sonatel"]),
    ("IPM ICS Mboro", Assurance.Segment.MUTUELLE, ["ics mboro", "ics"]),
    ("IPM Phosphate de Thiès", Assurance.Segment.MUTUELLE, ["phosphate de thiès", "phosphate de thies", "phosphates"]),
    ("IPM SYPAOA", Assurance.Segment.MUTUELLE, ["sypaoa"]),
    ("IPM C2K Staffing", Assurance.Segment.MUTUELLE, ["c2k", "c2k staffing"]),
    ("IPM STRH", Assurance.Segment.MUTUELLE, ["strh"]),
    ("IPM CMS (Crédit Mutuel du Sénégal)", Assurance.Segment.MUTUELLE, ["cms", "crédit mutuel du sénégal", "credit mutuel"]),
    ("IPM ONAS", Assurance.Segment.MUTUELLE, ["onas"]),
    ("IPM FILFILI", Assurance.Segment.MUTUELLE, ["filfili"]),
    ("IPM ZI Sentenac", Assurance.Segment.MUTUELLE, ["zi sentenac", "sentenac"]),
    ("IPM TOSTAN", Assurance.Segment.MUTUELLE, ["tostan"]),
    ("IPM SFD", Assurance.Segment.MUTUELLE, ["sfd"]),
    ("IPM Bénédiction", Assurance.Segment.MUTUELLE, ["bénédiction", "benediction"]),
    ("IPM ODEC", Assurance.Segment.MUTUELLE, ["odec"]),
    ("IPM MSE", Assurance.Segment.MUTUELLE, ["mse"]),
    ("IPM Groupe ISC", Assurance.Segment.MUTUELLE, ["groupe isc", "isc"]),
    ("IPM ISRA", Assurance.Segment.MUTUELLE, ["isra"]),
    ("IPM ACORP", Assurance.Segment.MUTUELLE, ["acorp"]),
    ("IPM Petite Côte", Assurance.Segment.MUTUELLE, ["petite côte", "petite cote"]),
    ("IPM BCEAO Kaolack", Assurance.Segment.MUTUELLE, ["bceao", "bceao kaolack"]),
    ("IPM KEDA Ceramics", Assurance.Segment.MUTUELLE, ["keda", "keda ceramics"]),
    ("IPM AGEEMAC", Assurance.Segment.MUTUELLE, ["ageemac"]),
    ("IPM SAGAM", Assurance.Segment.MUTUELLE, ["sagam"]),
    ("IPM Université Amadou Mokhtar Mbow", Assurance.Segment.MUTUELLE, ["université amadou mokhtar mbow", "universite amadou mokhtar mbow", "uam"]),
    ("IPM Polytechnique de Thiès", Assurance.Segment.MUTUELLE, ["polytechnique de thiès", "polytechnique de thies", "ept"]),
    ("IPM TRANSVI", Assurance.Segment.MUTUELLE, ["transvi"]),
    ("IPM Talix", Assurance.Segment.MUTUELLE, ["talix", "ipm talix"]),
    ("IPM Jean Lèvre", Assurance.Segment.MUTUELLE, ["jean lèvre", "jean levre"]),
    ("IPM GGA", Assurance.Segment.MUTUELLE, ["ipm gga", "gga"]),
    ("IPM CDE", Assurance.Segment.MUTUELLE, ["cde"]),
    ("IPM SOBAO", Assurance.Segment.MUTUELLE, ["sobao"]),
]

# Explicitly excluded / non prises en charge
EXCLUDED_NAMES = [
    "RIDWAN",
    "ASKIA",
    "IMP PROFIL",
]


class Command(BaseCommand):
    help = "Charge la liste des IPM et Assurances acceptées pour le Laboratoire BIONISSA"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simule l'association sans modifier la base de données",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        self.stdout.write(self.style.MIGRATE_HEADING("=== IMPORT DES CONVENTIONS & ASSURANCES : BIONISSA ==="))
        if dry_run:
            self.stdout.write(self.style.WARNING("[SIMULATION] Mode simulation active (--dry-run) : aucune modification en base.\n"))

        # 1. Trouver le Laboratoire Bionissa
        org = OrganismeDeSante.objects.filter(name__icontains="bionissa").first()
        if not org:
            self.stdout.write(self.style.ERROR("Erreur : Impossible de trouver le Laboratoire Bionissa dans la base de donnees."))
            return

        self.stdout.write(self.style.SUCCESS(f"[OK] Structure trouvee : {org.name} (ID: {org.id})\n"))

        # 2. Traiter chaque convention
        attached_count = 0
        created_assurances = 0

        for name, segment, aliases in BIONISSA_CONVENTIONS:
            # Chercher si l'assurance existe déjà
            assurance = None
            # Recherche exacte par nom
            assurance = Assurance.objects.filter(name__iexact=name).first()
            if not assurance:
                # Recherche par slug
                assurance = Assurance.objects.filter(slug=slugify(name)).first()
            if not assurance:
                # Recherche par alias
                for alias in aliases:
                    found = Assurance.objects.filter(name__icontains=alias).first()
                    if found:
                        assurance = found
                        break

            # Si introuvable, créer l'assurance
            if not assurance:
                if not dry_run:
                    assurance = Assurance.objects.create(
                        name=name,
                        slug=slugify(name),
                        segment=segment,
                        description=f"Convention conventionnee / Tiers-payant : {name}",
                        is_active=True,
                    )
                created_assurances += 1
                self.stdout.write(f"  [+] Nouvelle assurance creee : {name} (Segment: {segment})")
            else:
                self.stdout.write(f"  [OK] Assurance existante : {assurance.name}")

            # Lier l'assurance à Bionissa
            if not dry_run and assurance:
                PriseEnChargeAssurance.objects.update_or_create(
                    organisme=org,
                    assurance=assurance,
                    defaults={"is_active": True},
                )
            attached_count += 1

        # 3. Vérifier et détacher les exclusions explicites si présentes
        detached_count = 0
        for excl in EXCLUDED_NAMES:
            excl_assurances = Assurance.objects.filter(name__icontains=excl)
            for ea in excl_assurances:
                if not dry_run:
                    deleted, _ = PriseEnChargeAssurance.objects.filter(organisme=org, assurance=ea).delete()
                    if deleted:
                        detached_count += 1
                        self.stdout.write(self.style.WARNING(f"  [-] Retrait convention exclue : {ea.name}"))

        # 4. Bilan final
        self.stdout.write(self.style.SUCCESS(f"\n=== BILAN CONVENTIONS BIONISSA ==="))
        self.stdout.write(f"- Structure : {org.name}")
        self.stdout.write(f"- Conventions validees et rattachees : {attached_count} / {len(BIONISSA_CONVENTIONS)}")
        self.stdout.write(f"- Nouvelles assurances creees en BDD : {created_assurances}")
        if detached_count > 0:
            self.stdout.write(f"- Conventions exclues retirees : {detached_count}")
        self.stdout.write(self.style.SUCCESS("[OK] Operation terminee avec succes !"))
