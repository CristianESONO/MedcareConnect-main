# Generated manually for sous-devis par structure

import uuid
from collections import defaultdict
from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


def _create_part(DevisPart, devis, org, lines, tb, tp, ta):
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


def forwards_backfill_devis_parts(apps, schema_editor):
    Devis = apps.get_model("cart", "Devis")
    DevisPart = apps.get_model("cart", "DevisPart")
    CartItem = apps.get_model("cart", "CartItem")
    OrganismeDeSante = apps.get_model("healthcare", "OrganismeDeSante")

    for devis in Devis.objects.all().iterator():
        if DevisPart.objects.filter(devis_id=devis.pk).exists():
            continue
        details_list = devis.details or []
        if details_list:
            by_name = defaultdict(list)
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
                _create_part(DevisPart, devis, org, lines, tb, tp, ta)
        if DevisPart.objects.filter(devis_id=devis.pk).exists():
            continue
        if not devis.cart_id:
            continue
        snap = devis.details or []
        by_oid = defaultdict(list)
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
            _create_part(DevisPart, devis, org, lines, tb, tp, ta)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("cart", "0004_devis_archived_at_devis_archived_reason_and_more"),
        ("healthcare", "0012_prelevementzone"),
    ]

    operations = [
        migrations.CreateModel(
            name="DevisPart",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.CharField(editable=False, max_length=32, unique=True)),
                ("details", models.JSONField(help_text="Snapshot des lignes (actes) pour cette structure uniquement")),
                ("total_brut", models.DecimalField(decimal_places=2, max_digits=12)),
                ("total_assurance", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("total_patient", models.DecimalField(decimal_places=2, max_digits=12)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Brouillon"),
                            ("sent", "Envoyé"),
                            ("viewed", "Consulté"),
                            ("relanced", "Relancé"),
                            ("expired", "Expiré"),
                            ("archived", "Archivé"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("relance_count", models.PositiveSmallIntegerField(default=0)),
                ("last_relanced_at", models.DateTimeField(blank=True, null=True)),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                ("archived_reason", models.CharField(blank=True, max_length=120, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "devis",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="parts",
                        to="cart.devis",
                    ),
                ),
                (
                    "organisme",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="devis_parts",
                        to="healthcare.organismedesante",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sous-devis (structure)",
                "verbose_name_plural": "Sous-devis (structures)",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="devispart",
            constraint=models.UniqueConstraint(
                fields=("devis", "organisme"),
                name="cart_devispart_unique_devis_organisme",
            ),
        ),
        migrations.RunPython(forwards_backfill_devis_parts, noop_reverse),
    ]
