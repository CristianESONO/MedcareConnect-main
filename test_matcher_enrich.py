import os
import sys
import django

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medcare_connect.settings')
django.setup()

from healthcare.models import ActeMedical
from healthcare.catalog_excel import ActeCatalogMatcher, _normalize_str
from healthcare.lexique_intention import get_lexique_data

all_acts = list(ActeMedical.objects.filter(is_active=True).select_related("service_medical_category", "parent_service"))
matcher = ActeCatalogMatcher(all_acts)

print(f"Matcher avant enrichissement : {len(matcher.alias_map)} alias en mémoire.")

# Enrichir avec le lexique d'intention
lex_data = get_lexique_data()
enriched_count = 0
for variant, meta in lex_data.items():
    norm_var = _normalize_str(variant)
    target_name = meta.get("acte") or meta.get("prestation")
    if target_name and norm_var:
        norm_target = _normalize_str(target_name)
        target_obj = matcher.by_norm_name.get(norm_target)
        if not target_obj:
            for ref_norm, act in matcher.by_norm_name.items():
                if norm_target in ref_norm or ref_norm in norm_target:
                    target_obj = act
                    break
        if target_obj and norm_var not in matcher.alias_map:
            matcher.alias_map[norm_var] = target_obj
            enriched_count += 1

print(f"Matcher après enrichissement : {len(matcher.alias_map)} alias en mémoire (+{enriched_count} alias ajoutés).")

# Tester la liste exacte des 40 lignes rejetées ou confondues dans le rapport de l'utilisateur
user_lines = [
    "NFS+TR",
    "NFS + FROTIS SANGUIN",
    "Pu 24 h",
    "TE",
    "GSRH",
    "ASDOR",
    "Waler ROSE",
    "Micro albuminurie(albuminurie)",
    "Bandelettes Alb-sucre",
    "TOXO(IgG et IgM)",
    "HIV(PTME)",
    "IGF1",
    "T3",
    "T4",
    "Facteur 8",
    "ac anti CP 210",
    "PSAt",
    "OESTRADIOL",
    "HERPES",
    "Scoth test",
    "cytochimie+bacterio du LCR",
    "Cyto+bacterio du liquide de ponction",
    "Chimie LCR",
    "Ag HBe",
    "AC anti MUSCLE LISSE",
    "AC ANTI MITOCHONDRIE",
    "AC ANTI ENDOMYSIUM",
    "anti LKM",
    "DOSAGE PONDERAL DES Ig",
    "Ac Anti Facteur Intrinsèque",
    "METANEPHRINE",
    "RATH( Anticorps anti Recepteur de l'acethyle choline",
    "RUGEOLE",
    "Ac anti HBc totaux",
    "Ac anti HBc IgG",
    "PROCALCITONINE",
    "OXATURIE",
    "PV CHLAM MYCO",
    "RECHERCHE CHLAMYDIA",
    "RECHERCHE MYCOPLASME"
]

matched = 0
unmatched = 0

print("\n=== TEST DE RECONNAISSANCE SUR LES LIGNES DU RAPPORT ===")
for label in user_lines:
    act, method = matcher.match(raw_name=label)
    if act:
        matched += 1
        print(f"✅ '{label}' -> [{method}] {act.name} ({act.service_medical_category.display_name if act.service_medical_category else ''})")
    else:
        unmatched += 1
        print(f"❌ '{label}' -> NON TROUVE")

print(f"\nTotal reconnus : {matched} / {len(user_lines)} ({round(matched/len(user_lines)*100)}%)")
