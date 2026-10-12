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


@pytest.mark.django_db
def test_catalog_normalization_synonyms_and_duplicates():
    user = User.objects.create_user(username="test_presta_fuzzy", email="fuzzy@medcare.sn", password="pass")
    org = OrganismeDeSante.objects.create(user=user, name="Clinique de l'Espoir", is_active=True)

    svc_bio = ServiceMedical.objects.create(name="Biologie médicale", slug="biologie-medicale-test", order=1, is_active=True)
    svc_img = ServiceMedical.objects.create(name="Imagerie", slug="imagerie-test", order=2, is_active=True)

    nfs = ActeMedical.objects.create(
        name="NFS / Hémogramme",
        code="BIO-NFS",
        service_medical_category=svc_bio,
        level=3,
        reference_price=Decimal("5000"),
        is_active=True,
    )
    gly = ActeMedical.objects.create(
        name="Glycémie à jeun",
        code="BIO-GLY",
        service_medical_category=svc_bio,
        level=3,
        reference_price=Decimal("3000"),
        is_active=True,
    )
    echo = ActeMedical.objects.create(
        name="Échographie abdomino-pelvienne",
        code="IMG-ECHO-ABD",
        service_medical_category=svc_img,
        level=3,
        reference_price=Decimal("25000"),
        is_active=True,
    )

    # Fichier CSV contenant :
    # 1. Sigle avec points et minuscules : "n.f.s."
    # 2. Synonyme étendu : "Numération formule sanguine" (même acte que nfs -> doublon intra-fichier harmonisé)
    # 3. Inclusion de mots-clés : "Dosage de la glycémie à jeun" avec formatage "3.500 FCFA"
    # 4. Alias imagerie sans accents : "ECHO ABDOMINO PELVIENNE" avec formatage "25,000 CFA" et délai "Urgence"
    csv_content = (
        "Nom de l'acte;Prix;Délai indicatif;Disponible\n"
        "n.f.s.;5 000 FCFA;Sous 24h;Oui\n"
        "NUMERATION FORMULE SANGUINE;6000 CFA;24 h;Oui\n"
        "Dosage de la glycémie à jeun;3.500 FCFA;immediat;Oui\n"
        "ECHO ABDOMINO PELVIENNE;25,000;Urgent;Oui\n"
    )

    csv_file = SimpleUploadedFile("catalogue_variations.csv", csv_content.encode("utf-8"), content_type="text/csv")
    res = import_catalog_from_file(csv_file, org, auto_activate=True)

    assert res["success"] is True
    # Exactly 3 distinct leaf acts should be created/updated (no duplicate offers)
    assert PrestataireActe.objects.filter(organisme=org).count() == 3

    # NFS must have the final price from the second line (6000 FCFA)
    pa_nfs = PrestataireActe.objects.get(organisme=org, acte=nfs)
    assert pa_nfs.price == Decimal("6000.00")
    assert pa_nfs.delai == "24h"

    # Glycémie parsed correctly
    pa_gly = PrestataireActe.objects.get(organisme=org, acte=gly)
    assert pa_gly.price == Decimal("3500.00")
    assert pa_gly.delai == "immediat"

    # Echo parsed correctly
    pa_echo = PrestataireActe.objects.get(organisme=org, acte=echo)
    assert pa_echo.price == Decimal("25000.00")
    assert pa_echo.delai == "immediat"

    # Verify that the duplicate warning was generated
    assert any("correspond au même acte référentiel" in err for err in res["errors"])


@pytest.mark.django_db
def test_fuzzy_typo_matching_and_price_variations():
    user = User.objects.create_user(username="test_presta_typo", email="typo@medcare.sn", password="pass")
    org = OrganismeDeSante.objects.create(user=user, name="Cabinet Test Typo", is_active=True)
    svc = ServiceMedical.objects.create(name="Consultations", slug="consult-typo", order=1, is_active=True)

    nfs = ActeMedical.objects.create(name="NFS / Hémogramme", service_medical_category=svc, level=3, is_active=True)
    consult = ActeMedical.objects.create(name="Consultation de médecine générale", service_medical_category=svc, level=3, is_active=True)

    csv_content = (
        "Nom de l'acte;Prix;Délai\n"
        "Hemograme;Gratuit;immediat\n"
        "Consultation medecin generaliste;15 000 FCFA;24h\n"
    )
    csv_file = SimpleUploadedFile("typo.csv", csv_content.encode("utf-8"), content_type="text/csv")
    res = import_catalog_from_file(csv_file, org, auto_activate=True)
    assert res["success"] is True
    assert PrestataireActe.objects.filter(organisme=org).count() == 2

    pa_nfs = PrestataireActe.objects.get(organisme=org, acte=nfs)
    assert pa_nfs.price == Decimal("0.00")

    pa_c = PrestataireActe.objects.get(organisme=org, acte=consult)
    assert pa_c.price == Decimal("15000.00")


