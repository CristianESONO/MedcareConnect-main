import os
import sys
import json
import django
from django.db import transaction

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medcare_connect.settings')
django.setup()

from healthcare.models import ServiceMedical, ActeMedical

def normalize(s):
    if not s:
        return ""
    return s.strip().lower().replace("’", "'").replace(" ", "")

with open(r"e:\projets\MedcareConnect-main\MedcareConnect-main\referentiel_6piliers_medcare.json", "r", encoding="utf-8") as f:
    master = json.load(f)

print("================================================================", flush=True)
print("  MISE A JOUR DU CATALOGUE DES ACTES MEDCARE (COMPLEMENT)", flush=True)
print("================================================================", flush=True)

pillars_to_update = [
    ("biologie-medicale", "Biologie médicale"),
    ("imagerie-medicale", "Imagerie médicale"),
    ("explorations-fonctionnelles", "Explorations fonctionnelles"),
    ("soins-specialises", "Soins spécialisés"),
    ("soins-dentaires", "Soins dentaires")
]

grand_total_created = 0
grand_total_cats_created = 0

with transaction.atomic():
    for slug, label in pillars_to_update:
        try:
            svc = ServiceMedical.objects.get(slug=slug)
        except ServiceMedical.DoesNotExist:
            svc = ServiceMedical.objects.filter(name__icontains=label.split()[0]).first()
        
        if not svc:
            print(f"⚠️ Pilier introuvable en DB: {slug}", flush=True)
            continue

        print(f"\n--- Traitement pilier : {svc.name} (id={svc.id}) ---", flush=True)
        
        pillar_data = master["piliers"].get(slug, {})
        actes = pillar_data.get("actes", [])
        
        # Existing acts & categories for this pillar
        cats_cache = {}
        for c in ActeMedical.objects.filter(service_medical_category=svc, level=2):
            cats_cache[normalize(c.name)] = c
            
        acts_cache = {}
        for a in ActeMedical.objects.filter(service_medical_category=svc, level=3):
            acts_cache[normalize(a.name)] = a
            
        created_cats_count = 0
        created_acts_count = 0

        for item in actes:
            cat_name = (item.get("type_service") or "Actes généraux").strip()
            act_name = item.get("acte_standardise", "").strip()
            
            if not act_name:
                continue
                
            # 1. Catégorie (Level 2)
            cat_norm = normalize(cat_name)
            cat_obj = cats_cache.get(cat_norm)
            if not cat_obj:
                cat_obj, c_created = ActeMedical.objects.get_or_create(
                    name=cat_name,
                    service_medical_category=svc,
                    level=2,
                    defaults={
                        "parent_service": None,
                        "description": f"Catégorie {cat_name} du pilier {svc.display_name}",
                        "is_active": True
                    }
                )
                cats_cache[cat_norm] = cat_obj
                if c_created:
                    created_cats_count += 1
                    
            # 2. Acte (Level 3)
            act_norm = normalize(act_name)
            if act_norm not in acts_cache:
                raw_code = item.get("code")
                safe_code = None
                if raw_code and not ActeMedical.objects.filter(code=raw_code).exists():
                    safe_code = raw_code
                    
                desc_parts = []
                if item.get("actes_composants"):
                    desc_parts.append(f"Composants: {', '.join(item['actes_composants'])}")
                if item.get("lexique_intention"):
                    desc_parts.append(f"Variantes: {', '.join(item['lexique_intention'][:5])}")
                desc = " | ".join(desc_parts) if desc_parts else ""

                act_obj, a_created = ActeMedical.objects.get_or_create(
                    name=act_name,
                    service_medical_category=svc,
                    parent_service=cat_obj,
                    defaults={
                        "level": 3,
                        "code": safe_code,
                        "description": desc,
                        "is_active": True
                    }
                )
                acts_cache[act_norm] = act_obj
                if a_created:
                    created_acts_count += 1

        print(f"  Catégories créées (lvl 2) : {created_cats_count}", flush=True)
        print(f"  Actes créés (lvl 3)       : {created_acts_count}", flush=True)
        print(f"  Total actes DB pilier     : {ActeMedical.objects.filter(service_medical_category=svc, level=3).count()}", flush=True)
        
        grand_total_cats_created += created_cats_count
        grand_total_created += created_acts_count

print("\n================================================================", flush=True)
print(f"RÉSULTAT GLOBAL :", flush=True)
print(f"  - Nouvelles catégories ajoutées (lvl 2) : {grand_total_cats_created}", flush=True)
print(f"  - Nouveaux actes ajoutés (lvl 3)        : {grand_total_created}", flush=True)
print(f"  - Total d'actes niveau 3 dans la DB     : {ActeMedical.objects.filter(level=3).count()}", flush=True)
print("  - Pilier Ambulance médicalisée          : NON MODIFIÉ (Lexique d'intention uniquement)", flush=True)
print("================================================================", flush=True)
