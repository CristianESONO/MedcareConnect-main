"""Aligne la grille d'abonnement sur le document BIZ-ECO-003 (v3, 4 plans).

- Pionnier (gratuit M0–M6) : inchangé.
- Starter : NOUVEAU, 24 000 F/mois — mono-pilier, base + MedPlaque en add-on.
- Essentiel : 25 000 → 39 000 F/mois — + réservations, MedPlaque incluse, stats.
- Pro : 50 000 → 69 000 F/mois — tout inclus (API, multi-sites, support).
- Réseau : SUPPRIMÉ (les structures concernées basculent sur Pro).
"""
from django.db import migrations


def apply(apps, schema_editor):
    Feature = apps.get_model("healthcare", "SubscriptionFeature")
    Plan = apps.get_model("healthcare", "SubscriptionPlan")
    PlanFeature = apps.get_model("healthcare", "SubscriptionPlanFeature")
    Organisme = apps.get_model("healthcare", "OrganismeDeSante")

    feat = {f.code: f for f in Feature.objects.all()}

    def set_features(plan, codes):
        wanted = set(codes)
        # Ajoute les manquantes
        for c in wanted:
            if c in feat:
                PlanFeature.objects.get_or_create(
                    plan=plan, feature=feat[c], defaults={"included": True}
                )
        # Retire celles qui ne sont plus voulues
        PlanFeature.objects.filter(plan=plan).exclude(
            feature__code__in=wanted
        ).delete()

    base = ["listing", "profil_public", "assurances", "whatsapp_devis", "dashboard_basic"]

    # ── Pionnier (inchangé, on s'assure juste de l'ordre) ──
    Plan.objects.filter(slug="pionnier").update(order=0)

    # ── Starter (nouveau) ──
    starter, _ = Plan.objects.update_or_create(
        slug="starter",
        defaults={
            "name": "Starter",
            "short_description": "Structure mono-pilier — base annuaire + devis. MedPlaque en option (+5 000 F/mois).",
            "monthly_price_fcfa": 24000,
            "is_default": False,
            "is_public": True,
            "is_pioneer_offer": False,
            "order": 10,
        },
    )
    set_features(starter, base)

    # ── Essentiel ──
    essentiel = Plan.objects.filter(slug="essentiel").first()
    if essentiel:
        Plan.objects.filter(pk=essentiel.pk).update(
            monthly_price_fcfa=39000,
            short_description="Structures multi-piliers — réservations, MedPlaque incluse, stats mensuelles.",
            order=20,
        )
        set_features(
            essentiel,
            base + ["dashboard_advanced", "reservations", "medplaque", "stats_mensuelles"],
        )

    # ── Pro ──
    pro = Plan.objects.filter(slug="pro").first()
    if pro:
        Plan.objects.filter(pk=pro.pk).update(
            monthly_price_fcfa=69000,
            short_description="Hôpitaux / 6 piliers — tout Essentiel + API, multi-sites, support prioritaire.",
            order=30,
        )
        set_features(
            pro,
            base
            + [
                "dashboard_advanced",
                "reservations",
                "medplaque",
                "stats_mensuelles",
                "api_partenaires",
                "multi_sites",
                "support_prioritaire",
            ],
        )

    # ── Réseau : supprimé, structures rebasculées sur Pro ──
    reseau = Plan.objects.filter(slug="reseau").first()
    if reseau:
        target = pro or Plan.objects.filter(slug="essentiel").first()
        if target:
            Organisme.objects.filter(subscription_plan_id=reseau.pk).update(
                subscription_plan_id=target.pk
            )
        PlanFeature.objects.filter(plan=reseau).delete()
        # change requests éventuelles pointant vers Réseau
        try:
            reseau.change_requests.all().delete()
        except Exception:
            pass
        reseau.delete()


def reverse(apps, schema_editor):
    # Réversion minimale : retire Starter, restaure tarifs antérieurs. Réseau non recréé.
    Plan = apps.get_model("healthcare", "SubscriptionPlan")
    Plan.objects.filter(slug="starter").delete()
    Plan.objects.filter(slug="essentiel").update(monthly_price_fcfa=25000)
    Plan.objects.filter(slug="pro").update(monthly_price_fcfa=50000)


class Migration(migrations.Migration):
    dependencies = [
        ("healthcare", "0016_service_medical_pillar_icons"),
    ]

    operations = [
        migrations.RunPython(apply, reverse),
    ]
