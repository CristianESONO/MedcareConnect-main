"""
Complète les DevisPart manquants pour un devis parent (même logique que la migration 0005).

Les devis créés avant l’introduction des parts, importés, ou issus d’un déploiement où la
migration RunPython n’a pas couvert toutes les lignes, n’ont pas de sous-devis : la fiche
patient n’affiche alors pas les boutons WhatsApp. Cette fonction est idempotente.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal

from cart.models import CartItem, DevisPart


def _create_part(devis, org, lines, tb, tp, ta):
    DevisPart.objects.create(
        reference=f"DP-{uuid.uuid4().hex[:10].upper()}",
        devis_id=devis.pk,
        organisme_id=org.pk,
        details=list(lines),
        total_brut=tb,
        total_assurance=ta,
        total_patient=tp,
        status=devis.status,
        relance_count=devis.relance_count or 0,
        last_relanced_at=devis.last_relanced_at,
        archived_at=devis.archived_at,
        archived_reason=devis.archived_reason,
    )


def ensure_devis_has_parts(devis) -> int:
    """
    Crée les DevisPart si le parent n’en a aucun, à partir de `devis.details` puis du panier.

    Retourne le nombre de parts créées (0 si déjà des parts ou données insuffisantes).
    """
    from healthcare.models import OrganismeDeSante

    if devis.parts.exists():
        return 0

    created = 0
    details_list = devis.details or []

    if details_list:
        by_name: defaultdict[str, list] = defaultdict(list)
        for line in details_list:
            name = (line.get("organisme") or "").strip()
            by_name[name].append(line)
        for org_name, lines in by_name.items():
            if not org_name:
                continue
            org = OrganismeDeSante.objects.filter(name=org_name).first()
            if not org:
                continue
            tb = sum(Decimal(str(x.get("subtotal", "0"))) for x in lines)
            tp = sum(
                Decimal(str(x.get("patient_cost", x.get("subtotal", "0"))))
                for x in lines
            )
            ta = tb - tp
            _create_part(devis, org, lines, tb, tp, ta)
            created += 1

    if devis.parts.exists():
        return created

    if not devis.cart_id:
        return created

    snap = devis.details or []
    by_oid: defaultdict[int, list] = defaultdict(list)
    for ci in CartItem.objects.filter(cart_id=devis.cart_id).select_related(
        "prestataire_acte__organisme", "prestataire_acte__acte"
    ):
        by_oid[ci.prestataire_acte.organisme_id].append(ci)

    for oid, ci_list in by_oid.items():
        org = OrganismeDeSante.objects.filter(pk=oid).first()
        if not org:
            continue
        lines = []
        tb = Decimal("0")
        tp = Decimal("0")
        for ci in ci_list:
            pa = ci.prestataire_acte
            qty = ci.quantity or 1
            subtotal = pa.price * qty
            tb += subtotal
            patient_cost = subtotal
            coverage_rate = None
            for d in snap:
                if d.get("acte") == pa.acte.name and d.get("organisme") == org.name:
                    patient_cost = Decimal(str(d.get("patient_cost", subtotal)))
                    cr = d.get("coverage_rate")
                    coverage_rate = cr if cr not in (None, "None") else None
                    break
            tp += patient_cost
            lines.append({
                "acte": pa.acte.name,
                "organisme": org.name,
                "unit_price": str(pa.price),
                "quantity": qty,
                "subtotal": str(subtotal),
                "coverage_rate": str(coverage_rate) if coverage_rate else None,
                "patient_cost": str(patient_cost),
            })
        ta = tb - tp
        _create_part(devis, org, lines, tb, tp, ta)
        created += 1

    return created
