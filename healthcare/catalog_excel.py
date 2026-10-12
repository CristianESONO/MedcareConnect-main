"""
Import et Export du catalogue d'actes pour les prestataires de santé.
Prend en charge les formats Excel (.xlsx, .xls) et CSV (.csv).
"""
from __future__ import annotations

import csv
import difflib
import io
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.utils.text import slugify

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from healthcare.models import ActeMedical, OrganismeDeSante, PrestataireActe
from healthcare.prestataire_catalogue import (
    applicable_pilier_slugs,
    official_pilier_services,
    prestataire_leaf_actes_queryset,
)


DELAI_NORMALIZATION_MAP = {
    "IMMEDIAT": "immediat",
    "IMMEDIATE": "immediat",
    "URGENCE": "immediat",
    "URGENT": "immediat",
    "URGENTE": "immediat",
    "EN URGENCE": "immediat",
    "SANS DELAI": "immediat",
    "IMMEDIAT URGENCE": "immediat",
    "30MIN": "30min",
    "30 MIN": "30min",
    "MOINS DE 30 MIN": "30min",
    "MOINS DE 30MIN": "30min",
    "1H": "1h",
    "1 H": "1h",
    "1 HEURE": "1h",
    "MOINS D 1 HEURE": "1h",
    "MOINS D 1H": "1h",
    "2H": "2h",
    "2 H": "2h",
    "2 HEURES": "2h",
    "MOINS DE 2 HEURES": "2h",
    "MOINS DE 2H": "2h",
    "4H": "4h",
    "4 H": "4h",
    "JOURNEE": "4h",
    "DANS LA JOURNEE": "4h",
    "24H": "24h",
    "24 H": "24h",
    "SOUS 24 H": "24h",
    "SOUS 24H": "24h",
    "48H": "48h",
    "48 H": "48h",
    "SOUS 48 H": "48h",
    "SOUS 48H": "48h",
    "72H": "72h",
    "72 H": "72h",
    "SOUS 72 H": "72h",
    "SOUS 72H": "72h",
    "7J": "7j",
    "7 J": "7j",
    "7 JOURS": "7j",
    "SOUS 7 JOURS": "7j",
    "SOUS 7J": "7j",
    "RDV": "rdv",
    "SUR RDV": "rdv",
    "SUR RENDEZ VOUS": "rdv",
    "RENDEZ VOUS": "rdv",
}


def _normalize_str(s: str | None) -> str:
    """
    Normalisation canonique pour l'harmonisation médicale :
    - Décomposition Unicode (suppression totale des accents : é -> E, à -> A...)
    - Passage systématique en MAJUSCULES
    - Élimination des points dans les acronymes (ex: N.F.S. -> NFS, E.C.G. -> ECG, T.D.M. -> TDM)
    - Remplacement des caractères spéciaux et ponctuations par des espaces
    - Suppression des espaces superflus et insécables
    """
    if not s:
        return ""
    text = unicodedata.normalize("NFKD", str(s))
    text = "".join(c for c in text if not unicodedata.combining(c)).upper()
    # Supprimer les points au sein des sigles (ex: N.F.S. -> NFS, E.C.B.U. -> ECBU)
    text = re.sub(r"(?<=\b[A-Z0-9])\.(?=[A-Z0-9]\b)", "", text)
    # Remplacer les caractères non-alphanumériques par des espaces
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


FRENCH_STOP_WORDS = {
    "DE", "DU", "DES", "LA", "LE", "LES", "D", "L", "A", "AU", "AUX",
    "ET", "EN", "POUR", "PAR", "SUR", "SOUS", "AVEC", "SANS", "UN", "UNE"
}


def _extract_significant_tokens(norm_text: str) -> set[str]:
    """Extrait les tokens significatifs d'un nom d'acte (sans mots vides)."""
    words = norm_text.split()
    return {w for w in words if w not in FRENCH_STOP_WORDS and len(w) > 1}


# Dictionnaire étendu des synonymes et équivalences médicales (Sénégal / francophone)
MEDICAL_SYNONYMS: dict[str, list[str]] = {
    # ── Biologie médicale ──
    "NFS / HEMOGRAMME": [
        "NFS", "HEMOGRAMME", "NUMERATION FORMULE SANGUINE", "NFS COMPLET",
        "HEMOGRAMME NFS", "FROTTIS SANGUIN ET NUMERATION", "NUMERATION SANGUINE",
    ],
    "VS": ["VITESSE DE SEDIMENTATION", "VS VITESSE DE SEDIMENTATION", "VITESSE SEDIMENTATION"],
    "CRP": ["PROTEINE C REACTIVE", "CRP ULTRA SENSIBLE", "CRP QUANTITATIVE", "C REACTIVE PROTEINE"],
    "TP / INR": [
        "TP", "INR", "TAUX DE PROTHROMBINE", "TEMPS DE QUICK", "TP ET INR", "TP TAUX DE PROTHROMBINE",
    ],
    "TCA": [
        "TEMPS DE CEPHALINE ACTIVEE", "TCK", "TEMPS DE CEPHALINE KAOLIN",
    ],
    "FIBRINOGENE": ["FIBRINOGENE SANGUIN", "DOSAGE DU FIBRINOGENE", "FIBRINEMIE"],
    "D-DIMERES": ["D DIMERES", "DDIMERES", "DOSAGE D DIMERES"],
    "TEMPS DE THROMBINE (TT)": ["TEMPS DE THROMBINE", "TT"],
    "FROTTIS SANGUIN": ["FROTTIS", "FROTTIS SANGUIN GOUTTE EPAISSE", "FNS"],
    "GROUPE ABO/RHESUS": [
        "GROUPE SANGUIN", "GROUPE ABO", "GROUPE RHESUS", "GROUPAGE SANGUIN",
        "GROUPE RH", "GROUPE SANGUIN RHESUS", "ABO RHESUS",
    ],
    "RAI": ["RECHERCHE AGGLUTININES IRREGULIERES", "AGGLUTININES IRREGULIERES"],
    "ELECTROPHORESE DE L'HEMOGLOBINE": [
        "ELECTROPHORESE HEMOGLOBINE", "ELECTROPHORESE HB", "ELECTROPHORESE DES HEMOGLOBINES",
    ],
    "GLYCEMIE A JEUN": [
        "GLYCEMIE", "DOSAGE GLYCEMIE", "GLYCEMIE A JEUN VEINEUSE", "DOSAGE DU SUCRE", "SUCRE DANS LE SANG",
    ],
    "HBA1C": ["HEMOGLOBINE GLYQUEE", "HEMOGLOBINE A1C", "DOSAGE HBA1C"],
    "UREE SANGUINE": ["UREE", "DOSAGE UREE", "UREE PLASMATIQUE", "AZOTEMIE", "DOSAGE AZOTEMIE"],
    "CREATININEMIE": ["CREATININE", "DOSAGE CREATININE", "CREATININE SANGUINE", "CLAIRANCE CREATININE"],
    "NATREMIE": ["SODIUM", "DOSAGE SODIUM", "ION SODIUM"],
    "KALIEMIE": ["POTASSIUM", "DOSAGE POTASSIUM", "ION POTASSIUM"],
    "CHLOREMIE": ["CHLORE", "DOSAGE CHLORE", "ION CHLORE"],
    "CALCEMIE": ["CALCIUM", "DOSAGE CALCIUM", "CALCIUM SANGUIN"],
    "PHOSPHOREMIE": ["PHOSPHORE", "DOSAGE PHOSPHORE", "PHOSPHATEMIE", "PHOSPHORE SANGUIN"],
    "MAGNESEMIE": ["MAGNESIUM", "DOSAGE MAGNESIUM", "MAGNESIUM SANGUIN"],
    "ALBUMINE": ["ALBUMINEMIE", "DOSAGE ALBUMINE", "ALBUMINE SANGUINE"],
    "PROTEINES TOTALES": ["PROTIDEMIE", "DOSAGE PROTEINES TOTALES", "PROTEINES SANGUINES", "PROTIDES TOTAUX"],
    "GGT": ["GAMMA GT", "GAMMA GLUTAMYL TRANSFERASE", "DOSAGE GGT", "GAMMA GLUTAMYL TRANSPEPTIDASE"],
    "PAL": ["PHOSPHATASES ALCALINES", "PHOSPHATASE ALCALINE", "DOSAGE PAL"],
    "ECBU": [
        "EXAMEN CYTOBACTERIOLOGIQUE DES URINES", "CYTOBACTERIOLOGIE URINAIRE",
        "UROCULTURE", "ANALYSE D URINE", "ECBU URINES", "CYTOBACTERIOLOGIE DES URINES",
    ],
    "BANDELETTE URINAIRE": ["BU", "TEST BANDELETTE URINAIRE"],
    "GOUTTE EPAISSE": ["GE", "GOUTTE EPAISSE PALUDISME", "RECHERCHE DE PALUDISME"],
    "TDR PALUDISME": ["TEST DE DIAGNOSTIC RAPIDE PALUDISME", "TEST RAPIDE PALU", "TDR PALU"],
    "SEROLOGIE VIH": ["TEST VIH", "VIH", "VIH 1 2", "SEROLOGIE HIV", "DEPISTAGE VIH"],
    "SEROLOGIE HEPATITE B": ["HEPATITE B", "AG HBS", "ANTIGENE HBS", "SEROLOGIE HBS", "DEPISTAGE HEPATITE B"],
    "SEROLOGIE HEPATITE C": ["HEPATITE C", "AC ANTI VHC", "ANTI VHC", "DEPISTAGE HEPATITE C"],
    "SEROLOGIE SYPHILITIQUE": ["SYPHILIS", "BW", "TPHA", "VDRL", "TPHA VDRL", "SEROLOGIE SYPHILIS"],
    "SERODIAGNOSTIC DE WIDAL": ["WIDAL", "WIDAL ET FELIX", "TEST WIDAL", "SEROLOGIE TYPHOIDE"],
    "BILAN LIPIDIQUE": [
        "LIPIDOGRAMME", "BILAN LIPIDIQUE COMPLET", "EXPLORATION DES ANOMALIES LIPIDIQUES", "EAL",
    ],
    "CHOLESTEROL TOTAL": ["CHOLESTEROL", "DOSAGE CHOLESTEROL"],
    "TRIGLYCERIDES": ["TRIGLYCERIDEMIE", "DOSAGE TRIGLYCERIDES"],
    "ASAT": ["ASAT", "TGO", "SGOT", "TRANSAMINASES ASAT", "TRANSAMINASES TGO", "DOSAGE TGO", "TRANSAMINASES"],
    "ALAT": ["ALAT", "TGP", "SGPT", "TRANSAMINASES ALAT", "TRANSAMINASES TGP", "DOSAGE TGP"],
    "BILIRUBINE TOTALE": ["BILIRUBINE TOTALE ET DIRECTE", "BILIRUBINEMIE TOTALE", "BILIRUBINE", "DOSAGE BILIRUBINE"],
    "BILIRUBINE CONJUGUEE": ["BILIRUBINE DIRECTE", "BILIRUBINE CONJUGUEE ET LIBRE"],
    "TSH": ["THYREOSTIMULINE", "TSHUS", "TSH ULTRA SENSIBLE", "DOSAGE TSH"],
    "PSA": ["PSA TOTAL", "ANTIGENE SPECIFIQUE DE LA PROSTATE", "DOSAGE PSA"],
    "FER SERIQUE": ["DOSAGE FER", "SIDEREMIE", "FER"],
    "FERRITINE": ["FERRITINEMIE", "DOSAGE FERRITINE"],
    "TRANSFERRINE / CST": ["TRANSFERRINE", "CST", "COEFFICIENT DE SATURATION DE LA TRANSFERRINE"],
    "FROTTIS CERVICO-VAGINAL (FCV)": ["FCV", "FROTTIS DU COL", "FROTTIS CERVICO UTERIN", "FCU", "FROTTIS VAGINAL"],

    # ── Imagerie & Explorations fonctionnelles ──
    "ELECTROCARDIOGRAMME (ECG)": [
        "ECG", "ELECTROCARDIOGRAMME", "TRACE ECG", "ELECTROCARDIOGRAMME DE REPOS",
    ],
    "ECHOGRAPHIE ABDOMINALE": ["ECHO ABDOMINALE", "ECHOGRAPHIE DE L ABDOMEN"],
    "ECHOGRAPHIE ABDOMINO-PELVIENNE": [
        "ECHO ABDOMINO PELVIENNE", "ECHOGRAPHIE ABDOMINALE ET PELVIENNE", "ECHO ABDOMINALE ET PELVIENNE",
    ],
    "ECHOGRAPHIE PELVIENNE": ["ECHO PELVIENNE", "ECHOGRAPHIE DU BASSIN"],
    "ECHOGRAPHIE OBSTETRICALE": [
        "ECHO OBSTETRICALE", "ECHOGRAPHIE DE GROSSESSE", "ECHO PREMIER TRIMESTRE",
        "ECHO T1", "ECHO T2", "ECHO T3", "ECHO MORPHOLOGIQUE",
    ],
    "ECHOGRAPHIE CARDIAQUE": [
        "ECHOCARDIOGRAPHIE", "ECHO CARDIAQUE", "ECHOGRAPHIE COEUR", "ETT", "ECHO COEUR",
    ],
    "ECHOGRAPHIE MAMMAIRE": ["ECHO MAMMAIRE", "ECHOGRAPHIE DU SEIN", "ECHO DU SEIN"],
    "ECHOGRAPHIE THYROIDIENNE": ["ECHO THYROIDE", "ECHOGRAPHIE DE LA THYROIDE", "ECHO CERVICALE"],
    "ECHODOOPLER": ["ECHO DOPPLER", "ECHODOPPLER", "DOPPLER VASCULAIRE", "ECHO DOPPLER VEINEUX"],
    "RADIOGRAPHIE DU THORAX": [
        "RADIO THORAX", "RADIO PULMONAIRE", "RADIOGRAPHIE THORACIQUE", "RX THORAX",
        "TELETHORAX", "RX PULMONAIRE", "RADIO DU THORAX FACE",
    ],
    "RADIOGRAPHIE DU BASSIN": ["RADIO BASSIN", "RX BASSIN"],
    "RADIOGRAPHIE DU RACHIS": ["RADIO RACHIS", "RADIO COLONNE"],
    "MAMMOGRAPHIE": ["MAMMO", "MAMMOGRAPHIE BILATERALE"],
    "SCANNER (TDM)": ["SCANNER", "TDM", "TOMODENSITOMETRIE"],
    "SCANNER CEREBRAL": ["TDM CEREBRAL", "SCANNER DU CERVEAU", "SCANNER DE LA TETE"],
    "SCANNER THORACIQUE": ["TDM THORACIQUE", "SCANNER DES POUMONS"],
    "SCANNER ABDOMINO-PELVIEN": ["TDM ABDOMINO PELVIEN", "SCANNER DU VENTRE"],
    "IRM CEREBRALE": ["IRM DU CERVEAU", "IRM TETE"],

    # ── Consultations médicales ──
    "CONSULTATION DE MEDECINE GENERALE": [
        "CONSULTATION GENERALISTE", "CONSULTATION MEDECIN GENERALISTE",
        "MEDECINE GENERALE", "CONSULTATION GENERALE", "CONSULTATION MEDECIN",
    ],
    "CONSULTATION DE PEDIATRIE": [
        "CONSULTATION PEDIATRIQUE", "PEDIATRIE", "CONSULTATION MEDECIN PEDIATRE",
    ],
    "CONSULTATION DE GYNECOLOGIE": [
        "CONSULTATION GYNECOLOGIQUE", "GYNECOLOGIE", "CONSULTATION GYNECOLOGIE OBSTETRIQUE",
    ],
    "CONSULTATION DE CARDIOLOGIE": [
        "CONSULTATION CARDIOLOGIQUE", "CARDIOLOGIE", "CONSULTATION MEDECIN CARDIOLOGUE",
    ],
    "CONSULTATION DE DERMATOLOGIE": [
        "CONSULTATION DERMATOLOGIQUE", "DERMATOLOGIE", "CONSULTATION MEDECIN DERMATOLOGUE",
    ],
    "CONSULTATION D'OPHTALMOLOGIE": [
        "CONSULTATION OPHTALMOLOGIQUE", "OPHTALMOLOGIE", "CONSULTATION DES YEUX",
    ],
    "CONSULTATION D'ORL": [
        "CONSULTATION ORL", "ORL", "CONSULTATION OTO RHINO LARYNGOLOGIE",
    ],
    "CONSULTATION DENTAIRE": [
        "CONSULTATION CHIRURGIEN DENTISTE", "DENTISTE", "CHIRURGIE DENTAIRE", "SOINS DENTAIRES",
    ],
}


class ActeCatalogMatcher:
    """
    Moteur de recherche et d'appariement robuste pour les actes médicaux du catalogue :
    - Tolérance aux variations orthographiques, accents, majuscules et ponctuations
    - Reconnaissance des sigles et acronymes (N.F.S., E.C.G., E.C.B.U...)
    - Résolution des alias naturels (ex: 'NFS / Hémogramme' -> 'NFS' ou 'Hémogramme')
    - Dictionnaire clinique étendu des synonymes sénégalais et francophones
    - Appariement par sous-ensemble de mots-clés significatifs
    - Fuzzy matching (SequenceMatcher) pour tolérer les légères fautes de frappe
    """

    def __init__(self, leaf_actes: list[ActeMedical]):
        self.leaf_actes = leaf_actes
        self.by_id: dict[int, ActeMedical] = {a.pk: a for a in leaf_actes}
        self.by_code: dict[str, ActeMedical] = {}
        self.by_norm_name: dict[str, ActeMedical] = {}
        self.alias_map: dict[str, ActeMedical] = {}
        self.token_map: list[tuple[set[str], ActeMedical]] = []

        # Indexer les actes du référentiel
        for acte in leaf_actes:
            if acte.code:
                c_norm = _normalize_str(acte.code)
                self.by_code[c_norm] = acte
                self.by_code[c_norm.replace(" ", "")] = acte

            norm_name = _normalize_str(acte.name)
            self.by_norm_name[norm_name] = acte
            self.alias_map[norm_name] = acte

            # Extraire les alias naturels issus des séparateurs (/ , ( ) - [ ])
            parts = [
                _normalize_str(p)
                for p in re.split(r"[/()\[\]\-]", acte.name)
                if _normalize_str(p)
            ]
            for part in parts:
                if len(part) >= 2 and part not in self.alias_map:
                    self.alias_map[part] = acte

            sig_tokens = _extract_significant_tokens(norm_name)
            if sig_tokens:
                self.token_map.append((sig_tokens, acte))

        # Intégrer les synonymes médicaux avancés
        for standard_key, synonyms in MEDICAL_SYNONYMS.items():
            norm_key = _normalize_str(standard_key)
            matched_acte = self.by_norm_name.get(norm_key) or self.alias_map.get(norm_key)
            if not matched_acte:
                # Chercher par inclusion de tokens
                key_tokens = _extract_significant_tokens(norm_key)
                for ref_tokens, a in self.token_map:
                    if key_tokens and key_tokens.issubset(ref_tokens):
                        matched_acte = a
                        break

            if matched_acte:
                for syn in synonyms:
                    norm_syn = _normalize_str(syn)
                    if norm_syn and norm_syn not in self.alias_map:
                        self.alias_map[norm_syn] = matched_acte

    def match(
        self,
        raw_id: Any = None,
        raw_code: Any = None,
        raw_name: Any = None,
    ) -> tuple[ActeMedical | None, str]:
        """
        Tente d'apparier une ligne d'import avec un ActeMedical du référentiel.
        Retourne (acte_trouvé, méthode_de_correspondance).
        """
        # 1. Par ID Acte
        if raw_id is not None and str(raw_id).strip():
            try:
                aid = int(float(str(raw_id).strip()))
                if aid in self.by_id:
                    return self.by_id[aid], "id_exact"
            except (ValueError, TypeError):
                pass

        # 2. Par Code médical
        if raw_code is not None and str(raw_code).strip():
            code_norm = _normalize_str(str(raw_code))
            if code_norm in self.by_code:
                return self.by_code[code_norm], "code_exact"
            compact_code = code_norm.replace(" ", "")
            if compact_code in self.by_code:
                return self.by_code[compact_code], "code_compact"

        if not raw_name or not str(raw_name).strip():
            return None, "aucun_identifiant"

        name_str = str(raw_name).strip()
        norm_input = _normalize_str(name_str)
        if not norm_input:
            return None, "nom_vide"

        # 3. Nom normalisé exact
        if norm_input in self.by_norm_name:
            return self.by_norm_name[norm_input], "nom_exact"

        # 4. Alias naturel ou synonyme médical
        if norm_input in self.alias_map:
            return self.alias_map[norm_input], "alias_medical"

        # 4b. Sous-composantes si l'entrée contient des séparateurs
        input_subparts = [
            _normalize_str(p)
            for p in re.split(r"[/()\[\]\-]", name_str)
            if _normalize_str(p)
        ]
        for sub in input_subparts:
            if sub in self.by_norm_name:
                return self.by_norm_name[sub], "sous_partie_nom"
            if sub in self.alias_map:
                return self.alias_map[sub], "sous_partie_alias"

        # 5. Inclusion des mots-clés significatifs
        input_tokens = _extract_significant_tokens(norm_input)
        if input_tokens:
            best_token_match: tuple[ActeMedical, float] | None = None
            for ref_tokens, acte in self.token_map:
                if not ref_tokens:
                    continue
                # Le référentiel est inclus dans l'entrée (ex: 'DOSAGE GLYCEMIE A JEUN' pour 'GLYCEMIE A JEUN')
                if ref_tokens.issubset(input_tokens):
                    jaccard = len(ref_tokens) / len(input_tokens)
                    if best_token_match is None or jaccard > best_token_match[1]:
                        best_token_match = (acte, jaccard)
                # Ou l'entrée est un sous-ensemble complet de 2+ mots
                elif input_tokens.issubset(ref_tokens) and len(input_tokens) >= 2:
                    jaccard = len(input_tokens) / len(ref_tokens)
                    if best_token_match is None or jaccard > best_token_match[1]:
                        best_token_match = (acte, jaccard)

            if best_token_match and best_token_match[1] >= 0.45:
                return best_token_match[0], "tokens_significatifs"

        # 6. Fuzzy matching (SequenceMatcher) pour tolérer petites fautes de frappe
        candidates: list[tuple[ActeMedical, float]] = []
        for alias_text, acte in self.alias_map.items():
            if abs(len(alias_text) - len(norm_input)) > 5:
                continue
            if alias_text[0] != norm_input[0]:
                continue
            ratio = difflib.SequenceMatcher(None, norm_input, alias_text).ratio()
            if ratio >= 0.88:
                candidates.append((acte, ratio))

        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0], f"fuzzy_{candidates[0][1]:.2f}"

        return None, "non_trouve"


def _parse_delai(raw_val: Any) -> str:
    if not raw_val:
        return ""
    s = _normalize_str(str(raw_val))
    if not s:
        return ""
    if s in DELAI_NORMALIZATION_MAP:
        return DELAI_NORMALIZATION_MAP[s]
    for key, val in DELAI_NORMALIZATION_MAP.items():
        if key in s or s in key:
            return val
    # Direct match with standard choices
    for code, _ in PrestataireActe.DELAI_CHOICES:
        if code and code.upper() == s:
            return code
    return ""


def _parse_boolean(val: Any, default: bool = True) -> bool:
    if val is None or val == "":
        return default
    if isinstance(val, bool):
        return val
    s = _normalize_str(str(val))
    if s in ("1", "TRUE", "VRAI", "OUI", "YES", "O", "Y", "ACTIF", "DISPONIBLE", "DISPO", "PROPOSE", "ACTIVE"):
        return True
    if s in ("0", "FALSE", "FAUX", "NON", "NO", "N", "INACTIF", "INDISPONIBLE", "DESACTIVE", "INACTIVE"):
        return False
    return default


def _parse_price(val: Any) -> Decimal | None:
    if val is None or val == "":
        return None
    if isinstance(val, (int, float, Decimal)):
        try:
            p = Decimal(str(val)).quantize(Decimal("0.01"))
            if p < Decimal("0"):
                return Decimal("0.00")
            return min(p, Decimal("99999999.99"))
        except (InvalidOperation, TypeError):
            return None
    s = str(val).strip().upper()
    # Supprimer les devises et symboles monétaires
    for cur in ("FCFA", "CFA", "XOF", "F CFA", "FRANCS", "FRANC", "F", "$", "€"):
        s = s.replace(cur, "")
    s = s.replace(" ", "").replace("\xa0", "").strip()
    if s in ("GRATUIT", "OFFERT", "INCLUS", "0"):
        return Decimal("0.00")
    if not s:
        return None
    # Gérer les séparateurs de milliers et décimales
    if "." in s and "," in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "." in s:
        parts = s.split(".")
        if len(parts) == 2 and len(parts[1]) == 3:
            s = parts[0] + parts[1]
    elif "," in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) == 3:
            s = parts[0] + parts[1]
        else:
            s = s.replace(",", ".")
    try:
        p = Decimal(s).quantize(Decimal("0.01"))
        if p < Decimal("0"):
            return Decimal("0.00")
        return min(p, Decimal("99999999.99"))
    except (InvalidOperation, TypeError):
        return None


def generate_catalog_template_excel(org: OrganismeDeSante) -> io.BytesIO:
    """
    Génère un classeur Excel contenant la liste des actes du référentiel
    avec les tarifs et délais actuels de la structure (ou les prix de référence).
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Catalogue des actes"

    # Style configuration
    primary_fill = PatternFill(start_color="0D9488", end_color="0D9488", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")
    thin_border = Border(
        left=Side(style="thin", color="E5E7EB"),
        right=Side(style="thin", color="E5E7EB"),
        top=Side(style="thin", color="E5E7EB"),
        bottom=Side(style="thin", color="E5E7EB"),
    )
    zebra_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")

    headers = [
        "ID Acte",
        "Code",
        "Pilier",
        "Sous-catégorie",
        "Nom de l'acte",
        "Prix (FCFA)",
        "Délai indicatif",
        "Disponible (Oui/Non)",
        "Consignes RDV (Optionnel)",
    ]

    ws.append(headers)
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = primary_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border
    ws.row_dimensions[1].height = 28

    # Query applicable leaf acts
    applicable_slugs = applicable_pilier_slugs(org)
    leaf_qs = prestataire_leaf_actes_queryset()
    if applicable_slugs:
        leaf_qs = leaf_qs.filter(service_medical_category__slug__in=applicable_slugs)

    # Preload existing offers
    existing_pa = {
        pa.acte_id: pa
        for pa in PrestataireActe.objects.filter(organisme=org)
    }

    delai_labels = dict(PrestataireActe.DELAI_CHOICES)

    row_idx = 2
    for acte in leaf_qs.order_by(
        "service_medical_category__order",
        "service_medical_category__name",
        "parent_service__name",
        "name",
    ):
        pa = existing_pa.get(acte.pk)
        pilier_name = acte.service_medical_category.name if acte.service_medical_category else ""
        parent_name = acte.parent_service.name if acte.parent_service else ""

        if pa is not None:
            price = float(pa.price)
            delai_str = delai_labels.get(pa.delai, pa.delai) or ""
            dispo = "Oui" if pa.is_available else "Non"
            rdv_notes = pa.rdv_prerequisites or ""
        else:
            price = float(acte.reference_price) if acte.reference_price is not None else 0
            delai_str = ""
            dispo = "Non"
            rdv_notes = acte.rdv_prerequisites or ""

        row_data = [
            acte.pk,
            acte.code or "",
            pilier_name,
            parent_name,
            acte.name,
            price,
            delai_str,
            dispo,
            rdv_notes,
        ]
        ws.append(row_data)

        # Style data row
        is_even = (row_idx % 2 == 0)
        for col_num in range(1, len(row_data) + 1):
            cell = ws.cell(row=row_idx, column=col_num)
            cell.font = data_font
            cell.border = thin_border
            if is_even:
                cell.fill = zebra_fill
            if col_num in (1, 2, 8):
                cell.alignment = center_align
            elif col_num == 6:
                cell.alignment = right_align
                cell.number_format = "#,##0"
            else:
                cell.alignment = left_align

        ws.row_dimensions[row_idx].height = 20
        row_idx += 1

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # Sheet 2: Guide & Valeurs autorisées
    ws_guide = wb.create_sheet(title="Guide & Délais autorisés")
    ws_guide.append(["Champ", "Description & Valeurs acceptées"])
    ws_guide.cell(row=1, column=1).fill = primary_fill
    ws_guide.cell(row=1, column=1).font = header_font
    ws_guide.cell(row=1, column=2).fill = primary_fill
    ws_guide.cell(row=1, column=2).font = header_font

    guide_rows = [
        ("ID Acte", "Identifiant unique interne MedCare Connect. Ne pas modifier pour garantir une correspondance à 100%."),
        ("Nom de l'acte", "Intitulé officiel de l'acte médical."),
        ("Prix (FCFA)", "Prix de l'acte proposé par votre établissement en FCFA (ex: 15000)."),
        ("Disponible", "'Oui' pour afficher l'acte dans votre offre publique, 'Non' pour le désactiver."),
        ("Délai indicatif", "Délai de rendu des résultats ou de réalisation. Valeurs recommandées ci-dessous :"),
    ]
    for k, v in PrestataireActe.DELAI_CHOICES:
        if k:
            guide_rows.append(("", f"• {v} (ou '{k}')"))

    for g_k, g_v in guide_rows:
        ws_guide.append([g_k, g_v])

    ws_guide.column_dimensions["A"].width = 25
    ws_guide.column_dimensions["B"].width = 75

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out


def _detect_file_format(filename: str, content: bytes) -> str:
    ext = (filename or "").lower().rsplit(".", 1)[-1]
    if content.startswith(b"\xd0\xcf\x11\xe0"):
        return "xls_legacy"
    if ext in ("xlsx", "xlsm") or content.startswith(b"PK\x03\x04"):
        return "xlsx"
    if ext == "csv":
        return "csv"
    return "csv"


def _read_rows_from_file(file_obj) -> tuple[list[list[Any]], str]:
    """
    Lit le fichier uploadé (Excel ou CSV) et retourne la liste des lignes brutes.
    """
    content = file_obj.read()
    filename = getattr(file_obj, "name", "")
    fmt = _detect_file_format(filename, content)

    if fmt == "xls_legacy":
        raise ValueError(
            "Le format .xls (ancien Excel 97-2003) n'est pas supporté. "
            "Veuillez enregistrer votre fichier au format moderne Excel (.xlsx) ou CSV (.csv)."
        )

    if fmt == "xlsx":
        bio = io.BytesIO(content)
        wb = openpyxl.load_workbook(bio, data_only=True)
        # Select best matching sheet if multiple sheets exist
        ws = None
        for sname in wb.sheetnames:
            s_low = sname.lower()
            if any(k in s_low for k in ("catalogue", "acte", "tarif", "prix", "examen")):
                ws = wb[sname]
                break
        if ws is None:
            ws = wb.active
        rows = []
        for r in ws.iter_rows(values_only=True):
            if any(cell is not None for cell in r):
                rows.append(list(r))
        return rows, "xlsx"

    # CSV parser
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    decoded_text = None
    for enc in encodings:
        try:
            decoded_text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    if decoded_text is None:
        decoded_text = content.decode("utf-8", errors="replace")

    # Detect delimiter
    sample = decoded_text[:2048]
    delimiter = ";"
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,|\t,")
        delimiter = dialect.delimiter
    except Exception:
        if "\t" in sample:
            delimiter = "\t"
        elif ";" in sample:
            delimiter = ";"
        elif "," in sample:
            delimiter = ","

    reader = csv.reader(io.StringIO(decoded_text), delimiter=delimiter)
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    return rows, "csv"


def import_catalog_from_file(
    file_obj,
    org: OrganismeDeSante,
    auto_activate: bool = True,
) -> dict[str, Any]:
    """
    Importe ou met à jour le catalogue d'actes d'un prestataire depuis un fichier Excel ou CSV.
    """
    try:
        rows, fmt = _read_rows_from_file(file_obj)
    except Exception as e:
        return {
            "success": False,
            "error": f"Erreur lors de la lecture du fichier : {e}",
            "total_rows": 0,
            "created_count": 0,
            "updated_count": 0,
            "skipped_count": 0,
            "errors": [str(e)],
        }

    if not rows:
        return {
            "success": False,
            "error": "Le fichier fourni est vide ou aucune ligne valide n'a été détectée.",
            "total_rows": 0,
            "created_count": 0,
            "updated_count": 0,
            "skipped_count": 0,
            "errors": ["Aucune ligne détectée."],
        }

    # Find header row across the first 25 rows
    header_idx = -1
    col_map: dict[str, int] = {}
    found_headers_preview: list[str] = []

    for r_i, row in enumerate(rows[:25]):
        norm_row = [_normalize_str(str(c or "")).lower() for c in row]
        temp_map = {}
        for c_i, c_val in enumerate(norm_row):
            if not c_val:
                continue
            if "id" in c_val and ("acte" in c_val or c_val in ("id", "identifiant")):
                temp_map["id"] = c_i
            elif ("code" in c_val and "acte" in c_val) or c_val in ("code", "reference", "ref", "ref_acte", "code_acte"):
                temp_map["code"] = c_i
            elif any(w in c_val for w in ("nom", "acte", "actes", "designation", "libelle", "prestation", "prestations", "examen", "examens", "analyse", "analyses", "intitule", "rubrique", "description")):
                if "id" not in c_val:
                    temp_map["name"] = c_i
            elif any(w in c_val for w in ("prix", "tarif", "tarifs", "montant", "cout", "couts", "valeur", "pu", "frais", "cotation")):
                temp_map["price"] = c_i
            elif any(w in c_val for w in ("delai", "delais", "duree", "temps")):
                temp_map["delai"] = c_i
            elif any(w in c_val for w in ("dispo", "disponible", "disponibilite", "actif", "active", "statut", "propose")):
                temp_map["available"] = c_i
            elif any(w in c_val for w in ("consigne", "consignes", "prerequis", "preparation", "instruction", "instructions", "note", "notes")):
                temp_map["prerequisites"] = c_i

        if "name" in temp_map or "id" in temp_map:
            header_idx = r_i
            col_map = temp_map
            found_headers_preview = [str(c or "") for c in row if c is not None]
            if "price" in temp_map:
                break

    if header_idx == -1 or not col_map or ("name" not in col_map and "id" not in col_map):
        preview_text = " · ".join(found_headers_preview[:6]) if found_headers_preview else "Aucun en-tête lisible"
        return {
            "success": False,
            "error": (
                "En-têtes de colonnes non reconnus. Votre fichier doit contenir au moins "
                "une colonne désignant l'acte médical (ex: 'Nom de l'acte', 'Acte', 'Examen', 'Analyse' ou 'ID Acte')."
            ),
            "total_rows": len(rows),
            "created_count": 0,
            "updated_count": 0,
            "skipped_count": 0,
            "errors": [f"Colonnes détectées : {preview_text}"],
        }

    # Initialiser le moteur d'appariement robuste avec tous les actes du référentiel
    all_leaf_actes = list(
        ActeMedical.objects.filter(is_active=True).select_related(
            "service_medical_category", "parent_service"
        )
    )
    matcher = ActeCatalogMatcher(all_leaf_actes)

    # Précharger les offres existantes du prestataire pour mise à jour
    existing_offers = {
        pa.acte_id: pa
        for pa in PrestataireActe.objects.filter(organisme=org)
    }

    # Suivi des actes rencontrés dans CE fichier pour détecter et harmoniser les doublons
    seen_in_file: dict[int, dict[str, Any]] = {}

    created_count = 0
    updated_count = 0
    skipped_count = 0
    errors: list[str] = []
    data_rows = rows[header_idx + 1 :]

    try:
        with transaction.atomic():
            for line_num, row in enumerate(data_rows, start=header_idx + 2):
                def get_val(key):
                    idx = col_map.get(key)
                    if idx is not None and idx < len(row):
                        return row[idx]
                    return None

                raw_id = get_val("id")
                raw_code = get_val("code")
                raw_name = get_val("name")
                raw_price = get_val("price")
                raw_delai = get_val("delai")
                raw_available = get_val("available")
                raw_prereq = get_val("prerequisites")

                # Ignorer les lignes entièrement vides
                if not any(str(get_val(k) or "").strip() for k in col_map):
                    continue

                display_label = str(raw_name or raw_code or (f"ID {raw_id}" if raw_id else f"Ligne {line_num}")).strip()

                # Appariement intelligent multi-critères
                target_acte, match_method = matcher.match(
                    raw_id=raw_id,
                    raw_code=raw_code,
                    raw_name=raw_name,
                )

                if target_acte is None:
                    errors.append(f"Ligne {line_num} : Acte '{display_label}' introuvable dans le référentiel médical.")
                    skipped_count += 1
                    continue

                # Parser le prix avec tolérance monétaire complète
                parsed_price = _parse_price(raw_price)
                if parsed_price is None:
                    if target_acte.pk in existing_offers:
                        parsed_price = existing_offers[target_acte.pk].price
                    elif target_acte.reference_price is not None:
                        parsed_price = target_acte.reference_price
                    else:
                        parsed_price = Decimal("0.00")

                # Parser le délai indicatif
                parsed_delai = _parse_delai(raw_delai)
                if not parsed_delai and target_acte.pk in existing_offers:
                    parsed_delai = existing_offers[target_acte.pk].delai

                # Parser la disponibilité
                is_available = _parse_boolean(
                    raw_available,
                    default=auto_activate if parsed_price > 0 else True,
                )

                # Consignes / prérequis RDV
                prereq_text = str(raw_prereq).strip() if raw_prereq is not None else None

                # Détection des doublons au sein du même fichier
                is_duplicate_in_file = target_acte.pk in seen_in_file
                first_info = seen_in_file.get(target_acte.pk)

                pa = existing_offers.get(target_acte.pk)
                if pa is not None:
                    pa.price = parsed_price
                    pa.delai = parsed_delai
                    pa.is_available = is_available
                    update_fields = ["price", "delai", "is_available", "updated_at"]
                    if prereq_text is not None:
                        pa.rdv_prerequisites = prereq_text
                        update_fields.append("rdv_prerequisites")
                    pa.save(update_fields=update_fields)
                    if not is_duplicate_in_file:
                        updated_count += 1
                else:
                    new_pa = PrestataireActe.objects.create(
                        organisme=org,
                        acte=target_acte,
                        price=parsed_price,
                        delai=parsed_delai,
                        is_available=is_available,
                        rdv_prerequisites=prereq_text or "",
                    )
                    existing_offers[target_acte.pk] = new_pa
                    created_count += 1

                if is_duplicate_in_file and first_info:
                    errors.append(
                        f"Ligne {line_num} : L'acte '{display_label}' correspond au même acte référentiel que la ligne {first_info['line']} "
                        f"('{first_info['name']}'). Le tarif ({parsed_price:,.0f} FCFA) a été harmonisé sans doublon."
                    )
                else:
                    seen_in_file[target_acte.pk] = {
                        "line": line_num,
                        "name": display_label,
                        "price": parsed_price,
                    }
    except Exception as e:
        return {
            "success": False,
            "error": f"Erreur lors de l'enregistrement en base de données : {str(e)}",
            "total_rows": len(data_rows),
            "created_count": 0,
            "updated_count": 0,
            "skipped_count": len(data_rows),
            "errors": [str(e)],
        }

    return {
        "success": True,
        "format": fmt,
        "total_rows": len(data_rows),
        "created_count": created_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "imported_count": created_count + updated_count,
        "errors": errors[:50],  # Keep up to 50 for readability
    }
