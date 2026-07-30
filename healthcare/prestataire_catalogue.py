"""Catalogue actes prestataire — ordre démo, piliers applicables par type de structure."""
from __future__ import annotations

import unicodedata
from collections import OrderedDict, defaultdict

from django.db.models import Count, Q

from healthcare.data.catalog_pillars import PILLARS_FROM_DOCS
from healthcare.data.structure_types_demo import (
    DEMO_STRUCTURE_TYPES,
    PILIER_KEY_TO_SLUG,
    demo_key_for_type_name,
    demo_structure_for_type_name,
    pilier_slugs_for_demo_key,
)
from healthcare.models import ActeMedical, OrganismeDeSante, ServiceMedical
from healthcare.service_icons import icon_for_subfamily_label


def applicable_pilier_slugs(org: OrganismeDeSante) -> set[str] | None:
    """
    Slugs de piliers applicables à la structure.
    None = type inconnu → tous les piliers actifs sont affichés comme applicables.
    """
    type_name = (org.type_organisme.name if org.type_organisme_id else "") or ""
    demo_key = demo_key_for_type_name(type_name)
    if demo_key is None:
        return None
    return pilier_slugs_for_demo_key(demo_key)


def type_structure_context(org: OrganismeDeSante) -> dict:
    """Bandeau « type de structure » (ordre et libellés démo)."""
    current_name = org.type_organisme.name if org.type_organisme_id else ""
    current_demo_key = demo_key_for_type_name(current_name) or "labo"
    current_demo = demo_structure_for_type_name(current_name)

    chips = []
    for row in DEMO_STRUCTURE_TYPES:
        slugs = [PILIER_KEY_TO_SLUG[k] for k in row["pilier_keys"] if k in PILIER_KEY_TO_SLUG]
        chips.append(
            {
                "key": row["key"],
                "icon": row["icon"],
                "label": row["label"],
                "desc": row["desc"],
                "piliers": ",".join(slugs),
                "active": row["key"] == current_demo_key,
            }
        )

    if current_demo:
        type_label = current_demo["label"]
        type_desc = current_demo["desc"]
    elif current_name:
        type_label = current_name
        type_desc = "Type non référencé dans la démo — tous les piliers sont proposés."
    else:
        type_label = "Non renseigné"
        type_desc = "Renseignez votre type de structure dans votre profil."

    applicable = applicable_pilier_slugs(org)
    return {
        "type_chips": chips,
        "type_label": type_label,
        "type_desc": type_desc,
        "applicable_slugs": applicable or set(),
    }


def merge_catalog_blocks(catalog_by_pilier: list, org: OrganismeDeSante) -> list:
    """
    Réordonne tous les piliers actifs du référentiel (ordre démo) et marque applicabilité.
    """
    by_pk = {b["pilier"].pk: b for b in catalog_by_pilier}
    applicable = applicable_pilier_slugs(org)
    out = []
    for pilier in ServiceMedical.objects.filter(is_active=True).order_by("order", "name"):
        block = by_pk.get(pilier.pk)
        if block is None:
            block = {
                "pilier": pilier,
                "subgroups": [],
                "acte_count": 0,
            }
        block = dict(block)
        block["applicable"] = (
            True if applicable is None else pilier.slug in applicable
        )
        block["pilier"] = pilier
        out.append(block)
    return out


def _prereq_lines(text: str) -> list[str]:
    """Découpe un texte de consignes en lignes (affichage liste démo)."""
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


PILIER_ICONS: dict[str, str] = {
    "biologie-medicale": "🧬",
    "imagerie-medicale": "🩻",
    "explorations-fonctionnelles": "📈",
    "soins-paramedicaux": "💉",
}


def pilier_icon_for_slug(slug: str) -> str:
    return PILIER_ICONS.get(slug or "", "")


def prep_display_for_acte(acte, pa) -> dict:
    """État affichage colonne Préparation / panneau rappels."""
    ref = (acte.rdv_prerequisites or "").strip()
    custom = ""
    active = True
    configured = bool(ref)
    if pa is not None:
        custom = (pa.rdv_prerequisites or "").strip()
        active = pa.rdv_prerequisites_active
        configured = bool(custom) or (active and bool(ref))
    message = custom or ref
    return {
        "configured": configured and bool(message),
        "active": active,
        "text": message,
        "message": message,
        "reference": ref,
        "reference_lines": _prereq_lines(ref),
        "custom": custom,
        "pa_pk": pa.pk if pa else None,
    }


def prep_panel_payload(acte, category: str, pilier: str, pa, org=None, pilier_slug: str = "") -> dict:
    """Données JSON pour le panneau latéral (catalogue actes)."""
    from healthcare.prestataire_prep_reminders import reminders_for_acte

    prep = prep_display_for_acte(acte, pa)
    reminders = reminders_for_acte(org, acte.pk) if org else []
    return {
        "acte_id": acte.pk,
        "name": acte.name,
        "category": category,
        "pilier": pilier,
        "pilier_slug": pilier_slug,
        "pilier_icon": pilier_icon_for_slug(pilier_slug),
        "reference": prep["reference"],
        "reference_lines": prep["reference_lines"],
        "message": prep["message"],
        "active": prep["active"],
        "configured": prep["configured"],
        "reminders": reminders,
    }


def _normalize_catalog_label(name: str) -> str:
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip().replace("'", "'").replace("  ", " ")


_catalog_order_cache: dict | None = None


def _catalog_order_indexes() -> dict:
    """Index d'ordre pilier → type → acte (référentiel PDF / démo)."""
    global _catalog_order_cache
    if _catalog_order_cache is not None:
        return _catalog_order_cache

    type_order: dict[str, dict[str, int]] = {}
    acte_order: dict[tuple[str, str], dict[str, int]] = {}
    acte_names: dict[tuple[str, str], list[tuple[str, int]]] = {}

    for pillar in PILLARS_FROM_DOCS:
        pname = pillar["name"]
        for ti, tdef in enumerate(pillar.get("types") or []):
            tname = tdef["name"]
            type_order.setdefault(pname, {})[tname] = ti
            bucket: dict[str, int] = {}
            names_list: list[tuple[str, int]] = []
            for ai, aname in enumerate(tdef.get("actes") or []):
                norm = _normalize_catalog_label(aname)
                bucket[norm] = ai
                names_list.append((norm, ai))
            acte_order[(pname, tname)] = bucket
            acte_names[(pname, tname)] = names_list

    _catalog_order_cache = {
        "type_order": type_order,
        "acte_order": acte_order,
        "acte_names": acte_names,
    }
    return _catalog_order_cache


def _type_sort_key(pillar_name: str, type_name: str) -> tuple[int, str]:
    idx = _catalog_order_indexes()["type_order"].get(pillar_name, {}).get(type_name)
    if idx is None:
        return (9999, type_name.lower())
    return (idx, type_name.lower())


def _acte_sort_key(pillar_name: str, type_name: str, acte_name: str) -> tuple[int, str]:
    indexes = _catalog_order_indexes()
    bucket = indexes["acte_order"].get((pillar_name, type_name), {})
    norm = _normalize_catalog_label(acte_name)
    if norm in bucket:
        return (bucket[norm], acte_name.lower())

    for cat_norm, idx in indexes["acte_names"].get((pillar_name, type_name), []):
        if norm.startswith(cat_norm) or cat_norm.startswith(norm):
            return (idx, acte_name.lower())
        if norm.split(" ")[0] == cat_norm.split(" ")[0]:
            return (idx, acte_name.lower())

    return (9999, acte_name.lower())


def prestataire_leaf_actes_queryset():
    """Actes feuilles sélectionnables — ordre référentiel (pas alphabétique)."""
    return (
        ActeMedical.objects.filter(level=3, is_active=True)
        .annotate(
            _presta_sub_act_count=Count(
                "sub_acts", filter=Q(sub_acts__is_active=True)
            )
        )
        .filter(_presta_sub_act_count=0)
        .select_related("service_medical_category", "parent_service")
    )


def prestataire_leaf_actes_catalog_by_pilier() -> list:
    """
    Arbre démo : pilier → catégories (niveau 2) → actes feuilles.
    Ordre = référentiel catalog_pillars (comme DEMO_STRUCTURES), pas alphabétique.
    """
    rows = list(prestataire_leaf_actes_queryset())
    by_pilier: OrderedDict = OrderedDict()
    for acte in rows:
        pilier = acte.service_medical_category
        if pilier is None or not pilier.is_active:
            continue
        by_pilier.setdefault(pilier, []).append(acte)

    out = []
    for pilier, actes in by_pilier.items():
        pname = pilier.name
        by_parent: dict[tuple[int, str], list] = defaultdict(list)
        for a in actes:
            if a.parent_service_id:
                key = (a.parent_service_id, a.parent_service.name)
            else:
                key = (0, "Sans sous-famille")
            by_parent[key].append(a)

        subgroups = []
        parent_keys = sorted(
            by_parent.keys(),
            key=lambda t: _type_sort_key(pname, t[1]),
        )
        for pk_label in parent_keys:
            _pk, label = pk_label
            chunk = sorted(
                by_parent[pk_label],
                key=lambda x: _acte_sort_key(pname, label, x.name),
            )
            subgroups.append(
                {
                    "label": label,
                    "actes": chunk,
                    "icon": icon_for_subfamily_label(label),
                }
            )
        out.append(
            {
                "pilier": pilier,
                "subgroups": subgroups,
                "acte_count": sum(len(s["actes"]) for s in subgroups),
            }
        )
    return out
