"""
Import et Export du catalogue d'actes pour les prestataires de santé.
Prend en charge les formats Excel (.xlsx, .xls) et CSV (.csv).
"""
from __future__ import annotations

import csv
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
    "immediat": "immediat",
    "immédiat": "immediat",
    "urgence": "immediat",
    "immediat urgence": "immediat",
    "immédiat urgence": "immediat",
    "30min": "30min",
    "30 min": "30min",
    "moins de 30 min": "30min",
    "1h": "1h",
    "1 h": "1h",
    "1 heure": "1h",
    "moins d'1 heure": "1h",
    "moins d 1 heure": "1h",
    "2h": "2h",
    "2 h": "2h",
    "2 heures": "2h",
    "moins de 2 heures": "2h",
    "4h": "4h",
    "4 h": "4h",
    "journee": "4h",
    "dans la journee": "4h",
    "dans la journée": "4h",
    "24h": "24h",
    "24 h": "24h",
    "sous 24 h": "24h",
    "sous 24h": "24h",
    "48h": "48h",
    "48 h": "48h",
    "sous 48 h": "48h",
    "sous 48h": "48h",
    "72h": "72h",
    "72 h": "72h",
    "sous 72 h": "72h",
    "sous 72h": "72h",
    "7j": "7j",
    "7 j": "7j",
    "7 jours": "7j",
    "sous 7 jours": "7j",
    "sous 7j": "7j",
    "rdv": "rdv",
    "sur rdv": "rdv",
    "sur rendez-vous": "rdv",
    "sur rendezvous": "rdv",
    "rendez-vous": "rdv",
    "rendez vous": "rdv",
}


def _normalize_str(s: str | None) -> str:
    if not s:
        return ""
    text = unicodedata.normalize("NFKD", str(s))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(text.split())


def _parse_delai(raw_val: Any) -> str:
    if not raw_val:
        return ""
    s = _normalize_str(str(raw_val))
    if not s:
        return ""
    if s in DELAI_NORMALIZATION_MAP:
        return DELAI_NORMALIZATION_MAP[s]
    for key, val in DELAI_NORMALIZATION_MAP.items():
        if key in s:
            return val
    # Direct match with standard choices
    for code, _ in PrestataireActe.DELAI_CHOICES:
        if code and code.lower() == s:
            return code
    return ""


def _parse_boolean(val: Any, default: bool = True) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in ("1", "true", "vrai", "oui", "yes", "o", "y", "actif", "disponible"):
        return True
    if s in ("0", "false", "faux", "non", "no", "n", "inactif", "indisponible"):
        return False
    return default


def _parse_price(val: Any) -> Decimal | None:
    if val is None or val == "":
        return None
    if isinstance(val, (int, float, Decimal)):
        try:
            return Decimal(str(val)).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError):
            return None
    s = str(val).strip().upper()
    # Remove currency words
    for cur in ("FCFA", "CFA", "XOF", "F CFA", "FRANCS"):
        s = s.replace(cur, "")
    s = s.replace(" ", "").replace("\xa0", "").replace(",", ".")
    if not s:
        return None
    try:
        p = Decimal(s).quantize(Decimal("0.01"))
        return p if p >= Decimal("0") else None
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
    if ext in ("xlsx", "xlsm"):
        return "xlsx"
    if ext == "csv":
        return "csv"
    # Fallback inspecting signature
    if content.startswith(b"PK\x03\x04"):
        return "xlsx"
    return "csv"


def _read_rows_from_file(file_obj) -> tuple[list[list[Any]], str]:
    """
    Lit le fichier uploadé (Excel ou CSV) et retourne la liste des lignes brutes.
    """
    content = file_obj.read()
    filename = getattr(file_obj, "name", "")
    fmt = _detect_file_format(filename, content)

    if fmt == "xlsx":
        bio = io.BytesIO(content)
        wb = openpyxl.load_workbook(bio, data_only=True)
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
            "error": "Le fichier fourni est vide.",
            "total_rows": 0,
            "created_count": 0,
            "updated_count": 0,
            "skipped_count": 0,
            "errors": ["Aucune ligne détectée."],
        }

    # Find header row
    header_idx = -1
    col_map: dict[str, int] = {}
    for r_i, row in enumerate(rows[:10]):
        norm_row = [_normalize_str(str(c or "")) for c in row]
        temp_map = {}
        for c_i, c_val in enumerate(norm_row):
            if "id" in c_val and ("acte" in c_val or c_val == "id"):
                temp_map["id"] = c_i
            elif "code" in c_val:
                temp_map["code"] = c_i
            elif any(w in c_val for w in ("nom", "acte", "designation", "libelle", "prestation")):
                if "id" not in c_val:
                    temp_map["name"] = c_i
            elif any(w in c_val for w in ("prix", "tarif", "montant", "cout", "couts")):
                temp_map["price"] = c_i
            elif any(w in c_val for w in ("delai", "delais", "duree")):
                temp_map["delai"] = c_i
            elif any(w in c_val for w in ("dispo", "disponible", "actif", "active")):
                temp_map["available"] = c_i
            elif any(w in c_val for w in ("consigne", "consignes", "prerequis", "preparation")):
                temp_map["prerequisites"] = c_i

        # A valid header must have at least name or id, and preferably price
        if ("name" in temp_map or "id" in temp_map) and "price" in temp_map:
            header_idx = r_i
            col_map = temp_map
            break
        elif ("name" in temp_map or "id" in temp_map):
            header_idx = r_i
            col_map = temp_map

    if header_idx == -1 or not col_map:
        return {
            "success": False,
            "error": (
                "En-têtes de colonnes non reconnus. Assurez-vous d'avoir au moins les colonnes "
                "'Nom de l'acte' (ou 'ID Acte') et 'Prix (FCFA)'."
            ),
            "total_rows": len(rows),
            "created_count": 0,
            "updated_count": 0,
            "skipped_count": 0,
            "errors": ["Impossible d'identifier les colonnes d'en-tête."],
        }

    # Preload database reference acts
    all_leaf_actes = list(
        ActeMedical.objects.filter(is_active=True).select_related(
            "service_medical_category", "parent_service"
        )
    )
    by_id = {a.pk: a for a in all_leaf_actes}
    by_code = {a.code.strip().lower(): a for a in all_leaf_actes if a.code}
    by_exact_name = {a.name.strip().lower(): a for a in all_leaf_actes}
    by_norm_name = {_normalize_str(a.name): a for a in all_leaf_actes}

    # Preload existing provider offers for update
    existing_offers = {
        pa.acte_id: pa
        for pa in PrestataireActe.objects.filter(organisme=org)
    }

    created_count = 0
    updated_count = 0
    skipped_count = 0
    errors: list[str] = []
    data_rows = rows[header_idx + 1 :]

    with transaction.atomic():
        for line_num, row in enumerate(data_rows, start=header_idx + 2):
            # Safe access to columns
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

            # Ignore totally empty rows
            if not any(get_val(k) for k in col_map):
                continue

            # Match ActeMedical
            target_acte: ActeMedical | None = None
            if raw_id is not None:
                try:
                    aid = int(str(raw_id).strip())
                    target_acte = by_id.get(aid)
                except (ValueError, TypeError):
                    pass

            if target_acte is None and raw_code:
                c_str = str(raw_code).strip().lower()
                target_acte = by_code.get(c_str)

            if target_acte is None and raw_name:
                name_str = str(raw_name).strip()
                target_acte = by_exact_name.get(name_str.lower())
                if target_acte is None:
                    target_acte = by_norm_name.get(_normalize_str(name_str))

            if target_acte is None:
                display_label = raw_name or raw_code or raw_id or f"Ligne {line_num}"
                errors.append(f"Ligne {line_num} : Acte '{display_label}' introuvable dans le référentiel.")
                skipped_count += 1
                continue

            # Parse price
            parsed_price = _parse_price(raw_price)
            if parsed_price is None:
                if target_acte.pk in existing_offers:
                    # Keep existing price
                    parsed_price = existing_offers[target_acte.pk].price
                elif target_acte.reference_price is not None:
                    parsed_price = target_acte.reference_price
                else:
                    parsed_price = Decimal("0")

            # Parse delai
            parsed_delai = _parse_delai(raw_delai)
            if not parsed_delai and target_acte.pk in existing_offers:
                parsed_delai = existing_offers[target_acte.pk].delai

            # Parse availability
            is_available = _parse_boolean(
                raw_available,
                default=auto_activate if parsed_price > 0 else True,
            )

            # RDV prerequisites
            prereq_text = str(raw_prereq).strip() if raw_prereq is not None else None

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
