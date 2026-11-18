"""Fixtures partagées : utilisateurs, structure, catalogue, panier."""

import uuid

import pytest

from cart.models import Cart, CartItem
from healthcare.models import (
    ActeMedical,
    OrganismeDeSante,
    PrestataireActe,
    ServiceMedical,
    SubscriptionPlan,
)
from users.models import User


def _uniq(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


@pytest.fixture
def subscription_plan(db):
    return SubscriptionPlan.objects.create(
        name=_uniq("QA Plan"),
        slug=_uniq("qa-plan"),
    )


@pytest.fixture
def patient_user(db):
    return User.objects.create_user(
        username=_uniq("qa_patient"),
        email="patient@qa.test",
        password="test-pass-qa-123",
        user_type="patient",
    )


@pytest.fixture
def prestataire_user(db):
    return User.objects.create_user(
        username=_uniq("qa_prest"),
        email="prest@qa.test",
        password="test-pass-qa-123",
        user_type="prestataire",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username=_uniq("qa_admin"),
        email="admin@qa.test",
        password="test-pass-qa-123",
        user_type="admin",
    )


@pytest.fixture
def superuser(db):
    u = User.objects.create_user(
        username=_uniq("qa_super"),
        email="super@qa.test",
        password="test-pass-qa-123",
        user_type="admin",
        is_superuser=True,
    )
    return u


@pytest.fixture
def organisme_actif(subscription_plan, prestataire_user, db):
    return OrganismeDeSante.objects.create(
        user=prestataire_user,
        name=_uniq("Structure QA"),
        address="Dakar",
        subscription_plan=subscription_plan,
        is_active=True,
        is_verified=True,
    )


@pytest.fixture
def organisme_en_attente(subscription_plan, db):
    prest = User.objects.create_user(
        username=_uniq("qa_prest_pending"),
        email="pending@qa.test",
        password="test-pass-qa-123",
        user_type="prestataire",
    )
    return OrganismeDeSante.objects.create(
        user=prest,
        name=_uniq("Structure en attente"),
        address="Dakar",
        subscription_plan=subscription_plan,
        is_active=False,
        is_verified=False,
    )


@pytest.fixture
def prestataire_acte(organisme_actif, db):
    svc = ServiceMedical.objects.create(name=_uniq("Service QA"))
    acte = ActeMedical.objects.create(
        name=_uniq("Acte QA"),
        service_medical_category=svc,
        level=3,
    )
    return PrestataireActe.objects.create(
        organisme=organisme_actif,
        acte=acte,
        price=7500,
    )


@pytest.fixture
def cart_avec_ligne(patient_user, prestataire_acte, db):
    cart = Cart.objects.create(patient=patient_user, status="active", name="Chariot QA")
    CartItem.objects.create(
        cart=cart,
        prestataire_acte=prestataire_acte,
        quantity=1,
    )
    return cart


@pytest.fixture
def acte_catalogue_libre(db):
    svc = ServiceMedical.objects.create(name=f"Svc CRUD {_uniq('crud')}")
    return ActeMedical.objects.create(
        name=f"Acte CRUD {_uniq('acte')}",
        service_medical_category=svc,
        level=3,
        is_active=True,
    )


@pytest.fixture
def organisme_horaires(organisme_actif, db):
    from appointments.slots import JOURS

    organisme_actif.opening_hours = {
        day: {"open": "07:00", "close": "18:00", "closed": False} for day in JOURS
    }
    organisme_actif.save(update_fields=["opening_hours"])
    return organisme_actif


@pytest.fixture
def devis_part_patient(patient_user, organisme_horaires, prestataire_acte, db):
    from decimal import Decimal

    from cart.models import Devis, DevisPart

    cart = Cart.objects.create(patient=patient_user, status="converted")
    devis = Devis.objects.create(
        patient=patient_user,
        cart=cart,
        total_brut=Decimal("7500"),
        total_assurance=Decimal("0"),
        total_patient=Decimal("7500"),
        details=[],
        status="sent",
    )
    return DevisPart.objects.create(
        devis=devis,
        organisme=organisme_horaires,
        details=[{"acte": prestataire_acte.acte.name, "quantity": 1}],
        total_brut=Decimal("7500"),
        total_assurance=Decimal("0"),
        total_patient=Decimal("7500"),
        status="sent",
    )
