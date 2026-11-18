"""Check which demo acts are missing from the database."""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medcare_connect.settings")

import django
django.setup()

from healthcare.models import ServiceMedical, ActeMedical
from healthcare.views import ACTES_ORDER


def normalize(name):
    if not name:
        return ""
    return (
        name.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace(" ", "")
        .lower()
    )


db_piliers = {normalize(p.name): p.name for p in ServiceMedical.objects.all()}
db_subgroups = {
    normalize(n): n
    for n in ActeMedical.objects.filter(level=2).values_list("name", flat=True)
}
db_acts = {
    normalize(n): n
    for n in ActeMedical.objects.filter(level=3, is_active=True).values_list("name", flat=True)
}

print("=== PILIERS ===")
for p_name in ACTES_ORDER:
    p_norm = normalize(p_name)
    found = "OUI" if p_norm in db_piliers else "MANQUANT"
    print("  [%s] %s" % (found, p_name))

print()
print("=== CATEGORIES MANQUANTES (niveau 2) ===")
total_missing_cats = 0
for p_name, p_info in ACTES_ORDER.items():
    for cat in p_info["categories"]:
        cat_norm = normalize(cat)
        if cat_norm not in db_subgroups:
            print("  MANQUANT: [%s] -> %s" % (p_name, cat))
            total_missing_cats += 1
if total_missing_cats == 0:
    print("  Toutes les categories sont presentes!")
print("Total categories manquantes: %d" % total_missing_cats)

print()
print("=== ACTES MANQUANTS (niveau 3) ===")
total_missing = 0
found_count = 0
for p_name, p_info in ACTES_ORDER.items():
    for cat, acts in p_info["acts"].items():
        for act in acts:
            act_norm = normalize(act)
            if act_norm in db_acts:
                found_count += 1
            else:
                print("  MANQUANT [%s] [%s]: %s" % (p_name, cat, act))
                total_missing += 1

print()
print("Actes trouves dans la DB: %d" % found_count)
print("Actes manquants:          %d" % total_missing)
print("Total actes DB (lvl3):    %d" % len(db_acts))
print("Total sous-svcs DB (lvl2):%d" % len(db_subgroups))
print("Total piliers DB:         %d" % len(db_piliers))
