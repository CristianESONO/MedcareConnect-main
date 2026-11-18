"""
update_missing_acts.py — Ajoute les actes et catégories manquants à la base de données en s’appuyant sur ACTES_ORDER définie dans healthcare/views.py.
Le script est idempotent grâce à get_or_create.
"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medcare_connect.settings")
import django
django.setup()

from healthcare.models import ServiceMedical, ActeMedical
from healthcare.views import ACTES_ORDER

def normalize(name):
    return name.replace("'", "’").replace(" ", "").lower()

added = 0
for pillar_key, pillar_data in ACTES_ORDER.items():
    # dans ACTES_ORDER, la clé est le nom du pilier (ex: "Biologie médicale")
    pillar_name = pillar_key
    try:
        svc = ServiceMedical.objects.get(name=pillar_name)
    except ServiceMedical.DoesNotExist:
        print(f"⚠️ Pilier absent dans la DB : {pillar_name}")
        continue
    for cat_name, act_list in pillar_data.get("acts", {}).items():
        cat_obj, _ = ActeMedical.objects.get_or_create(
            name=cat_name,
            service_medical_category=svc,
            level=2,
            defaults={"parent_service": None, "description": "", "is_active": True},
        )
        for act_name in act_list:
            act_obj, created = ActeMedical.objects.get_or_create(
                name=act_name,
                service_medical_category=svc,
                parent_service=cat_obj,
                level=3,
                defaults={"description": "", "is_active": True},
            )
            if created:
                added += 1
                print(f"✅ Ajouté : {act_name} → {cat_name} ({pillar_name})")

print(f"\n🛠️ Total actes ajoutés : {added}\n")
