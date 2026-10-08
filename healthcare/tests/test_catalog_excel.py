import io
from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from healthcare.catalog_excel import generate_catalog_template_excel, import_catalog_from_file
from healthcare.models import ActeMedical, OrganismeDeSante, PrestataireActe, ServiceMedical

User = get_user_model()


@pytest.mark.django_db
def test_generate_and_import_catalog_excel():
    user = User.objects.create_user(username="test_presta", email="test@medcare.sn", password="pass")
    org = OrganismeDeSante.objects.create(user=user, name="Clinique Test", is_active=True)

    svc = ServiceMedical.objects.create(name="Biologie médicale", slug="biologie-medicale", order=1, is_active=True)
    acte1 = ActeMedical.objects.create(
        name="NFS / Hémogramme",
        code="BIO-NFS",
        service_medical_category=svc,
        level=3,
        reference_price=Decimal("5000"),
        is_active=True,
    )
    acte2 = ActeMedical.objects.create(
        name="Glycémie à jeun",
        code="BIO-GLY",
        service_medical_category=svc,
        level=3,
        reference_price=Decimal("3000"),
        is_active=True,
    )

    # 1. Génération du modèle Excel
    bio = generate_catalog_template_excel(org)
    assert bio.getvalue() is not None
    assert len(bio.getvalue()) > 100

    # 2. Importation via le flux Excel
    upload = SimpleUploadedFile(
        "mon_catalogue.xlsx",
        bio.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    res = import_catalog_from_file(upload, org, auto_activate=True)
    assert res["success"] is True
    assert res["imported_count"] >= 2
    assert PrestataireActe.objects.filter(organisme=org, acte=acte1).exists()

    # 3. Modification et réimport via CSV
    csv_content = (
        "ID Acte;Code;Nom de l'acte;Prix (FCFA);Délai indicatif;Disponible\n"
        f"{acte1.pk};BIO-NFS;NFS / Hémogramme;6500;Sous 24 h;Oui\n"
        f"{acte2.pk};BIO-GLY;Glycémie à jeun;3500;30min;Oui\n"
    )
    csv_file = SimpleUploadedFile("update.csv", csv_content.encode("utf-8"), content_type="text/csv")
    res_csv = import_catalog_from_file(csv_file, org, auto_activate=True)
    assert res_csv["success"] is True
    assert res_csv["updated_count"] >= 2

    pa1 = PrestataireActe.objects.get(organisme=org, acte=acte1)
    assert pa1.price == Decimal("6500.00")
    assert pa1.delai == "24h"
    assert pa1.is_available is True

    pa2 = PrestataireActe.objects.get(organisme=org, acte=acte2)
    assert pa2.price == Decimal("3500.00")
    assert pa2.delai == "30min"


@pytest.mark.django_db
def test_actes_excel_views(client):
    user = User.objects.create_user(
        username="test_presta_view",
        email="view@medcare.sn",
        password="pass",
        user_type="prestataire",
    )
    org = OrganismeDeSante.objects.create(user=user, name="Centre Médical Alpha", is_active=True)
    svc = ServiceMedical.objects.create(name="Consultations", slug="consultations", order=1, is_active=True)
    acte = ActeMedical.objects.create(
        name="Consultation Généraliste",
        service_medical_category=svc,
        level=3,
        reference_price=Decimal("10000"),
        is_active=True,
    )

    client.force_login(user)

    # Template download view
    url_template = reverse("healthcare:actes_template_excel")
    resp_template = client.get(url_template)
    assert resp_template.status_code == 200
    assert "spreadsheetml" in resp_template["Content-Type"]

    # Import view via AJAX
    csv_content = f"ID Acte;Nom de l'acte;Prix;Délai\n{acte.pk};Consultation Généraliste;12000;immediat\n"
    csv_file = SimpleUploadedFile("catalogue.csv", csv_content.encode("utf-8"), content_type="text/csv")

    url_import = reverse("healthcare:actes_import_excel")
    resp_import = client.post(
        url_import,
        {"file": csv_file, "auto_activate": "1"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert resp_import.status_code == 200
    data = resp_import.json()
    assert data["ok"] is True
    assert data["imported_count"] == 1

    pa = PrestataireActe.objects.get(organisme=org, acte=acte)
    assert pa.price == Decimal("12000.00")
    assert pa.delai == "immediat"
