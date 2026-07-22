#!/usr/bin/env python3
"""Smoke test HTTP — parcours admin/patient liés aux rappels RDV."""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medcare_connect.settings")
os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
os.environ["HTTPS_ENABLED"] = "false"

import django

django.setup()

from datetime import timedelta

from django.test import Client
from django.urls import reverse
from django.utils import timezone

from appointments.models import RendezVous
from healthcare.models import ActeMedical, OrganismeDeSante, ServiceMedical, SubscriptionPlan
from users.models import User

FAILURES: list[str] = []


def check(label: str, status: int, expected=(200, 302)):
    if status not in (expected if isinstance(expected, tuple) else (expected,)):
        FAILURES.append(f"{label}: HTTP {status} (attendu {expected})")
        return False
    return True


def main() -> int:
    client = Client()
    suffix = uuid.uuid4().hex[:8]

    admin = User.objects.create_user(
        username=f"smoke_admin_{suffix}",
        password="x",
        user_type="admin",
        is_superuser=True,
    )
    patient = User.objects.create_user(
        username=f"smoke_patient_{suffix}",
        password="x",
        user_type="patient",
    )
    prest = User.objects.create_user(
        username=f"smoke_prest_{suffix}",
        password="x",
        user_type="prestataire",
    )
    plan = SubscriptionPlan.objects.create(
        name=f"Smoke {suffix}", slug=f"smoke-{suffix}", is_public=False
    )
    org = OrganismeDeSante.objects.create(
        user=prest,
        name=f"Smoke Org {suffix}",
        address="Dakar",
        subscription_plan=plan,
        is_active=True,
    )
    svc = ServiceMedical.objects.create(name=f"Smoke Svc {suffix}")
    acte = ActeMedical.objects.create(
        name=f"Smoke Acte {suffix}",
        service_medical_category=svc,
        level=3,
        rdv_prerequisites="Smoke prerequisite text.",
    )
    rdv = RendezVous.objects.create(
        patient=patient,
        organisme=org,
        start=timezone.now() + timedelta(days=1),
        status=RendezVous.STATUS_CONFIRMED,
        actes_snapshot=[{"acte_id": acte.pk, "acte": acte.name, "quantity": 1}],
    )

    urls_admin = [
        ("dashboard index", reverse("dashboard:index")),
        ("actes list", reverse("dashboard:actes_list")),
        ("acte edit", reverse("dashboard:acte_edit", kwargs={"pk": acte.pk})),
        ("rdv overview", reverse("dashboard:rdv_overview")),
        ("rdv detail", reverse("dashboard:rdv_admin_detail", kwargs={"reference": rdv.reference})),
        ("reminder schedules", reverse("dashboard:rdv_reminder_schedules_list")),
        ("reminder create form", reverse("dashboard:rdv_reminder_schedule_create")),
    ]

    client.force_login(admin)
    for label, url in urls_admin:
        r = client.get(url)
        check(label, r.status_code)
        print(f"  GET {label}: {r.status_code}")

    client.force_login(patient)
    for label, url in [
        ("patient rdv tab", reverse("users:patient_panel_tab", kwargs={"tab": "rdv"})),
    ]:
        r = client.get(url)
        check(label, r.status_code)
        print(f"  GET {label}: {r.status_code}")

    if FAILURES:
        print("\nÉCHECS:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("\nSmoke test OK — aucune erreur 500 détectée sur les URLs ciblées.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
