import os
import re
import json

ref_dir = r"e:\projets\MedcareConnect-main\MedcareConnect-main\documents\referentiel"
files = [
    ("Biologie médicale", "Referentiel_Biologie_MedCare (1).html"),
    ("Imagerie médicale", "Referentiel_Imagerie_MedCare.html"),
    ("Explorations fonctionnelles", "Referentiel_Explorations_MedCare.html"),
    ("Ambulance médicalisée", "Referentiel_Ambulance_MedCare.html"),
    ("Soins spécialisés", "Referentiel_Soins_Specialises_MedCare.html"),
    ("Soins dentaires", "Referentiel_Dentaire_MedCare.html"),
]

for pillar_name, fname in files:
    fpath = os.path.join(ref_dir, fname)
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(r'var DATA\s*=\s*(\[.*?\]);', content, re.DOTALL)
    if m:
        data = json.loads(m.group(1))
        print(f"=== {pillar_name} ({fname}) ===")
        print(f"Total entries: {len(data)}")
        if data:
            print(f"Sample item keys: {list(data[0].keys())}")
            print(f"Sample item: {data[0]}")
    else:
        print(f"=== {pillar_name} ({fname}) : NO var DATA found! ===")
