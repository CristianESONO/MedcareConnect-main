"""
DashboardService — Logique métier pour le tableau de bord prestataire.

Extrait de healthcare/views.py::prestataire_dashboard afin de décharger la vue
de toute logique non liée au HTTP.
"""
from __future__ import annotations

from django.db.models import Count, Sum
from django.utils import timezone


class DashboardService:
    """Calculs statistiques pour le tableau de bord d'un OrganismeDeSante."""

    # ------------------------------------------------------------------ #
    #  Métriques de visite et panier                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_period_stats(org, since=None) -> dict:
        """
        Retourne le comptage de vues de profil et d'items panier sur la période.

        Args:
            org: OrganismeDeSante instance
            since: datetime ou None (toute la durée)

        Returns:
            dict avec views_period, items_period
        """
        from cart.models import CartItem
        from healthcare.models import ProfileView

        views_qs = ProfileView.objects.filter(organisme=org)
        if since:
            views_qs = views_qs.filter(viewed_at__gte=since)

        items_qs = CartItem.objects.filter(prestataire_acte__organisme=org)
        if since:
            items_qs = items_qs.filter(added_at__gte=since)

        return {
            "views_period": views_qs.count(),
            "items_period": items_qs.count(),
            "_items_qs": items_qs,  # réutilisé par top_actes
        }

    @staticmethod
    def get_devis_stats(org, since=None) -> dict:
        """
        Comptage et valeur des sous-devis (DevisPart) sur la période.

        Returns:
            dict avec devis_period, devis_value, pending_devis, new_devis_count
        """
        from cart.models import DevisPart

        devis_part_qs = DevisPart.objects.filter(
            organisme=org,
            status__in=["sent", "viewed", "relanced"],
        ).exclude(devis__status="draft")
        if since:
            devis_part_qs = devis_part_qs.filter(created_at__gte=since)

        devis_period = devis_part_qs.count()
        devis_value = devis_part_qs.aggregate(v=Sum("total_brut"))["v"] or 0

        pending_devis = DevisPart.objects.filter(
            organisme=org,
            status="sent",
            created_at__lte=timezone.now() - timezone.timedelta(hours=24),
        ).exclude(devis__status="draft").count()

        new_devis_count = DevisPart.objects.filter(
            organisme=org,
            status="sent",
        ).exclude(devis__status="draft").count()

        return {
            "devis_period": devis_period,
            "devis_value": devis_value,
            "pending_devis": pending_devis,
            "new_devis_count": new_devis_count,
        }

    @staticmethod
    def get_top_actes(items_qs, limit: int = 5) -> tuple[list, int]:
        """
        Top actes par nombre d'apparitions dans les paniers.

        Args:
            items_qs: CartItem queryset (déjà filtré par période)
            limit: nombre max de résultats

        Returns:
            (list of rows, max_count)
        """
        rows = list(
            items_qs.values("prestataire_acte__acte__name", "prestataire_acte__price")
            .annotate(n=Count("id"))
            .order_by("-n", "prestataire_acte__acte__name")[:limit]
        )
        max_count = max((r["n"] for r in rows), default=0)
        return rows, max_count

    @staticmethod
    def get_insurance_split(org, since=None, limit: int = 5) -> tuple[list, int]:
        """
        Répartition des assurances parmi les paniers récents pour cet organisme.

        Returns:
            (insurance_split list, insurance_total)
        """
        from cart.models import Cart

        filter_kwargs: dict = {"items__prestataire_acte__organisme": org}
        if since:
            filter_kwargs["updated_at__gte"] = since

        rows = (
            Cart.objects.filter(**filter_kwargs)
            .values("selected_insurance__name")
            .annotate(n=Count("id", distinct=True))
            .order_by("-n")[:limit]
        )
        total = sum(r["n"] for r in rows) or 0
        split = [
            {
                "name": r["selected_insurance__name"] or "Sans assurance",
                "count": r["n"],
                "pct": round(r["n"] * 100.0 / total) if total else 0,
            }
            for r in rows
        ]
        return split, total

    @staticmethod
    def get_rdv_counts(org) -> dict:
        """
        Nombre de RDV en attente et de RDV confirmés à venir.
        """
        from appointments.models import RendezVous

        rdv_requested = RendezVous.objects.filter(
            organisme=org, status=RendezVous.STATUS_REQUESTED
        ).count()
        rdv_upcoming = RendezVous.objects.filter(
            organisme=org,
            status=RendezVous.STATUS_CONFIRMED,
            start__gte=timezone.now(),
        ).count()
        return {
            "rdv_requested_count": rdv_requested,
            "rdv_upcoming_count": rdv_upcoming,
            "new_rdv_count": rdv_requested,
        }

    @staticmethod
    def build_context(
        org,
        period_key: str = "30j",
        period_label: str = "",
        since=None,
        visit_source_filter: str = "all",
    ) -> dict:
        """
        Construit le contexte complet pour le template prestataire/dashboard.html.

        Args:
            org: OrganismeDeSante
            period_key: clé de période (7j, 30j, 90j, etc.)
            period_label: libellé de période
            since: datetime ou None
            visit_source_filter: 'all' ou source de visite

        Returns:
            dict contexte prêt pour render()
        """
        from cart.models import CartItem
        from healthcare.models import PrestataireActe, PriseEnChargeAssurance, ProfileView
        from healthcare.prestataire_analytics import build_activity_chart, medplaque_stats, recent_visits
        from messaging.models import Message

        actes_count = PrestataireActe.objects.filter(organisme=org).count()
        insurances_count = PriseEnChargeAssurance.objects.filter(organisme=org).count()
        recent_views = recent_visits(org, limit=8, source=visit_source_filter)
        accepted_insurances = list(
            PriseEnChargeAssurance.objects.filter(organisme=org, is_active=True)
            .select_related("assurance")
            .order_by("assurance__name")[:6]
        )
        unread = Message.objects.filter(receiver=org.user, is_read=False).count()

        # Période
        period_stats = DashboardService.get_period_stats(org, since)
        items_qs = period_stats.pop("_items_qs")
        devis_stats = DashboardService.get_devis_stats(org, since)
        top_actes_rows, top_actes_max = DashboardService.get_top_actes(items_qs)
        insurance_split, insurance_total = DashboardService.get_insurance_split(org, since)
        rdv_counts = DashboardService.get_rdv_counts(org)

        # Complétion profil (helper privé dans views.py)
        from healthcare.views import _dashboard_completion
        completion = _dashboard_completion(org, actes_count, insurances_count)
        completion_done = sum(1 for c in completion if c["ok"])
        completion_pct = int(round(completion_done * 100.0 / max(len(completion), 1)))

        from healthcare.models import SubscriptionChangeRequest
        pending_subscription_request = SubscriptionChangeRequest.objects.filter(
            organisme=org, status="pending"
        ).first()

        return {
            "org": org,
            "actes_count": actes_count,
            "insurances_count": insurances_count,
            "profile_views_total": org.profile_views_count,
            "recent_views": recent_views,
            "unread_messages": unread,
            "dash_active": "home",
            "period_key": period_key,
            "period_label": period_label,
            "views_period": period_stats["views_period"],
            "items_period": period_stats["items_period"],
            "top_actes_rows": top_actes_rows,
            "top_actes_max": top_actes_max,
            "insurance_split": insurance_split,
            "insurance_split_total": insurance_total,
            "completion": completion,
            "completion_done": completion_done,
            "completion_total": len(completion),
            "completion_pct": completion_pct,
            "accepted_insurances_preview": accepted_insurances,
            "pending_subscription_request": pending_subscription_request,
            "activity_chart": build_activity_chart(org, period_key),
            "medplaque": medplaque_stats(org, since=since),
            "visit_source_filter": visit_source_filter,
            **devis_stats,
            **rdv_counts,
        }
