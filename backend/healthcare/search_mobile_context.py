"""Contexte embarqué pour les onglets bas mobile (panier / messages) sur /healthcare/search/."""

from decimal import Decimal


def build_search_mobile_app_context(request):
    user = request.user
    if user.is_authenticated and getattr(user, "is_patient", False):
        from messaging.models import Conversation
        from users.patient_panel import _chariot_ctx

        from messaging.views import _group_by_day

        ctx = _chariot_ctx(user)
        search_convs = (
            Conversation.objects.filter(patient=user)
            .select_related(
                "patient",
                "prestataire",
                "devis_part__organisme",
                "rendez_vous",
            )
            .order_by("-updated_at")
        )
        ctx["search_conversations"] = search_convs
        ctx["grouped_search_conversations"] = _group_by_day(search_convs)
        return ctx

    if not user.is_authenticated:
        from cart.views import _guest_cart_get_map
        from healthcare.models import PrestataireActe

        mp = _guest_cart_get_map(request)
        guest_items = []
        guest_total = Decimal(0)
        if mp:
            pas = (
                PrestataireActe.objects.filter(
                    pk__in=list(mp.keys()),
                    is_available=True,
                    organisme__is_active=True,
                )
                .select_related("acte", "organisme", "acte__service_medical_category")
            )
            found = {pa.pk: pa for pa in pas}
            for pa_id, qty in sorted(mp.items()):
                pa = found.get(pa_id)
                if not pa:
                    continue
                sub = pa.price * qty
                guest_total += sub
                guest_items.append({"pa": pa, "qty": qty, "subtotal": sub})

        org_groups_map: dict[int, dict] = {}
        for row in guest_items:
            org = row["pa"].organisme
            bucket = org_groups_map.setdefault(
                org.pk,
                {"organisme": org, "lines": [], "total": Decimal(0), "count": 0},
            )
            bucket["lines"].append(row)
            bucket["total"] += row["subtotal"]
            bucket["count"] += row["qty"]
        guest_org_groups = sorted(
            org_groups_map.values(), key=lambda g: g["organisme"].name.lower()
        )
        return {
            "guest_items": guest_items,
            "guest_total": guest_total,
            "guest_org_groups": guest_org_groups,
            "cart_items_count": sum(row["qty"] for row in guest_items),
        }

    return {}
