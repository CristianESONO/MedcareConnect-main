"""
Chatbot d'onboarding & Assistant d'import prestataire.
Périmètre : Piliers 1 à 6 (Biologie, Imagerie, Explorations, Ambulance, Soins spécialisés, Dentaire).
Gère la réconciliation d'import selon le cahier des charges et la sauvegarde dans le catalogue.
"""
from __future__ import annotations
import difflib
import json
import logging
import os
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from healthcare.models import ActeMedical, PrestataireActe, ServiceMedical, TypeOrganisme, OrganismeDeSante
from healthcare.catalog_excel import (
    ActeCatalogMatcher,
    _read_rows_from_file,
    _normalize_str,
    _parse_price,
    _parse_delai,
)
from healthcare.reconciliation_engine import normalize_label

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Page principale
# ─────────────────────────────────────────────────────────────────────────────

@ensure_csrf_cookie
@login_required
def chatbot_collecte_view(request):
    """
    Affiche l'assistant d'import.
    Pour les prestataires connectés ayant déjà un profil établissement,
    les questions redondantes (nature, piliers, contact) sont passées directement
    pour aller à l'import de catalogue et à la réconciliation.
    """
    PILIER_PKS = [1, 2, 3, 4, 5, 6]
    piliers = ServiceMedical.objects.filter(pk__in=PILIER_PKS).order_by("order")
    types_organisme = TypeOrganisme.objects.all().order_by("name")

    org = None
    try:
        org = OrganismeDeSante.objects.get(user=request.user)
    except OrganismeDeSante.DoesNotExist:
        pass

    # Préparation du référentiel des actes actifs pour le select de réconciliation
    leaf_actes = list(
        ActeMedical.objects.filter(is_active=True)
        .select_related("service_medical_category")
        .order_by("name")
    )
    ref_list = []
    for a in leaf_actes:
        cat_name = a.service_medical_category.name if a.service_medical_category else "Général"
        code_tag = cat_name[:3].upper() if cat_name else "ACT"
        ref_list.append({
            "id": a.pk,
            "n": a.name,
            "c": code_tag,
        })

    recommends_imagerie = False
    recommends_biologie = False
    if org:
        p_names = [p.name.lower() for p in org.piliers_actifs.all()]
        t_name = org.type_organisme.name.lower() if org.type_organisme else ""
        org_name = org.name.lower()
        if any("imagerie" in p for p in p_names) or "imagerie" in t_name or "scanner" in t_name or "radiologie" in t_name or "imagerie" in org_name:
            recommends_imagerie = True
        if any("biologie" in p for p in p_names) or "laboratoire" in t_name or "labo" in t_name or "bio" in org_name:
            recommends_biologie = True

    return render(
        request,
        "healthcare/chatbot_collecte.html",
        {
            "piliers": piliers,
            "types_organisme": types_organisme,
            "org": org,
            "has_org": bool(org),
            "ref_actes": ref_list,
            "ref_actes_json": ref_list,
            "page_title": "Assistant d'import · MedCare",
            "import_url": "/sante/prestataire/actes/import-excel/",
            "dash_active": "chatbot",
            "recommends_imagerie": recommends_imagerie,
            "recommends_biologie": recommends_biologie,
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# API : sauvegarde des réponses Q1 / Q2 / Q4 (onboarding initial)
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
@login_required
def api_chatbot_submit(request):
    """
    Reçoit les réponses aux questions 1, 2 et 4 (JSON).
    """
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        data = {}

    q1_nature     = data.get("q1_nature", "structure")
    q1_type_libre = (data.get("q1_type_libre") or "").strip()
    q2_piliers    = data.get("q2_piliers", [])
    q4_nom        = (data.get("q4_nom") or "").strip()
    q4_telephone  = (data.get("q4_telephone") or "").strip()
    q4_email      = (data.get("q4_email") or "").strip()
    q4_city       = (data.get("q4_city") or "Dakar").strip()

    errors = {}
    if not q1_nature:
        errors["q1_nature"] = "Veuillez indiquer le type d'établissement."
    if not q2_piliers:
        errors["q2_piliers"] = "Sélectionnez au moins un pilier d'activité."
    if not q4_telephone:
        errors["q4_telephone"] = "Un numéro de téléphone est obligatoire."

    if errors:
        return JsonResponse({"ok": False, "errors": errors}, status=400)

    try:
        org, created = OrganismeDeSante.objects.get_or_create(
            user=request.user,
            defaults={
                "name": q4_nom or request.user.get_full_name() or request.user.username,
                "address": q4_city,
                "city": q4_city,
            },
        )

        if not created:
            if q4_nom and not org.name:
                org.name = q4_nom
            org.city = q4_city or org.city

        org.account_nature = q1_nature
        org.type_libre     = q1_type_libre
        if q4_telephone:
            org.contact_phone = q4_telephone
        if q4_email:
            org.contact_email = q4_email
        org.save()

        if q2_piliers:
            pilier_objs = ServiceMedical.objects.filter(pk__in=q2_piliers)
            org.piliers_actifs.set(pilier_objs)

        return JsonResponse({
            "ok": True,
            "created": created,
            "org_id": org.pk,
            "org_name": org.name,
            "message": "Établissement " + ("créé" if created else "mis à jour") + " avec succès.",
            "import_url": "/sante/prestataire/actes/import-excel/",
            "piliers_count": len(q2_piliers),
        })

    except Exception as exc:
        logger.exception("Erreur chatbot submit: %s", exc)
        return JsonResponse({
            "ok": False,
            "message": f"Une erreur est survenue : {exc}",
        }, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# Helper : Lecture et extraction d'un output JSON de réconciliation
# ─────────────────────────────────────────────────────────────────────────────

def _parse_reconciled_json_data(json_data: dict | list, all_leaf_actes: list[ActeMedical], matcher: ActeCatalogMatcher) -> list[dict]:
    exact_map = {a.name.lower(): a for a in all_leaf_actes}
    exact_code_map = {a.code.lower(): a for a in all_leaf_actes if a.code}

    if isinstance(json_data, dict) and "lines" in json_data:
        items = json_data.get("lines", [])
    elif isinstance(json_data, dict) and "rows" in json_data:
        return json_data.get("rows", [])
    elif isinstance(json_data, list):
        items = json_data
    else:
        items = []

    seen_nraw = set()
    result_rows = []

    for l in items:
        if not isinstance(l, dict):
            continue
        if l.get("kind") and l.get("kind") != "acte":
            continue

        raw_name = l.get("label") or l.get("raw") or l.get("name") or ""
        if not raw_name or str(raw_name).strip().lower() in ("nom", "libelle", "acte", "designation"):
            continue

        nraw = normalize_label(str(raw_name))
        if not nraw or nraw in seen_nraw:
            continue
        seen_nraw.add(nraw)

        issue = l.get("issue", "none")
        cand = l.get("candidat_retenu") or {}
        cand_act = cand.get("acte") or {}
        cand_name = cand_act.get("name") or ""
        cand_code = str(cand_act.get("id") or cand_act.get("code") or "")

        matched_acte = None
        method = "none"

        if cand_name and cand_name.lower() in exact_map:
            matched_acte = exact_map[cand_name.lower()]
            method = "nom_exact"
        elif cand_code and cand_code.lower() in exact_code_map:
            matched_acte = exact_code_map[cand_code.lower()]
            method = "code_exact"
        else:
            if cand_name:
                matched_acte, method = matcher.match(raw_name=cand_name)
            if not matched_acte:
                ctx_or_raw = l.get("ctx") or raw_name
                matched_acte, method = matcher.match(raw_name=ctx_or_raw)

        p_val = l.get("price")
        if isinstance(p_val, dict):
            p_val = p_val.get("value")
        price_val = None
        if p_val is not None:
            parsed_p, _ = _parse_price(p_val)
            if parsed_p is not None:
                price_val = float(parsed_p)

        delai_val = l.get("delai") or ""
        if delai_val:
            parsed_d, _ = _parse_delai(delai_val)
            delai_val = parsed_d or ""

        if matched_acte:
            best_id = matched_acte.pk
            best_nom = matched_acte.name
            st = "ok" if issue == "reconnu" else "confirm"
            score_num = cand.get("score")
            sc = int(score_num * 100) if score_num is not None else (100 if st == "ok" else 85)
        else:
            best_id = -1
            best_nom = ""
            st = "none"
            sc = int(cand.get("score", 0) * 100) if cand.get("score") else 0

        via = cand.get("via") or l.get("explication") or "rapprochement"

        result_rows.append({
            "raw": str(raw_name).strip(),
            "nraw": nraw,
            "st": st,
            "via": str(via),
            "sc": sc,
            "best": best_id,
            "best_nom": best_nom,
            "price": price_val,
            "delai": delai_val,
        })

    return result_rows


# ─────────────────────────────────────────────────────────────────────────────
# API : Réconciliation du fichier importé (Excel, CSV ou JSON pré-rapproché)
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
@login_required
def api_chatbot_reconcile(request):
    """
    Reçoit un fichier Excel, CSV ou JSON issu du programme de rapprochement,
    extrait les lignes et exécute la réconciliation contre le référentiel des actes standardisés.
    """
    upload = request.FILES.get("file") or request.FILES.get("catalog_file")
    if not upload:
        return JsonResponse({"ok": False, "error": "Veuillez sélectionner un fichier Excel (.xlsx), CSV (.csv) ou JSON de réconciliation (.json)."}, status=400)

    filename = getattr(upload, "name", "fichier")
    all_leaf_actes = list(
        ActeMedical.objects.filter(is_active=True).select_related("service_medical_category", "parent_service")
    )
    matcher = ActeCatalogMatcher(all_leaf_actes)

    # 1. Cas particulier : fichier JSON pré-rapproché (output du programme autonome)
    if filename.lower().endswith(".json"):
        try:
            content = upload.read().decode("utf-8")
            json_data = json.loads(content)
        except Exception as exc:
            return JsonResponse({"ok": False, "error": f"Fichier JSON de rapprochement invalide : {exc}"}, status=400)

        result_rows = _parse_reconciled_json_data(json_data, all_leaf_actes, matcher)
        if not result_rows:
            return JsonResponse({"ok": False, "error": "Aucun acte exploitable trouvé dans ce fichier JSON."}, status=400)

        c_ok = sum(1 for row in result_rows if row["st"] == "ok")
        c_cf = sum(1 for row in result_rows if row["st"] == "confirm")
        c_no = sum(1 for row in result_rows if row["st"] == "none")

        return JsonResponse({
            "ok": True,
            "filename": filename,
            "rows": result_rows,
            "stats": {
                "ok": c_ok,
                "cf": c_cf,
                "no": c_no,
                "total": len(result_rows),
            },
        })

    # 2. Fichier tabulaire Excel / CSV
    try:
        raw_rows, fmt = _read_rows_from_file(upload)
    except Exception as exc:
        logger.warning("Erreur lecture fichier réconciliation: %s", exc)
        return JsonResponse({"ok": False, "error": f"Impossible de lire le fichier ({exc})."}, status=400)

    if not raw_rows:
        return JsonResponse({"ok": False, "error": "Le fichier importé est vide."}, status=400)

    # Détection des en-têtes
    header_idx = -1
    col_map: dict[str, int] = {}
    for r_i, r in enumerate(raw_rows[:25]):
        norm_r = [_normalize_str(str(c or "")).lower() for c in r]
        temp_map = {}
        for c_i, c_val in enumerate(norm_r):
            if not c_val:
                continue
            if "id" in c_val and ("acte" in c_val or c_val in ("id", "identifiant")):
                temp_map["id"] = c_i
            elif ("code" in c_val and "acte" in c_val) or c_val in ("code", "reference", "ref"):
                temp_map["code"] = c_i
            elif any(w in c_val for w in ("nom", "acte", "actes", "designation", "libelle", "prestation", "examen", "analyse", "intitule")):
                if "id" not in c_val:
                    temp_map["name"] = c_i
            elif any(w in c_val for w in ("prix", "tarif", "montant", "cout", "valeur", "pu")):
                temp_map["price"] = c_i
            elif any(w in c_val for w in ("delai", "delais", "duree", "temps")):
                temp_map["delai"] = c_i

        if "name" in temp_map or "id" in temp_map:
            header_idx = r_i
            col_map = temp_map
            break

    data_rows = raw_rows[header_idx + 1:] if header_idx >= 0 else raw_rows
    name_col = col_map.get("name", 0 if "id" not in col_map else 1)
    id_col = col_map.get("id")
    code_col = col_map.get("code")
    price_col = col_map.get("price")
    delai_col = col_map.get("delai")

    # Moteur d'appariement
    all_leaf_actes = list(
        ActeMedical.objects.filter(is_active=True).select_related("service_medical_category", "parent_service")
    )
    matcher = ActeCatalogMatcher(all_leaf_actes)

    seen_nraw = set()
    result_rows = []

    for r in data_rows:
        if not r or not any(cell is not None and str(cell).strip() for cell in r):
            continue

        raw_name = str(r[name_col]).strip() if name_col < len(r) and r[name_col] is not None else ""
        if not raw_name or raw_name.lower() in ("nom", "libelle", "acte", "designation"):
            continue

        nraw = normalize_label(raw_name)
        if not nraw or nraw in seen_nraw:
            continue
        seen_nraw.add(nraw)

        raw_id = r[id_col] if id_col is not None and id_col < len(r) else None
        raw_code = r[code_col] if code_col is not None and code_col < len(r) else None
        raw_price = r[price_col] if price_col is not None and price_col < len(r) else None
        raw_delai = r[delai_col] if delai_col is not None and delai_col < len(r) else None

        price_val = None
        if raw_price is not None:
            parsed_p, _ = _parse_price(raw_price)
            if parsed_p is not None:
                price_val = float(parsed_p)

        delai_val = ""
        if raw_delai:
            parsed_d, _ = _parse_delai(raw_delai)
            delai_val = parsed_d or ""

        matched_acte, method = matcher.match(raw_id=raw_id, raw_code=raw_code, raw_name=raw_name)

        if matched_acte:
            if method in ("id_exact", "code_exact", "code_compact", "nom_exact", "alias_medical"):
                st = "ok"
                sc = 100
                via = "nom" if method == "nom_exact" else ("alias" if method == "alias_medical" else method)
            else:
                st = "confirm"
                sc = 85
                via = "flou"
            best_id = matched_acte.pk
            best_nom = matched_acte.name
        else:
            # Recherche du candidat le plus proche
            best_ratio = 0.0
            closest_acte = None
            for a in all_leaf_actes:
                r_sim = difflib.SequenceMatcher(None, nraw, normalize_label(a.name)).ratio()
                if r_sim > best_ratio:
                    best_ratio = r_sim
                    closest_acte = a

            if closest_acte and best_ratio >= 0.72:
                st = "confirm"
                sc = int(best_ratio * 100)
                via = "flou"
                best_id = closest_acte.pk
                best_nom = closest_acte.name
            else:
                st = "none"
                sc = int(best_ratio * 100) if best_ratio >= 0.45 else 0
                via = "—"
                best_id = closest_acte.pk if (closest_acte and best_ratio >= 0.55) else -1
                best_nom = closest_acte.name if (closest_acte and best_ratio >= 0.55) else ""

        result_rows.append({
            "raw": raw_name,
            "nraw": nraw,
            "st": st,
            "via": via,
            "sc": sc,
            "best": best_id,
            "best_nom": best_nom,
            "price": price_val,
            "delai": delai_val,
        })

    c_ok = sum(1 for row in result_rows if row["st"] == "ok")
    c_cf = sum(1 for row in result_rows if row["st"] == "confirm")
    c_no = sum(1 for row in result_rows if row["st"] == "none")

    return JsonResponse({
        "ok": True,
        "filename": getattr(upload, "name", "fichier"),
        "rows": result_rows,
        "stats": {
            "ok": c_ok,
            "cf": c_cf,
            "no": c_no,
            "total": len(result_rows),
        },
    })


# ─────────────────────────────────────────────────────────────────────────────
# API : Chargement direct d'un rapprochement pré-généré (Programme autonome)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def api_chatbot_load_preset(request):
    """
    Charge directement un fichier de rapprochement pré-généré par le programme autonome.
    presets disponibles :
      - 'imagerie' -> ACTES_ET_TARIFICATIONS_reconcilie.json (81 actes · Écho, Scanner, IRM, Radio)
      - 'biologie' / 'bionissa' -> catalogue_test_bionissa_clinique_reconcilie.json (26 actes)
    """
    preset = (request.GET.get("preset") or request.POST.get("preset") or "").lower().strip()

    preset_files = {
        "imagerie": ("ACTES_ET_TARIFICATIONS_reconcilie.json", "Catalogue Imagerie (ACTES ET TARIFICATIONS · 81 actes)"),
        "biologie": ("catalogue_test_bionissa_clinique_reconcilie.json", "Catalogue Biologie (Test Bionissa · 26 actes)"),
        "bionissa": ("catalogue_test_bionissa_clinique_reconcilie.json", "Catalogue Biologie (Test Bionissa · 26 actes)"),
    }

    if preset not in preset_files:
        return JsonResponse({"ok": False, "error": f"Modèle inconnu '{preset}'. Choix disponibles : 'imagerie', 'biologie'."}, status=400)

    fname, display_name = preset_files[preset]
    file_path = os.path.join(settings.BASE_DIR, "documents", "programme_import", fname)
    if not os.path.exists(file_path):
        return JsonResponse({"ok": False, "error": f"Fichier de rapprochement introuvable sur le serveur : {fname}"}, status=404)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        return JsonResponse({"ok": False, "error": f"Erreur lors de la lecture du fichier JSON : {exc}"}, status=500)

    all_leaf_actes = list(
        ActeMedical.objects.filter(is_active=True).select_related("service_medical_category", "parent_service")
    )
    matcher = ActeCatalogMatcher(all_leaf_actes)

    result_rows = _parse_reconciled_json_data(data, all_leaf_actes, matcher)

    c_ok = sum(1 for row in result_rows if row["st"] == "ok")
    c_cf = sum(1 for row in result_rows if row["st"] == "confirm")
    c_no = sum(1 for row in result_rows if row["st"] == "none")

    return JsonResponse({
        "ok": True,
        "filename": fname,
        "display_name": display_name,
        "preset": preset,
        "rows": result_rows,
        "stats": {
            "ok": c_ok,
            "cf": c_cf,
            "no": c_no,
            "total": len(result_rows),
        },
    })


# ─────────────────────────────────────────────────────────────────────────────
# API : Application et validation des correspondances au catalogue
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
@login_required
def api_chatbot_apply_reconciliation(request):
    """
    Enregistre les actes réconciliés et validés par l'utilisateur dans
    la table PrestataireActe de son établissement.
    """
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return JsonResponse({"ok": False, "error": "Données JSON invalides."}, status=400)

    items = payload.get("items", [])
    if not items:
        return JsonResponse({"ok": False, "error": "Aucun acte à enregistrer."}, status=400)

    try:
        org = OrganismeDeSante.objects.get(user=request.user)
    except OrganismeDeSante.DoesNotExist:
        org = OrganismeDeSante.objects.create(
            user=request.user,
            name=request.user.get_full_name() or request.user.username,
            address="Dakar",
            city="Dakar",
        )

    created_count = 0
    updated_count = 0
    skipped_labels = []  # Libellés ignorés car absents du référentiel

    with transaction.atomic():
        for item in items:
            act_id = item.get("acte_id")
            if not act_id or act_id <= 0:
                # Acte non apparié : libellé original tracé pour le retour
                raw_label = item.get("raw") or item.get("raw_label") or ""
                if raw_label:
                    skipped_labels.append(raw_label)
                continue

            try:
                acte = ActeMedical.objects.get(pk=act_id)
            except ActeMedical.DoesNotExist:
                raw_label = item.get("raw") or item.get("raw_label") or ""
                if raw_label:
                    skipped_labels.append(raw_label)
                continue

            item_price = item.get("price")
            if item_price is not None:
                try:
                    price_dec = Decimal(str(item_price))
                except Exception:
                    price_dec = Decimal("10000")
            else:
                price_dec = Decimal("10000")

            item_delai = item.get("delai") or ""

            pa, created = PrestataireActe.objects.get_or_create(
                organisme=org,
                acte=acte,
                defaults={
                    "price": price_dec,
                    "delai": item_delai,
                    "is_available": True,
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1
                if item.get("price") is not None:
                    pa.price = price_dec
                if item_delai:
                    pa.delai = item_delai
                pa.is_available = True
                pa.save()

    total_applied = created_count + updated_count

    # Auto-configurer les piliers_actifs si l'org n'en a pas encore
    # (garantit la visibilité des actes dans /prestataire/actes/)
    if total_applied > 0 and not org.piliers_actifs.exists():
        pilier_ids = set()
        acte_ids_imported = [
            item.get("acte_id") for item in items
            if item.get("acte_id") and item.get("acte_id") > 0
        ]
        for acte in ActeMedical.objects.filter(pk__in=acte_ids_imported).select_related(
            "service_medical_category", "parent_service"
        ):
            # Le pilier = service de niveau 1
            cat = acte.service_medical_category
            if cat is not None:
                if cat.parent is None:
                    pilier_ids.add(cat.pk)
                elif cat.parent.parent is None:
                    pilier_ids.add(cat.parent.pk)
                elif cat.parent.parent.parent is None:
                    pilier_ids.add(cat.parent.parent.pk)
            if acte.parent_service_id:
                pilier_ids.add(acte.parent_service_id)
        if pilier_ids:
            org.piliers_actifs.set(pilier_ids)


    skipped_count = len(skipped_labels)
    msg_parts = [
        f"Félicitations ! {total_applied} acte(s) ont été enregistrés dans votre catalogue",
        f"({created_count} nouveau(x), {updated_count} mis à jour).",
    ]
    if skipped_count:
        msg_parts.append(
            f"{skipped_count} libellé(s) n'ont pas pu être associés au référentiel MedCare "
            f"et n'ont pas été importés."
        )
    msg = " ".join(msg_parts)

    return JsonResponse({
        "ok": True,
        "created_count": created_count,
        "updated_count": updated_count,
        "total_count": total_applied,
        "skipped_count": skipped_count,
        "skipped_labels": skipped_labels[:50],  # max 50 pour éviter payload trop lourd
        "message": msg,
        "redirect_url": "/sante/prestataire/actes/",
    })