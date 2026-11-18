import os
import re
import json

REF_DIR = r"e:\projets\MedcareConnect-main\MedcareConnect-main\documents\referentiel"
OUT_DIR = r"e:\projets\MedcareConnect-main\MedcareConnect-main\documents\referentiel\exports_json"
TOOL_DIR = r"e:\projets\MedcareConnect-main\catalog_import_tool"
os.makedirs(OUT_DIR, exist_ok=True)

pillars_cfg = [
    {
        "id": 1,
        "slug": "biologie-medicale",
        "name": "Biologie médicale",
        "file": "Referentiel_Biologie_MedCare (1).html",
        "ambulance_mode": False
    },
    {
        "id": 2,
        "slug": "imagerie-medicale",
        "name": "Imagerie médicale",
        "file": "Referentiel_Imagerie_MedCare.html",
        "ambulance_mode": False
    },
    {
        "id": 3,
        "slug": "explorations-fonctionnelles",
        "name": "Explorations fonctionnelles",
        "file": "Referentiel_Explorations_MedCare.html",
        "ambulance_mode": False
    },
    {
        "id": 4,
        "slug": "ambulance-medicalisee",
        "name": "Ambulance médicalisée",
        "file": "Referentiel_Ambulance_MedCare.html",
        "ambulance_mode": True  # JUSTE LE LEXIQUE D'INTENTION
    },
    {
        "id": 5,
        "slug": "soins-specialises",
        "name": "Soins spécialisés",
        "file": "Referentiel_Soins_Specialises_MedCare.html",
        "ambulance_mode": False
    },
    {
        "id": 6,
        "slug": "soins-dentaires",
        "name": "Soins dentaires",
        "file": "Referentiel_Dentaire_MedCare.html",
        "ambulance_mode": False
    }
]

master_export = {
    "plateforme": "MedCare Connect",
    "version": "1.0",
    "description": "Référentiel officiel standardisé des 6 piliers MedCare avec lexique d'intention",
    "piliers": {}
}

lexique_intention_global = {}

for p in pillars_cfg:
    fpath = os.path.join(REF_DIR, p["file"])
    with open(fpath, "r", encoding="utf-8") as f:
        html_txt = f.read()
    
    m = re.search(r'var DATA\s*=\s*(\[.*?\]);', html_txt, re.DOTALL)
    if not m:
        print(f"ERREUR: Pas de var DATA dans {p['file']}")
        continue
    
    raw_data = json.loads(m.group(1))
    
    # Save individual JSON
    clean_slug = p["slug"].replace("-", "_")
    single_out_path = os.path.join(OUT_DIR, f"{clean_slug}.json")
    
    if p["ambulance_mode"]:
        # Pour l'ambulance : SEULEMENT le lexique d'intention
        lexique_ambulance = []
        for item in raw_data:
            service_type = item.get("type_service", "")
            prestation = item.get("acte_standardise", "")
            variantes = item.get("lexique_intention", [])
            lexique_ambulance.append({
                "type_service": service_type,
                "prestation_cible": prestation,
                "intentions_synonymes": variantes
            })
            for v in variantes:
                lexique_intention_global[v.lower().strip()] = {
                    "pilier": "Ambulance médicalisée",
                    "pilier_slug": "ambulance-medicalisee",
                    "service": service_type,
                    "prestation": prestation
                }
        
        ambulance_export = {
            "pilier_id": p["id"],
            "pilier_slug": p["slug"],
            "pilier_nom": p["name"],
            "lexique_intention_uniquement": True,
            "remarque": "Catalogue des actes inchangé sur la plateforme (déjà conforme). Utilisation exclusive du lexique d'intention pour l'aiguillage.",
            "nb_intentions_couvertes": len(lexique_ambulance),
            "lexique_intention": lexique_ambulance
        }
        with open(single_out_path, "w", encoding="utf-8") as f:
            json.dump(ambulance_export, f, ensure_ascii=False, indent=2)
            
        master_export["piliers"][p["slug"]] = ambulance_export
        print(f"Exporté {p['name']} (Lexique d'intention uniquement) : {len(lexique_ambulance)} intentions -> {single_out_path}")
    else:
        # Piliers 1, 2, 3, 5, 6
        actes_list = []
        for item in raw_data:
            actes_list.append({
                "type_service": item.get("type_service", ""),
                "code": item.get("code", ""),
                "acte_standardise": item.get("acte_standardise", ""),
                "actes_composants": item.get("actes_composants", []),
                "lexique_intention": item.get("lexique_intention", []),
                "tarif_fcfa_indicatif": item.get("tarif_fcfa", None)
            })
            for v in item.get("lexique_intention", []):
                lexique_intention_global[v.lower().strip()] = {
                    "pilier": p["name"],
                    "pilier_slug": p["slug"],
                    "service": item.get("type_service", ""),
                    "acte": item.get("acte_standardise", "")
                }
        
        pillar_export = {
            "pilier_id": p["id"],
            "pilier_slug": p["slug"],
            "pilier_nom": p["name"],
            "lexique_intention_uniquement": False,
            "nb_actes": len(actes_list),
            "actes": actes_list
        }
        with open(single_out_path, "w", encoding="utf-8") as f:
            json.dump(pillar_export, f, ensure_ascii=False, indent=2)
            
        master_export["piliers"][p["slug"]] = pillar_export
        print(f"Exporté {p['name']} : {len(actes_list)} actes -> {single_out_path}")

# Export master file
master_path = os.path.join(OUT_DIR, "referentiel_6piliers_medcare.json")
with open(master_path, "w", encoding="utf-8") as f:
    json.dump(master_export, f, ensure_ascii=False, indent=2)
print(f"\n--> Master export enregistré dans {master_path}")

# Copy master to catalog_import_tool and root
tool_master = os.path.join(TOOL_DIR, "referentiel_6piliers_medcare.json")
with open(tool_master, "w", encoding="utf-8") as f:
    json.dump(master_export, f, ensure_ascii=False, indent=2)

root_master = r"e:\projets\MedcareConnect-main\MedcareConnect-main\referentiel_6piliers_medcare.json"
with open(root_master, "w", encoding="utf-8") as f:
    json.dump(master_export, f, ensure_ascii=False, indent=2)

# Export complete Lexique d'Intention
lexique_path = os.path.join(OUT_DIR, "lexique_intention_medcare.json")
with open(lexique_path, "w", encoding="utf-8") as f:
    json.dump(lexique_intention_global, f, ensure_ascii=False, indent=2)
print(f"--> Lexique d'intention global enregistré ({len(lexique_intention_global)} termes) dans {lexique_path}")

lexique_root = r"e:\projets\MedcareConnect-main\MedcareConnect-main\lexique_intention_medcare.json"
with open(lexique_root, "w", encoding="utf-8") as f:
    json.dump(lexique_intention_global, f, ensure_ascii=False, indent=2)

tool_lexique = os.path.join(TOOL_DIR, "lexique_intention_medcare.json")
with open(tool_lexique, "w", encoding="utf-8") as f:
    json.dump(lexique_intention_global, f, ensure_ascii=False, indent=2)
