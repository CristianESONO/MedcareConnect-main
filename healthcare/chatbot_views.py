"""
Chatbot d'onboarding & Assistant d'import prestataire.
Périmètre : Piliers 1 à 6 (Biologie, Imagerie, Explorations, Ambulance, Soins spécialisés, Dentaire).
Gère la réconciliation d'import selon le cahier des charges et la sauvegarde dans le catalogue.
"""
from __future__ import annotations
import difflib
import json
import logging
from decimal import Decimal

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
# API : Réconciliation du fichier importé
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
@login_required
def api_chatbot_reconcile(request):
    """
    Reçoit un fichier Excel ou CSV, extrait les lignes et exécute la
    réconciliation contre le référentiel des actes standardisés MedCare.
    Retourne la liste des lignes avec statuts (ok / confirm / none), score,
    actes correspondants et statistiques.
    """
    upload = request.FILES.get("file") or request.FILES.get("catalog_file")
    if not upload:
        return JsonResponse({"ok": False, "error": "Veuillez sélectionner un fichier Excel (.xlsx) ou CSV (.csv)."}, status=400)

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

            if closest_acte and best_ratio >= 0.55:
                st = "confirm"
                sc = int(best_ratio * 100)
                via = "flou"
                best_id = closest_acte.pk
                best_nom = closest_acte.name
            else:
                st = "none"
                sc = int(best_ratio * 100) if best_ratio >= 0.3 else 0
                via = "—"
                best_id = closest_acte.pk if (closest_acte and best_ratio >= 0.4) else -1
                best_nom = closest_acte.name if (closest_acte and best_ratio >= 0.4) else ""

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

    with transaction.atomic():
        for item in items:
            act_id = item.get("acte_id")
            if not act_id or act_id <= 0:
                continue

            try:
                acte = ActeMedical.objects.get(pk=act_id)
            except ActeMedical.DoesNotExist:
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


    msg = (
        f"Félicitations ! {total_applied} acte(s) ont été enregistrés dans votre catalogue "
        f"({created_count} nouveau(x), {updated_count} mis à jour)."
    )

    return JsonResponse({
        "ok": True,
        "created_count": created_count,
        "updated_count": updated_count,
        "total_count": total_applied,
        "message": msg,
        "redirect_url": "/sante/prestataire/actes/",
    })