import os
import sys
import json
import django

sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medcare_connect.settings')
django.setup()

from healthcare.models import ServiceMedical, ActeMedical

def normalize(s):
    if not s:
        return ""
    return s.strip().lower().replace("’", "'").replace(" ", "")

# Load the master export
with open(r"e:\projets\MedcareConnect-main\MedcareConnect-main\referentiel_6piliers_medcare.json", "r", encoding="utf-8") as f:
    master = json.load(f)

print("=== VERIFICATION DES ACTES A METTRE A JOUR (COMPLEMENT) ===")

pillars_to_update = [
    ("biologie-medicale", "Biologie médicale"),
    ("imagerie-medicale", "Imagerie médicale"),
    ("explorations-fonctionnelles", "Explorations fonctionnelles"),
    ("soins-specialises", "Soins spécialisés"),
    ("soins-dentaires", "Soins dentaires")
]

total_to_add = 0
plan = []

for slug, label in pillars_to_update:
    try:
        svc = ServiceMedical.objects.get(slug=slug)
    except ServiceMedical.DoesNotExist:
        # Fallback to name icontains
        svc = ServiceMedical.objects.filter(name__icontains=label.split()[0]).first()
    
    if not svc:
        print(f"ERREUR: Pilier introuvable en DB: {slug} ({label})")
        continue

    # Existing DB acts for this service
    existing_lvl2 = {normalize(a.name): a for a in ActeMedical.objects.filter(service_medical_category=svc, level=2)}
    existing_lvl3 = {normalize(a.name): a for a in ActeMedical.objects.filter(service_medical_category=svc, level=3)}

    pillar_data = master["piliers"].get(slug, {})
    actes = pillar_data.get("actes", [])
    
    missing_for_pillar = []
    
    for item in actes:
        act_name = item["acte_standardise"].strip()
        cat_name = item.get("type_service", "").strip() or "Actes généraux"
        code = item.get("code", "")
        
        if normalize(act_name) not in existing_lvl3:
            missing_for_pillar.append({
                "act_name": act_name,
                "cat_name": cat_name,
                "code": code,
                "composants": item.get("actes_composants", []),
                "lexique": item.get("lexique_intention", [])
            })
            
    print(f"Pilier: {svc.name} (id={svc.id})")
    print(f"  Total dans référentiel HTML : {len(actes)}")
    print(f"  Déjà dans la DB (lvl 3)      : {len(existing_lvl3)}")
    print(f"  Manquants à insérer (complément) : {len(missing_for_pillar)}")
    total_to_add += len(missing_for_pillar)
    plan.append((svc, missing_for_pillar))

print(f"\nTOTAL GLOBAL D'ACTES A AJOUTER : {total_to_add}")
