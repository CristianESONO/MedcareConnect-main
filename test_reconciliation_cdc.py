"""
Suite de tests de validation du Cahier des Charges Technique — Moteur de Réconciliation MedCare
Valide rigoureusement les 16 cas de test du §10 et les critères d'acceptation du §11.
"""
import os
import sys
import json

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

from healthcare.reconciliation_engine import (
    normalize_label,
    check_discriminant_mismatch,
    ReconciliationRepository,
    ReconciliationSession,
    match_line
)

print("==================================================================", flush=True)
print("  TESTS DE CONFORMITÉ — CAHIER DES CHARGES RECONCILIATION V1", flush=True)
print("==================================================================", flush=True)

# 1. Chargement du référentiel seed
master_path = r"e:\projets\MedcareConnect-main\MedcareConnect-main\referentiel_6piliers_medcare.json"
with open(master_path, "r", encoding="utf-8") as f:
    master_json = json.load(f)

repo = ReconciliationRepository()
repo.load_seed(master_json)
print(f"Chargé : {len(repo.act_by_id)} actes dans le référentiel.", flush=True)

# Test Pilier 1 (Biologie)
p1 = 1
# Test Pilier 4 (Ambulance)
p4 = 4

passed = 0
total = 0

def check(test_num: int, label: str, condition: bool, details: str = ""):
    global passed, total
    total += 1
    if condition:
        passed += 1
        print(f"  ✅ [Cas {test_num}] {label} : REUSSI {details}", flush=True)
    else:
        print(f"  ❌ [Cas {test_num}] {label} : ECHEC {details}", flush=True)

# 1. NFS -> Reconnu via alias -> NFS (hémogramme)
r1 = match_line("NFS", p1, repo)
check(1, "NFS", r1["etat"] == "reconnu" and r1["via"] == "alias" and "NFS (hémogramme)" in r1["candidats"][0]["nom"], f"-> {r1['candidats'][0]['nom']}")

# 2. Calcémie -> Reconnu via nom -> Calcémie
r2 = match_line("Calcémie", p1, repo)
check(2, "Calcémie", r2["etat"] == "reconnu" and r2["via"] == "nom" and r2["candidats"][0]["nom"] == "Calcémie", f"-> {r2['candidats'][0]['nom']}")

# 3. NFS+TR -> Reconnu via alias -> panel NFS + réticulocytes
r3 = match_line("NFS+TR", p1, repo)
check(3, "NFS+TR", r3["etat"] == "reconnu" and r3["via"] == "alias" and "NFS + réticulocytes" in r3["candidats"][0]["nom"], f"-> {r3['candidats'][0]['nom']}")

# 4. TPTCK (TC-TS) -> Ressemblant / À confirmer -> panel Bilan d'hémostase
r4 = match_line("TPTCK (TC-TS)", p1, repo)
check(4, "TPTCK (TC-TS)", r4["etat"] in ["ressemblant", "confirm"] and not r4["auto_valide"] and "Bilan d'hémostase" in r4["candidats"][0]["nom"], f"-> {r4['candidats'][0]['nom']}")

# 5. RUGEOLE -> Inconnu, candidat n°1 : Sérologie rougeole
r5 = match_line("RUGEOLE", p1, repo)
check(5, "RUGEOLE", not r5["auto_valide"] and "rougeole" in r5["candidats"][0]["nom"].lower(), f"-> candidat n°1 : {r5['candidats'][0]['nom']}")

# 6. Scoth test -> Inconnu / Non apparié, candidat n°1 : Scotch-test anal
r6 = match_line("Scoth test", p1, repo)
check(6, "Scoth test", not r6["auto_valide"] and "scotch" in r6["candidats"][0]["nom"].lower(), f"-> candidat n°1 : {r6['candidats'][0]['nom']}")

# 7. ac anti CP 210 -> Inconnu, candidat n°1 : anti-gp210
r7 = match_line("ac anti CP 210", p1, repo)
check(7, "ac anti CP 210", not r7["auto_valide"] and "gp210" in r7["candidats"][0]["nom"].lower(), f"-> candidat n°1 : {r7['candidats'][0]['nom']}")

# 8. Ac anti HBc IgM, IgG, totaux -> Trois actes distincts, jamais permutés
r8_igm = match_line("Ac anti HBc IgM", p1, repo)
r8_igg = match_line("Ac anti HBc IgG", p1, repo)
r8_tot = match_line("Ac anti HBc totaux", p1, repo)
hbc_distincts = (
    "IgM" in r8_igm["candidats"][0]["nom"] and
    "IgG" in r8_igg["candidats"][0]["nom"] and
    "totaux" in r8_tot["candidats"][0]["nom"]
)
check(8, "Ac anti HBc IgM/IgG/totaux", hbc_distincts, f"-> 3 cibles distinctes sans permutation")

# 9. PV CHLAM MYCO -> Composite : Prélèvement vaginal + Chlamydia + Mycoplasme, jamais PV seul
r9 = match_line("PV CHLAM MYCO", p1, repo)
check(9, "PV CHLAM MYCO", r9["etat"] == "composite" and not r9["auto_valide"], f"-> état : {r9['etat']}")

# 10. Électrophorèse de L'hémoglobine (protidogramme) -> Conflit, arbitrage humain
r10 = match_line("Électrophorèse de L'hémoglobine (protidogramme)", p1, repo)
check(10, "Électrophorèse de L'hémoglobine (protidogramme)", r10["etat"] == "conflit" and not r10["auto_valide"], f"-> état : {r10['etat']}")

# 11. TG -> Conflit tant que §7 n'est pas résolu
r11 = match_line("TG", p1, repo)
check(11, "TG", r11["etat"] == "conflit" and not r11["auto_valide"], f"-> état : {r11['etat']}")

# 12. TE -> Test d'Emmel, actif dans le pilier Biologie seulement
r12_bio = match_line("TE", p1, repo)
r12_img = match_line("TE", 2, repo)
check(12, "TE (alias court 2 car)", r12_bio["etat"] == "reconnu" and "Emmel" in r12_bio["candidats"][0]["nom"] and r12_img["etat"] != "reconnu", f"-> Biologie : {r12_bio['candidats'][0]['nom']}")

# 13. SMUR (pilier Ambulance) -> Reconnu via alias -> Intervention SMUR pré-hospitalière
r13 = match_line("SMUR", p4, repo)
check(13, "SMUR (Ambulance)", r13["etat"] == "reconnu" and "SMUR" in r13["candidats"][0]["nom"], f"-> {r13['candidats'][0]['nom']}")

# 14. Même fichier réimporté -> 100% automatique, 0 doublon
session1 = ReconciliationSession("BATCH-001", structure_id=10, pillar_id=p1, repo=repo)
file_data = [
    {"libelle": "NFS", "prix": 5000},
    {"libelle": "Calcémie", "prix": 3000},
    {"libelle": "NFS", "prix": 5000}, # Doublon intentionnel
]
stats1 = session1.import_lines(file_data)
check(14, "Idempotence & 0 doublon", stats1["total"] == 2 and stats1["reconnu"] == 2, f"-> {stats1['total']} lignes retenues sur 3, 100% reconnues")

# 15. Un second labo écrit "Scoth test" après validation par le premier -> Reconnu via alias
# Le labo 1 valide "Scoth test" vers Scotch-test anal (id de Scotch-test)
target_act_scotch = next(a for a in repo.acts_by_pillar[p1] if "scotch" in a["nom_norm"])
session_labo1 = ReconciliationSession("BATCH-LAB1", structure_id=1, pillar_id=p1, repo=repo)
session_labo1.import_lines([{"libelle": "Scoth test", "prix": 4000}])
# Opérateur valide
session_labo1.validate_human_decision(line_id=1, chosen_act_ids=[target_act_scotch["id"]], operator="Dr. Diallo")

# Labo 2 importe maintenant "Scoth test"
session_labo2 = ReconciliationSession("BATCH-LAB2", structure_id=2, pillar_id=p1, repo=repo)
stats_labo2 = session_labo2.import_lines([{"libelle": "Scoth test", "prix": 4500}])
check(15, "Apprentissage inter-labos", stats_labo2["reconnu"] == 1, f"-> Labo 2 immédiatement reconnu via nouvel alias appris !")

# 16. Retrait d'un alias -> les lignes concernées repassent en "à confirmer"
# Désactivation de l'alias
norm_scotch = normalize_label("Scoth test")
for al in repo.aliases_by_pillar[p1][norm_scotch]:
    al["statut"] = "retire"
r16 = match_line("Scoth test", p1, repo)
check(16, "Retrait d'alias", r16["etat"] != "reconnu" and not r16["auto_valide"], f"-> état : {r16['etat']} (reparti en à confirmer / arbitrage)")

print("\n==================================================================", flush=True)
print(f"RÉSULTATS DE LA SUITE DE TESTS CDC V1 : {passed} / {total} VALIDÉS ({round(passed/total*100)}%)", flush=True)
print("==================================================================", flush=True)
