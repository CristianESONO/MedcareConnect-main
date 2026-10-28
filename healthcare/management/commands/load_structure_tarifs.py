"""
Commande Django pour charger automatiquement les catalogues de tarifs des structures
(Clinique Clémar, CARIM, Laboratoire Bionissa) directement depuis le serveur, sans
avoir besoin de se connecter à chaque compte structure dans l'interface web.

Usage sur le serveur :
    python manage.py load_structure_tarifs
    python manage.py load_structure_tarifs --structure clemar
    python manage.py load_structure_tarifs --structure carim
    python manage.py load_structure_tarifs --structure bionissa
    python manage.py load_structure_tarifs --dry-run
"""
import os
import re
import sys
from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify

import openpyxl

from healthcare.models import (
    OrganismeDeSante,
    TypeOrganisme,
    ActeMedical,
    PrestataireActe,
    ServiceMedical,
    SubscriptionPlan,
)
from healthcare.catalog_excel import (
    ActeCatalogMatcher,
    _normalize_str,
    _parse_price,
    DELAI_NORMALIZATION_MAP,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Charge automatiquement les catalogues de tarifs pour Clémar, CARIM et Bionissa"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            type=str,
            default=None,
            help="Répertoire contenant les fichiers de données (par défaut documents/données a charger)",
        )
        parser.add_argument(
            "--structure",
            type=str,
            choices=["all", "clemar", "carim", "bionissa"],
            default="all",
            help="Structure cible à charger (all, clemar, carim, bionissa)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Exécute l'analyse et la réconciliation sans enregistrer en base",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        target = options["structure"]
        custom_dir = options["dir"]

        self.stdout.write(self.style.MIGRATE_HEADING("=== IMPORT DES TARIFS MEDCARE CONNECT ==="))
        if dry_run:
            self.stdout.write(self.style.WARNING("[SIMULATION] Mode simulation active (--dry-run) : aucune modification en base.\n"))

        # 1. Localisation du dossier de données
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        possible_dirs = [
            custom_dir,
            os.path.join(base_dir, "documents", "donnees_a_charger"),
            os.path.join(base_dir, "documents", "données a charger"),
            os.path.join(base_dir, "documents"),
        ]
        data_dir = None
        for d in possible_dirs:
            if d and os.path.isdir(d):
                data_dir = d
                break

        if not data_dir:
            self.stdout.write(self.style.ERROR("Impossible de localiser le dossier des donnees."))
            return

        self.stdout.write(f"Dossier source : {data_dir}\n")

        # 2. Initialisation du matcher avec le référentiel des actes
        leaf_actes = list(
            ActeMedical.objects.filter(is_active=True).select_related("service_medical_category", "parent_service")
        )
        matcher = ActeCatalogMatcher(leaf_actes)
        self.stdout.write(f"Referentiel medical charge : {len(leaf_actes)} actes de base disponibles.\n")

        # 3. Exécution par structure
        if target in ("all", "clemar"):
            self.process_clemar(data_dir, matcher, dry_run)

        if target in ("all", "carim"):
            self.process_carim(data_dir, matcher, dry_run)

        if target in ("all", "bionissa"):
            self.process_bionissa(data_dir, matcher, dry_run)

        self.stdout.write(self.style.SUCCESS("\n[OK] Operation terminee avec succes !"))

    # ─────────────────────────────────────────────────────────────
    # Utilitaires de gestion des structures & utilisateurs
    # ─────────────────────────────────────────────────────────────
    def get_or_create_structure(
        self,
        name_hint: str,
        display_name: str,
        type_name: str,
        default_phone: str = "+221338000000",
        address: str = "Dakar",
    ) -> OrganismeDeSante:
        """Trouve une structure existante par mot-clé, ou la crée avec son compte utilisateur."""
        org = OrganismeDeSante.objects.filter(name__icontains=name_hint).first()
        if org:
            self.stdout.write(self.style.SUCCESS(f"  [OK] Structure trouvee en BDD : {org.name} (ID: {org.id})"))
            return org

        # Type d'organisme
        t_slug = slugify(type_name)
        type_org = TypeOrganisme.objects.filter(slug=t_slug).first()
        if not type_org:
            type_org = TypeOrganisme.objects.filter(name__icontains=type_name.split()[0]).first()
        if not type_org:
            type_org = TypeOrganisme.objects.create(name=type_name, slug=t_slug, order=0)

        username = slugify(display_name).replace("-", "_")
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                "email": f"{username}@medcare.sn",
                "first_name": display_name,
                "user_type": "prestataire",
                "is_active": True,
            },
        )
        user.set_password("medcare2024")
        user.save()

        default_plan = SubscriptionPlan.objects.filter(is_default=True).first()

        org = OrganismeDeSante.objects.create(
            user=user,
            name=display_name,
            slug=slugify(display_name),
            type_organisme=type_org,
            address=address,
            city="Dakar",
            contact_phone=default_phone,
            is_active=True,
            is_verified=True,
            subscription_plan=default_plan,
        )
        self.stdout.write(self.style.SUCCESS(f"  [+] Nouvelle structure creee en BDD : {org.name} (Utilisateur: {username})"))
        return org

    def _save_prestataire_acte(
        self,
        org: OrganismeDeSante,
        acte: ActeMedical,
        price: Decimal,
        price_ipm: Decimal | None = None,
        price_assurance: Decimal | None = None,
        delai: str = "",
        prereq: str = "",
        dry_run: bool = False,
    ) -> tuple[bool, bool]:
        """Enregistre ou met à jour l'offre de la structure."""
        if dry_run:
            return True, False

        pa, created = PrestataireActe.objects.update_or_create(
            organisme=org,
            acte=acte,
            defaults={
                "price": price,
                "price_ipm": price_ipm,
                "price_assurance": price_assurance,
                "coverage_status_ipm": "covered" if price_ipm is not None else "to_confirm",
                "coverage_status_assurance": "covered" if price_assurance is not None else "to_confirm",
                "delai": delai or "",
                "is_available": True,
                "rdv_prerequisites": prereq or "",
            },
        )
        return True, created

    def _get_or_create_custom_acte(self, name: str, category_slug: str, reference_price: Decimal | None = None) -> ActeMedical:
        """Cree un acte medical specifique si aucun acte correspondant n'est au referentiel."""
        import uuid
        clean_name = name.strip()
        existing = ActeMedical.objects.filter(name__iexact=clean_name).first()
        if existing:
            return existing

        category = ServiceMedical.objects.filter(slug=category_slug).first()
        if not category:
            category = ServiceMedical.objects.filter(is_active=True).first() or ServiceMedical.objects.first()

        code = f"SPE-{uuid.uuid4().hex[:8].upper()}"
        acte = ActeMedical.objects.create(
            name=clean_name,
            code=code,
            service_medical_category=category,
            reference_price=reference_price,
            is_active=True,
        )
        return acte

    # ─────────────────────────────────────────────────────────────
    # TRAITEMENT CLEMAR
    # ─────────────────────────────────────────────────────────────
    def process_clemar(self, data_dir: str, matcher: ActeCatalogMatcher, dry_run: bool):
        self.stdout.write(self.style.MIGRATE_LABEL("\n>> Traitement : Clinique Clemar"))
        org = self.get_or_create_structure("clemar", "Clinique Clemar", "Clinique privee", "+221338240000")

        f_consult = self._find_file(data_dir, ["Tarifs Consultations Clemar.xlsx", "Consultations Clemar"])
        f_imagerie = self._find_file(data_dir, ["Tarifs Imagerie Clemar.xlsx", "Imagerie Clemar"])
        f_labo = self._find_file(data_dir, ["Tarifs Labo Clémar.xlsx", "Tarifs Labo Clemar.xlsx", "Labo Clemar"])

        matched_total = 0
        created_total = 0

        # A. Consultations
        if f_consult:
            self.stdout.write(f"  [FICHIER] {os.path.basename(f_consult)}")
            wb = openpyxl.load_workbook(f_consult, data_only=True)
            ws = wb.active
            for row in ws.iter_rows(values_only=True):
                if not row or len(row) < 2 or not row[0]:
                    continue
                label = str(row[0]).strip()
                if any(k in label.lower() for k in ("consultation", "tarif", "clinique")):
                    if "sau" not in label.lower() and "spécialiste" not in label.lower() and "généraliste" not in label.lower():
                        continue
                price_val, _ = _parse_price(row[1])
                if price_val and price_val > 0:
                    target_acte, method = matcher.match(raw_name=label)
                    if not target_acte:
                        target_acte = self._get_or_create_custom_acte(label, "consultations-medicales", price_val)
                    ok, is_new = self._save_prestataire_acte(org, target_acte, price_val, delai="immediat", dry_run=dry_run)
                    matched_total += 1
                    if is_new:
                        created_total += 1

        # B. Imagerie
        if f_imagerie:
            self.stdout.write(f"  [FICHIER] {os.path.basename(f_imagerie)}")
            wb = openpyxl.load_workbook(f_imagerie, data_only=True)
            ws = wb.active
            for row in ws.iter_rows(values_only=True):
                if not row or len(row) < 2 or not row[0]:
                    continue
                label = str(row[0]).strip()
                if label.lower() in ("examen", "tarif (fcfa)", "clinique clemar – tarifs de l'imagerie", "échographie"):
                    continue
                price_val, _ = _parse_price(row[1])
                if price_val and price_val > 0:
                    target_acte, method = matcher.match(raw_name=label)
                    if not target_acte:
                        target_acte = self._get_or_create_custom_acte(label, "imagerie-medicale", price_val)
                    ok, is_new = self._save_prestataire_acte(org, target_acte, price_val, delai="1h", dry_run=dry_run)
                    matched_total += 1
                    if is_new:
                        created_total += 1

        # C. Laboratoire (avec Comptant, IPM et Assurances !)
        if f_labo:
            self.stdout.write(f"  [FICHIER] {os.path.basename(f_labo)}")
            wb = openpyxl.load_workbook(f_labo, data_only=True)
            ws = wb.active
            # Header: DESIGNATION | PRIX UNITAIRE | SANS COUVERTURE | IPM | ASSURANCES
            for row in ws.iter_rows(values_only=True):
                if not row or not row[0]:
                    continue
                label = str(row[0]).strip()
                if label.upper() in ("DESIGNATION", "ACTE", "ANALYSE"):
                    continue
                # Prix comptant
                price_val, _ = _parse_price(row[2] if len(row) > 2 else None)
                # Prix IPM
                price_ipm, _ = _parse_price(row[3] if len(row) > 3 else None)
                # Prix Assurance
                price_assur, _ = _parse_price(row[4] if len(row) > 4 else None)

                effective_price = price_val or price_ipm or price_assur
                if effective_price and effective_price > 0:
                    code_cotation = str(row[1]).strip() if len(row) > 1 and row[1] else ""
                    target_acte, method = matcher.match(raw_name=label, raw_code=code_cotation)
                    if not target_acte:
                        target_acte = self._get_or_create_custom_acte(label, "laboratoire-biologie", effective_price)
                    ok, is_new = self._save_prestataire_acte(
                        org,
                        target_acte,
                        effective_price,
                        price_ipm=price_ipm,
                        price_assurance=price_assur,
                        delai="24h",
                        dry_run=dry_run,
                    )
                    matched_total += 1
                    if is_new:
                        created_total += 1

        self.stdout.write(self.style.SUCCESS(f"  => Clemar : {matched_total} actes traites ({created_total} nouvelles offres enregistrees)."))

    # ─────────────────────────────────────────────────────────────
    # TRAITEMENT CARIM (Imagerie)
    # ─────────────────────────────────────────────────────────────
    def process_carim(self, data_dir: str, matcher: ActeCatalogMatcher, dry_run: bool):
        self.stdout.write(self.style.MIGRATE_LABEL("\n>> Traitement : CARIM"))
        org = self.get_or_create_structure("carim", "CARIM - Centre d'Imagerie", "Centre d'imagerie medicale", "+221338250000")

        f_carim_xlsx = self._find_file(data_dir, ["Tarifs et actes CARIM.xlsx"])
        f_carim_ods = self._find_file(data_dir, ["Tarifs et actes CARIM.ods"])

        rows_to_process = []
        if f_carim_xlsx:
            self.stdout.write(f"  [FICHIER] {os.path.basename(f_carim_xlsx)}")
            wb = openpyxl.load_workbook(f_carim_xlsx, data_only=True)
            ws = wb.active
            for r in ws.iter_rows(values_only=True):
                if r and len(r) >= 4 and r[1] and r[3]:
                    if str(r[1]).strip().lower() not in ("nom de l'acte", "examen"):
                        rows_to_process.append((str(r[1]).strip(), r[3]))
        elif f_carim_ods:
            self.stdout.write(f"  [FICHIER ODS] {os.path.basename(f_carim_ods)}")
            rows_to_process = self._read_ods_carim(f_carim_ods)

        matched_total = 0
        created_total = 0
        for label, price_raw in rows_to_process:
            price_val, _ = _parse_price(price_raw)
            if price_val and price_val > 0:
                target_acte, method = matcher.match(raw_name=label)
                if not target_acte:
                    target_acte = self._get_or_create_custom_acte(label, "imagerie-medicale", price_val)
                ok, is_new = self._save_prestataire_acte(org, target_acte, price_val, delai="2h", dry_run=dry_run)
                matched_total += 1
                if is_new:
                    created_total += 1

        self.stdout.write(self.style.SUCCESS(f"  => CARIM : {matched_total} actes d'imagerie traites ({created_total} nouvelles offres enregistrees)."))

    # ─────────────────────────────────────────────────────────────
    # TRAITEMENT BIONISSA (Biologie)
    # ─────────────────────────────────────────────────────────────
    def process_bionissa(self, data_dir: str, matcher: ActeCatalogMatcher, dry_run: bool):
        self.stdout.write(self.style.MIGRATE_LABEL("\n>> Traitement : Laboratoire Bionissa"))
        org = self.get_or_create_structure("bionissa", "Laboratoire Bionissa", "Laboratoire d'analyses medicales", "+221338260000")

        f_bionissa = self._find_file(data_dir, ["Tarifs Labo Bionissa.xlsx", "Labo Bionissa"])
        if not f_bionissa:
            self.stdout.write(self.style.WARNING("  [ATTENTION] Fichier Bionissa introuvable."))
            return

        self.stdout.write(f"  [FICHIER] {os.path.basename(f_bionissa)}")
        wb = openpyxl.load_workbook(f_bionissa, data_only=True)
        ws = wb.active

        # Entêtes identifiés :
        # Col 3 : Paramètres (nom acte)
        # Col 10 : Code (ex: B10, B40...)
        # Col 11 : Prix
        # Col 12 : Conditions de prélèvement (Consignes RDV / Prérequis)
        # Col 13 : Tube
        # Col 16 : Délai
        matched_total = 0
        created_total = 0

        for row_idx in range(5, ws.max_row + 1):
            param = ws.cell(row_idx, 3).value
            if not param or not str(param).strip():
                # Vérifier si en col 1
                param = ws.cell(row_idx, 1).value
                if not param or not str(param).strip():
                    continue

            label = str(param).strip()
            if label.upper() in ("PARAMETRES", "PARAMÈTRES", "MARQUEURS", "DESIGNATION"):
                continue

            price_raw = ws.cell(row_idx, 11).value
            price_val, _ = _parse_price(price_raw)
            if not price_val or price_val <= 0:
                continue

            code_raw = str(ws.cell(row_idx, 10).value or "").strip()
            cond_prelev = str(ws.cell(row_idx, 12).value or "").strip()
            tube = str(ws.cell(row_idx, 13).value or "").strip()
            delai_raw = str(ws.cell(row_idx, 16).value or "").strip()

            prereq_parts = []
            if cond_prelev and cond_prelev.upper() != "N/A":
                prereq_parts.append(cond_prelev)
            if tube and tube.upper() != "N/A":
                prereq_parts.append(f"Tube: {tube}")
            prereq_str = " - ".join(prereq_parts)

            # Normaliser délai
            delai_norm = "24h"
            if delai_raw:
                delai_norm = DELAI_NORMALIZATION_MAP.get(delai_raw.upper().strip(), "24h")

            target_acte, method = matcher.match(raw_name=label, raw_code=code_raw)
            if not target_acte:
                target_acte = self._get_or_create_custom_acte(label, "laboratoire-biologie", price_val)

            ok, is_new = self._save_prestataire_acte(
                org,
                target_acte,
                price_val,
                delai=delai_norm,
                prereq=prereq_str,
                dry_run=dry_run,
            )
            matched_total += 1
            if is_new:
                created_total += 1

        self.stdout.write(self.style.SUCCESS(f"  => Bionissa : {matched_total} analyses de biologie traitees ({created_total} nouvelles offres enregistrees)."))

    # ─────────────────────────────────────────────────────────────
    # Lecteur XML / Zip natif pour ODS
    # ─────────────────────────────────────────────────────────────
    def _read_ods_carim(self, ods_path: str) -> list[tuple[str, Any]]:
        import zipfile
        import xml.etree.ElementTree as ET

        results = []
        try:
            with zipfile.ZipFile(ods_path, "r") as z:
                content = z.read("content.xml")
                root = ET.fromstring(content)
                tables = root.findall(".//{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table")
                current_category = "IMAGERIE"
                for t in tables:
                    for tr in t.findall(".//{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table-row"):
                        cells = []
                        for cell in tr.findall(".//{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table-cell"):
                            p = cell.findall(".//{urn:oasis:names:tc:opendocument:xmlns:text:1.0}p")
                            txt = " ".join("".join(el.itertext()) for el in p).strip()
                            repeat = int(cell.attrib.get("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}number-columns-repeated", 1))
                            if repeat > 20:
                                continue
                            cells.append(txt)
                        cleaned = [c for c in cells if c]
                        if not cleaned:
                            continue
                        first = cleaned[0].strip()
                        if len(cleaned) >= 2 and any(k in cleaned[-1].upper() for k in ("PRIX", "TARIF")):
                            current_category = first
                            continue
                        elif len(cleaned) == 1 and first.upper() in ["ECHOGRAPHIES", "SCANNER", "IRM", "EXAMENS SPECIAUX", "RADIOGRAPHIES"]:
                            current_category = first
                            continue
                        if len(cleaned) >= 2:
                            name = cleaned[0] if len(cleaned) == 2 else (cleaned[0] + " " + cleaned[1])
                            price = cleaned[-1]
                            cat_upper = current_category.upper()
                            if "ECHOGRAPHIE" in cat_upper and not name.upper().startswith("ECHOGRAPHIE"):
                                name = f"Échographie {name}"
                            elif "SCANNER" in cat_upper and not name.upper().startswith("SCANNER") and not name.upper().startswith("URO") and not name.upper().startswith("ANGIO"):
                                name = f"Scanner {name}"
                            elif "IRM" in cat_upper and not name.upper().startswith("IRM"):
                                name = f"IRM {name}"
                            elif "RADIOGRAPHIE" in cat_upper and not name.upper().startswith("RADIOGRAPHIE") and not name.upper().startswith("RAIDOGRAPHIE"):
                                name = f"Radiographie {name}"
                            results.append((name, price))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erreur lecture ODS : {e}"))
        return results

    # ─────────────────────────────────────────────────────────────
    # Détection souple des fichiers
    # ─────────────────────────────────────────────────────────────
    def _find_file(self, data_dir: str, candidates: list[str]) -> str | None:
        """Trouve un fichier parmi une liste de noms possibles, insensible à la casse."""
        if not os.path.isdir(data_dir):
            return None
        all_files = os.listdir(data_dir)
        for cand in candidates:
            cand_norm = _normalize_str(cand)
            for f in all_files:
                if _normalize_str(f) == cand_norm or cand.lower() in f.lower():
                    return os.path.join(data_dir, f)
        return None
