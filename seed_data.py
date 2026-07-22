#!/usr/bin/env python3
"""
Données de démo MedCare Connect.

Catalogue officiel (familles de soins + actes + assurances) :
  documents/SEGMENTATION_DES_SERVICES (1).pdf
  documents/ASSURANCES_SENEGAL.pdf

Usage :
  python seed_data.py                  # démo : catalogue si base vide + organismes
  python seed_data.py --reset-catalog  # supprime ancien catalogue + recharge les PDF + organismes
"""
from __future__ import annotations

import argparse
import os
import random

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medcare_connect.settings")
django.setup()

from users.models import User, PatientProfile
from healthcare.models import (
    TypeOrganisme,
    Region,
    ServiceMedical,
    ActeMedical,
    OrganismeDeSante,
    PrestataireActe,
    PriseEnChargeAssurance,
    get_default_subscription_plan,
)
from healthcare.data.catalog_loader import (
    load_full_reference_catalog,
    reset_reference_catalog,
)
from healthcare.organisme_types import sync_organisme_types


def seed_types_regions() -> None:
    print("Types d'organisme & régions...")
    sync_organisme_types()
    for name in ["Dakar", "Thiès", "Saint-Louis", "Ziguinchor", "Kaolack", "Diourbel"]:
        Region.objects.get_or_create(name=name)


def seed_catalog(reset: bool) -> dict:
    if reset:
        print("Réinitialisation du catalogue (actes, services, assurances, offres & PEC)...")
        reset_reference_catalog()
    elif ServiceMedical.objects.exists():
        print("Catalogue déjà présent — mise à jour assurances + actes (sans purge).")
    else:
        print("Base vide — chargement du catalogue officiel (PDF)...")

    assurances_map = load_full_reference_catalog()
    print(f"  → {ServiceMedical.objects.count()} familles (piliers), {ActeMedical.objects.count()} actes, {len(assurances_map)} assurances.")
    return assurances_map


def seed_providers(assurances_map: dict) -> None:
    print("Organismes de démo & offres...")
    sync_organisme_types()
    types = {t.name: t for t in TypeOrganisme.objects.all()}

    dakar = Region.objects.get(name="Dakar")
    providers_data = [
        ("Clinique de la Madeleine", "Clinique", "Rue de la Madeleine", "Madeleine", "Dakar"),
        ("Hôpital Principal de Dakar", "Hôpital", "Avenue Nelson Mandela", "Plateau", "Dakar"),
        ("Laboratoire Bio24", "Laboratoire", "Avenue Cheikh Anta Diop", "Fann", "Dakar"),
        ("Centre Médical Horizon", "Centre de santé", "Route de Ouakam", "Ouakam", "Dakar"),
        ("Cabinet Dr Sow", "Cabinet médical", "Rue 10 x Corniche", "Médina", "Dakar"),
        ("Clinique du Cap", "Clinique", "Route des Almadies", "Almadies", "Dakar"),
        ("Pharmacie Sahel", "Pharmacie", "Boulevard du Général de Gaulle", "Plateau", "Dakar"),
        ("Polyclinique de Liberté", "Clinique", "Avenue de la Liberté", "Liberté", "Dakar"),
    ]

    all_actes = list(ActeMedical.objects.filter(level=3, is_active=True))
    if not all_actes:
        print("  (!) Aucun acte de niveau 3 — impossible de créer des offres.")
        return

    assurances_list = list(assurances_map.values())
    _base_lat, _base_lng = 14.7167, -17.4677

    delai_keys = [k for k, _ in PrestataireActe.DELAI_CHOICES if k]

    for org_name, type_name, address, quartier, city in providers_data:
        prises_dom = type_name in ("Laboratoire", "Hôpital", "Centre de Santé") or (
            type_name == "Clinique" and random.random() > 0.35
        )
        if type_name in ("Pharmacie", "Cabinet Médical"):
            prises_dom = False

        if OrganismeDeSante.objects.filter(name=org_name).exists():
            org = OrganismeDeSante.objects.get(name=org_name)
            # Met à jour les champs « diversité » si le centre existait déjà (re-seed sans reset)
            OrganismeDeSante.objects.filter(pk=org.pk).update(
                prises_sang_domicile=prises_dom,
            )
        else:
            u_username = org_name.lower().replace(" ", "_").replace("'", "")[:20]
            u, created = User.objects.get_or_create(
                username=u_username,
                defaults={
                    "email": f"{u_username}@medcare.sn",
                    "user_type": "prestataire",
                    "first_name": org_name.split()[0],
                    "last_name": " ".join(org_name.split()[1:]),
                },
            )
            if created:
                u.set_password("medcare2024")
                u.save()

            _wa = f"+221771{(abs(hash(org_name)) % 900000) + 100000:06d}"
            org, created = OrganismeDeSante.objects.get_or_create(
                user=u,
                defaults={
                    "subscription_plan": get_default_subscription_plan(),
                    "name": org_name,
                    "raison_sociale": f"{org_name} SARL",
                    "type_organisme": types.get(type_name),
                    "address": address,
                    "quartier": quartier,
                    "city": city,
                    "region": dakar,
                    "latitude": _base_lat + random.uniform(-0.09, 0.09),
                    "longitude": _base_lng + random.uniform(-0.09, 0.09),
                    "contact_phone": f"+221 33 8{random.randint(1, 9)}0 00 {random.randint(10, 99):02d}",
                    "contact_email": f"contact@{u_username}.sn",
                    "whatsapp_number": _wa,
                    "prises_sang_domicile": prises_dom,
                    "description": f"{org_name} est un établissement de santé réputé à {city}, offrant des soins de qualité aux patients.",
                    "is_active": True,
                    "is_verified": True,
                    "opening_hours": {
                        "Lundi": {"open": "08:00", "close": "18:00", "closed": False},
                        "Mardi": {"open": "08:00", "close": "18:00", "closed": False},
                        "Mercredi": {"open": "08:00", "close": "18:00", "closed": False},
                        "Jeudi": {"open": "08:00", "close": "18:00", "closed": False},
                        "Vendredi": {"open": "08:00", "close": "17:00", "closed": False},
                        "Samedi": {"open": "09:00", "close": "13:00", "closed": False},
                        "Dimanche": {"open": "", "close": "", "closed": True},
                    },
                },
            )

        # Offres : compléter si manquantes (après reset ou nouveau labo)
        existing_pa = set(
            PrestataireActe.objects.filter(organisme=org).values_list("acte_id", flat=True)
        )
        pool = [a for a in all_actes if a.id not in existing_pa]
        if not pool:
            continue
        n_add = min(len(pool), random.randint(12, 22))
        for acte in random.sample(pool, n_add):
            ref = float(acte.reference_price or 10000)
            variation = random.uniform(0.8, 1.3)
            PrestataireActe.objects.get_or_create(
                organisme=org,
                acte=acte,
                defaults={
                    "price": round(ref * variation / 500) * 500,
                    "is_available": True,
                    "delai": random.choice(delai_keys) if delai_keys else "",
                },
            )

        if assurances_list:
            existing_pec = set(
                PriseEnChargeAssurance.objects.filter(organisme=org).values_list(
                    "assurance_id", flat=True
                )
            )
            candidates = [a for a in assurances_list if a.id not in existing_pec]
            if candidates:
                pick = random.sample(candidates, min(len(candidates), random.randint(4, 8)))
                for ass in pick:
                    PriseEnChargeAssurance.objects.get_or_create(
                        organisme=org,
                        assurance=ass,
                        defaults={"is_active": True},
                    )


def seed_patient() -> None:
    patient = User.objects.filter(username="testpatient").first()
    if patient:
        PatientProfile.objects.get_or_create(
            user=patient,
            defaults={"city": "Dakar", "quartier": "Plateau", "gender": "M"},
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed MedCare Connect")
    parser.add_argument(
        "--reset-catalog",
        action="store_true",
        help="Supprime services/actes/assurances/offres/PEC puis recharge depuis les documents PDF.",
    )
    args = parser.parse_args()

    seed_types_regions()
    assurances_map = seed_catalog(args.reset_catalog)
    seed_providers(assurances_map)
    seed_patient()

    from healthcare.models import Assurance

    print("\nTerminé — stats :")
    print(f"  Utilisateurs :     {User.objects.count()}")
    print(f"  Prestataires :     {OrganismeDeSante.objects.count()}")
    print(f"  Familles (piliers): {ServiceMedical.objects.count()}")
    print(f"  Actes :            {ActeMedical.objects.count()}")
    print(f"  Assurances :       {Assurance.objects.count()}")
    print(f"  Offres (PA) :      {PrestataireActe.objects.count()}")
    print(f"  PEC :              {PriseEnChargeAssurance.objects.count()}")


if __name__ == "__main__":
    main()
