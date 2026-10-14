import os
import sys
import json

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

from healthcare.reconciliation_engine import normalize_label

with open("referentiel_6piliers_medcare.json", "r", encoding="utf-8") as f:
    master = json.load(f)

# Collect all aliases in Biologie
bio_aliases = {}
for act in master["piliers"]["biologie-medicale"]["actes"]:
    nom = act["acte_standardise"]
    nom_norm = normalize_label(nom)
    bio_aliases[nom_norm] = nom
    for al in act.get("lexique_intention", []):
        bio_aliases[normalize_label(al)] = nom

test_terms = [
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
    "anti LKM",
    "DOSAGE PONDERAL DES Ig",
    "Ac Anti Facteur Intrinsèque",
    "METANEPHRINE",
    "RATH( Anticorps anti Recepteur de l'acethyle choline",
    "RUGEOLE",
    "Ac anti HBc totaux",
    "Ac anti HBc IgG",
    "OXATURIE",
    "PV CHLAM MYCO",
    "RECHERCHE CHLAMYDIA",
    "RECHERCHE MYCOPLASME"
]

print("=== VERIFICATION DES TERMES REJETES OU MAL ASSOCIES DANS LE REFERENTIEL ===")
for t in test_terms:
    norm = normalize_label(t)
    match = bio_aliases.get(norm)
    status = "TROUVE" if match else "NON TROUVE"
    print(f"[{status:10}] '{t}' -> {match}")
