"""Catalogue actes prestataire — ordre démo, piliers applicables par type de structure."""
from __future__ import annotations

import unicodedata
from collections import OrderedDict, defaultdict

from django.db.models import Count, Q

from healthcare.data.catalog_pillars import PILLARS_FROM_DOCS
from healthcare.data.structure_types_demo import (
    ALL_PILIER_KEYS,
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


def official_pilier_names() -> list[str]:
    """Noms canoniques des 6 piliers (ordre DEMO_STRUCTURES / SEGMENTATION PDF)."""
    return [p["name"] for p in PILLARS_FROM_DOCS]


OFFICIAL_PILIER_SLUG_ORDER: tuple[str, ...] = tuple(
    PILIER_KEY_TO_SLUG[k] for k in ALL_PILIER_KEYS
)


def official_pilier_services() -> list[ServiceMedical]:
    """Les 6 piliers référentiel actifs, ordre démo (slug canonique)."""
    slugs = OFFICIAL_PILIER_SLUG_ORDER
    by_slug = {
        s.slug: s
        for s in ServiceMedical.objects.filter(slug__in=slugs, is_active=True)
    }
    names = official_pilier_names()
    by_name = {
        s.name: s
        for s in ServiceMedical.objects.filter(name__in=names, is_active=True)
    }
    out: list[ServiceMedical] = []
    for i, slug in enumerate(slugs):
        svc = by_slug.get(slug)
        if svc is None and i < len(names):
            svc = by_name.get(names[i])
        if svc is not None:
            out.append(svc)
    return out


def merge_catalog_blocks(catalog_by_pilier: list, org: OrganismeDeSante) -> list:
    """
    Réordonne les 6 piliers référentiel (ordre démo) et marque applicabilité.
    Les piliers hors référentiel (imports legacy) sont exclus.
    """
    by_pk = {b["pilier"].pk: b for b in catalog_by_pilier}
    applicable = applicable_pilier_slugs(org)
    out = []
    for pilier in official_pilier_services():
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
    "imagerie-medicale": "🖥",
    "explorations-fonctionnelles": "⚡",
    "ambulance-medicalisee": "🚑",
    "soins-specialises": "🩺",
    "soins-dentaires": "🦷",
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


# Libellés catégorie (niveau 2) — variantes imports legacy → référentiel démo
_TYPE_LABEL_ALIASES: dict[tuple[str, str], str] = {
    ("Soins dentaires", "chirurgie dentaire"): "Chirurgie dentaire & orale",
    ("Soins dentaires", "soins conservateurs"): "Soins conservateurs & prévention",
    ("Soins dentaires", "protheses"): "Prothèses dentaires",
    ("Soins dentaires", "esthetique dentaire"): "Dentisterie esthétique",
    ("Soins spécialisés", "cardiologie (soins)"): "Cardiologie",
    ("Soins spécialisés", "orl (soins & gestes)"): "ORL",
    ("Soins spécialisés", "ophtalmologie (soins)"): "Ophtalmologie",
    ("Soins spécialisés", "dermatologie (soins)"): "Dermatologie",
    ("Soins spécialisés", "gynecologie (soins)"): "Gynécologie",
    ("Soins spécialisés", "urologie (soins)"): "Urologie",
    ("Soins spécialisés", "rhumatologie / orthopedie (soins)"): "Rhumatologie / Orthopédie",
    ("Soins spécialisés", "pediatrie (soins)"): "Pédiatrie",
    ("Soins spécialisés", "kinesitherapie / reeducation fonctionnelle"): "Kinésithérapie / Rééducation",
    ("Soins spécialisés", "neurologie (soins)"): "Neurologie",
    ("Soins spécialisés", "pneumologie (soins)"): "Médecine générale",
    ("Soins spécialisés", "gastro-enterologie (soins)"): "Médecine générale",
    ("Explorations fonctionnelles", "cardiologie (explorations)"): "Cardiologie",
    ("Explorations fonctionnelles", "pneumologie (explorations)"): "Pneumologie",
    ("Explorations fonctionnelles", "gastro-enterologie (explorations)"): "Gastro-entérologie",
    ("Explorations fonctionnelles", "neurologie (explorations)"): "Neurologie",
    ("Explorations fonctionnelles", "orl (explorations)"): "ORL",
    ("Explorations fonctionnelles", "ophtalmologie (explorations)"): "Ophtalmologie",
    ("Explorations fonctionnelles", "dermatologie (explorations)"): "Dermatologie",
    ("Explorations fonctionnelles", "gynecologie (explorations)"): "Gynécologie",
    ("Explorations fonctionnelles", "urologie (explorations)"): "Urologie",
    ("Explorations fonctionnelles", "andrologie / fertilite (explorations)"): "Andrologie / Fertilité",
    ("Explorations fonctionnelles", "orthopedie / traumatologie (explorations)"): "Orthopédie",
}

# Noms d'actes en base (imports anciens) → nom canonique référentiel démo
_ACTE_DB_TO_REF_NORM: dict[str, str] = {
    "consultation dentaire specialisee": "consultation specialisee",
    "bilan bucco-dentaire complet": "bilan bucco-dentaire",
    "traitement endodontique mono-radiculaire": "traitement mono-radiculaire",
    "traitement endodontique bi-radiculaire": "traitement bi-radiculaire",
    "traitement endodontique multi-radiculaire": "traitement multi-radiculaire",
    "extraction dentaire simple": "extraction simple",
    "extraction dent de sagesse incluse": "dent de sagesse incluse",
    "drainage abces dentaire": "drainage abces buccal",
    "obturations (composite, amalgame)": "obturation composite",
    "traitement carie (composite)": "obturation composite",
    "detartrage complet": "detartrage",
    "detartrage + polissage + fluoration": "detartrage",
    "couronne ceramique / zirconium": "couronne ceramique",
    "couronne (ceramique, zircon, etc.)": "couronne ceramique",
    "bridge 3 elements": "bridge (par element)",
    "bridge": "bridge (par element)",
    "pose d'implant dentaire": "pose d'implant",
    "couronne sur implant": "couronne implantaire",
    "appareil orthodontique fixe": "appareil fixe (bagues)",
    "appareil orthodontique fixe (arcade)": "appareil fixe (bagues)",
    "appareil orthodontique amovible": "appareil amovible",
    "gouttieres transparentes (aligneurs)": "gouttieres transparentes",
    "contention post-orthodontie": "contentions",
    "blanchiment dentaire professionnel": "blanchiment dentaire",
    "facette ceramique (par dent)": "facettes",
    "smile design (consultation + plan)": "smile design",
    "laser yag (soins)": "laser yag",
    "laser retinien (soins)": "laser retinien",
    "injection intravitreenne (soins)": "injection intravitreenne",
    "biopsie cutanee (soins)": "biopsie cutanee",
    "reeducation post-traumatique (entorse, fracture)": "reeducation post-traumatique",
    "reeducation post-operatoire (genou, hanche, epaule)": "reeducation post-operatoire",
    "kine respiratoire adulte (drainage bronchique)": "kine respiratoire adulte",
    "hemodialyse chronique": "hemodialyse chronique (seance)",
    "ajustement et suivi du traitement psychotrope": "ajustement traitement psychotrope",
    "nebulisation therapeutique (pneumo)": "nebulisation therapeutique",
    "oxygenotherapie (support)": "oxygenotherapie",
    "radiographie rachis (cervical / dorsal / lombaire)": "radiographie rachis cervical",
    "doppler veineux membre inferieur": "echodoppler veineux mi",
    "doppler arteriel membre inferieur": "echodoppler arteriel mi",
    "doppler carotidien": "echodoppler carotidien",
    "echographie cardiaque (echo-coeur)": "echodoppler cardiaque (echo coeur)",
    "tdm thoraco-abdomino-pelvien (tap)": "tdm tap (thoraco-abdomino-pelvien)",
    "tdm des sinus": "tdm sinus",
    "biopsie hepatique (echographie / scanner)": "biopsie hepatique (echo / scanner)",
    "biopsie renale (echographie / scanner)": "biopsie renale (echo / scanner)",
    "biopsie mammaire (stereotaxie / echographie)": "biopsie mammaire (stereotaxie / echo)",
    "biopsie thyroidienne (echographie)": "biopsie thyroidienne (echo)",
    "biopsie ganglionnaire (echographie / scanner)": "biopsie ganglionnaire (echo / scanner)",
    "ponction pleurale (echographie / scanner)": "ponction pleurale (echo / scanner)",
    "cartographie des naevus": "cartographie des naevus",
    "spermogramme (hors laboratoire central)": "spermogramme",
    "test de migration-survie": "test de migration-survie (tms)",
}


def _canonical_type_norm(pillar_name: str, type_name: str) -> str:
    n = _normalize_catalog_label(type_name)
    alias = _TYPE_LABEL_ALIASES.get((pillar_name, n))
    if alias:
        return _normalize_catalog_label(alias)
    return n


def _type_labels_equivalent(pillar_name: str, type_a: str, type_b: str) -> bool:
    return _canonical_type_norm(pillar_name, type_a) == _canonical_type_norm(pillar_name, type_b)


def _ref_norm_for_db_acte(acte_norm: str) -> str:
    return _ACTE_DB_TO_REF_NORM.get(acte_norm, acte_norm)


def _pillar_def_for_service(service: ServiceMedical) -> dict | None:
    slug = (service.slug or "").strip()
    for pillar in PILLARS_FROM_DOCS:
        if pillar["name"] == service.name:
            return pillar
        from django.utils.text import slugify

        if slugify(pillar["name"]) == slug:
            return pillar
    return None


def _match_acte_for_reference(
    db_actes: list,
    used_ids: set[int],
    pillar_name: str,
    type_label: str,
    ref_name: str,
):
    ref_norm = _normalize_catalog_label(ref_name)
    best = None
    best_score = -1
    for acte in db_actes:
        if acte.pk in used_ids:
            continue
        an = _normalize_catalog_label(acte.name)
        mapped = _ref_norm_for_db_acte(an)
        if mapped != ref_norm and an != ref_norm:
            continue
        parent = acte.parent_service.name if acte.parent_service_id else ""
        type_ok = not parent or _type_labels_equivalent(pillar_name, parent, type_label)
        score = 0
        if an == ref_norm:
            score += 20
        elif mapped == ref_norm:
            score += 10
        if type_ok:
            score += 5
        if score > best_score:
            best_score = score
            best = acte
    return best


_catalog_order_cache: dict | None = None


def reset_catalog_order_cache() -> None:
    """Invalide le cache d'ordre après rechargement du référentiel."""
    global _catalog_order_cache
    _catalog_order_cache = None


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
    canon = _canonical_type_norm(pillar_name, type_name)
    type_map = _catalog_order_indexes()["type_order"].get(pillar_name, {})
    idx = type_map.get(type_name)
    if idx is None:
        for tname, ti in type_map.items():
            if _canonical_type_norm(pillar_name, tname) == canon:
                return (ti, type_name.lower())
        return (9999, type_name.lower())
    return (idx, type_name.lower())


def _acte_sort_key(pillar_name: str, type_name: str, acte_name: str) -> tuple[int, str]:
    indexes = _catalog_order_indexes()
    canon_type = _canonical_type_norm(pillar_name, type_name)
    bucket = indexes["acte_order"].get((pillar_name, type_name), {})
    if not bucket:
        for key, b in indexes["acte_order"].items():
            if key[0] == pillar_name and _canonical_type_norm(pillar_name, key[1]) == canon_type:
                bucket = b
                type_name = key[1]
                break
    norm = _ref_norm_for_db_acte(_normalize_catalog_label(acte_name))
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


def _actes_to_subgroups(pilier: ServiceMedical, actes: list) -> list:
    """Regroupe des actes feuilles par sous-famille (niveau 2), ordre référentiel démo."""
    pillar_def = _pillar_def_for_service(pilier)
    if pillar_def and actes:
        used_ids: set[int] = set()
        by_type: OrderedDict[str, list] = OrderedDict()
        for tdef in pillar_def.get("types") or []:
            label = tdef["name"]
            chunk: list = []
            for ref_name in tdef.get("actes") or []:
                acte = _match_acte_for_reference(
                    actes, used_ids, pillar_def["name"], label, ref_name
                )
                if acte is None:
                    continue
                used_ids.add(acte.pk)
                chunk.append(acte)
            if chunk:
                by_type[label] = chunk
        if by_type:
            return [
                {
                    "label": label,
                    "actes": chunk,
                    "icon": icon_for_subfamily_label(label),
                }
                for label, chunk in by_type.items()
            ]

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
    return subgroups


def service_actes_catalog_rows(service: ServiceMedical) -> list[dict]:
    """
    Liste plate acte + catégorie dans l'ordre exact du référentiel démo.
    Une seule ligne par acte référentiel (doublons legacy ignorés).
    """
    pillar_def = _pillar_def_for_service(service)
    db_actes = list(
        prestataire_leaf_actes_queryset()
        .filter(service_medical_category=service)
        .select_related("parent_service")
    )
    if not pillar_def:
        rows = []
        for sg in _actes_to_subgroups(service, db_actes):
            for acte in sg["actes"]:
                rows.append({"acte": acte, "category": sg["label"]})
        return rows

    used_ids: set[int] = set()
    rows: list[dict] = []
    for tdef in pillar_def.get("types") or []:
        type_label = tdef["name"]
        for ref_name in tdef.get("actes") or []:
            acte = _match_acte_for_reference(
                db_actes, used_ids, pillar_def["name"], type_label, ref_name
            )
            if acte is None:
                continue
            used_ids.add(acte.pk)
            rows.append(
                {
                    "acte": acte,
                    "category": type_label,
                    "display_name": ref_name,
                }
            )
    return rows


def service_actes_catalog_subgroups(
    service: ServiceMedical,
    search_query: str = "",
) -> list:
    """Catégories + actes pour filtre public (ordre référentiel)."""
    rows = service_actes_catalog_rows(service)
    q = (search_query or "").strip().lower()
    if q:
        rows = [r for r in rows if q in r["acte"].name.lower()]
    grouped: dict[str, list] = OrderedDict()
    for row in rows:
        grouped.setdefault(row["category"], []).append(row["acte"])
    return [
        {
            "label": label,
            "actes": actes,
            "icon": icon_for_subfamily_label(label),
        }
        for label, actes in grouped.items()
    ]


def prestataire_leaf_actes_catalog_by_pilier() -> list:
    """
    Arbre démo : pilier → catégories (niveau 2) → actes feuilles.
    Ordre = référentiel catalog_pillars (comme DEMO_STRUCTURES), pas alphabétique.
    """
    rows = list(prestataire_leaf_actes_queryset())
    by_pilier_pk: dict[int, list] = defaultdict(list)
    for acte in rows:
        pilier = acte.service_medical_category
        if pilier is None or not pilier.is_active:
            continue
        by_pilier_pk[pilier.pk].append(acte)

    out = []
    for pilier in official_pilier_services():
        actes = by_pilier_pk.get(pilier.pk, [])
        subgroups = _actes_to_subgroups(pilier, actes) if actes else []
        out.append(
            {
                "pilier": pilier,
                "subgroups": subgroups,
                "acte_count": sum(len(s["actes"]) for s in subgroups),
            }
        )
    return out
