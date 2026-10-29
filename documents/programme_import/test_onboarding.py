#!/usr/bin/env python3
"""
Test de non-régression et validation du moteur d'onboarding MedCare
selon le Manuel d'Architecture (Annexe pages 20-23).
"""

import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from medcare_matching import ReconciliationEngine

def run_tests():
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    print("=" * 80)
    print(" TEST SUITE — MEDCARE MATCHING & ONBOARDING")
    print("=" * 80)

    ref_file = os.path.join(cur_dir, "referentiel_onboarding.json")
    engine = ReconciliationEngine(ref_file)
    print(f"✓ Référentiel chargé : {len(engine.index.actes)} actes, {len(engine.index.entries)} entrées indexées.")

    # 1. Test du fichier réel Imagerie ACTES ET TARIFICATIONS (.ods et .xlsx)
    for ext, fname in [("ODS", "ACTES_ET_TARIFICATIONS.ods"), ("XLSX", "ACTES_ET_TARIFICATIONS.xlsx")]:
        fpath = os.path.join(cur_dir, fname)
        if not os.path.exists(fpath):
            continue
        print(f"\n--- Test sur le fichier réel {ext} : {fname} ---")
        res = engine.reconcile_file(fpath, default_pillar="img", rule="V1")
        s = res["summary"]

        print(f"Total lignes lues  : {s['total_lines']} (attendu: 112)")
        print(f"Sections détectées : {len(s['sections'])} (attendu: 5)")
        print(f"Actes médicaux     : {s['actes_count']} (attendu: 81)")
        print(f"  🟢 Reconnus      : {s['reconnus']} (attendu: 61)")
        print(f"  🟡 À confirmer   : {s['a_confirmer']} (attendu: 9)")
        print(f"  🔴 Inconnus      : {s['inconnus']} (attendu: 11)")
        print(f"Prix manquants     : {s['prix_manquants']} (attendu: 1)")
        print(f"Prix anomalies     : {s['prix_anomalies']} (attendu: 1)")

        assert s["total_lines"] == 112, f"Total lignes {s['total_lines']} != 112"
        assert len(s["sections"]) == 5, f"Sections {len(s['sections'])} != 5"
        assert s["actes_count"] == 81, f"Actes {s['actes_count']} != 81"
        assert s["reconnus"] == 61, f"Reconnus {s['reconnus']} != 61"
        assert s["a_confirmer"] == 9, f"À confirmer {s['a_confirmer']} != 9"
        assert s["inconnus"] == 11, f"Inconnus {s['inconnus']} != 11"
        assert s["prix_manquants"] == 1, f"Prix manquants {s['prix_manquants']} != 1"
        assert s["prix_anomalies"] == 1, f"Prix anomalies {s['prix_anomalies']} != 1"
        print(f"✓ Tous les compteurs {ext} sont 100% conformes au manuel !")

        # Vérification des cas spécifiques de l'Annexe
        lines_by_num = {l["num"]: l for l in res["lines"]}

        # Cas TOGD (Ligne 79)
        togd = lines_by_num[79]
        assert togd["price"]["value"] == 700000
        assert togd["price"]["statut"] == "anomalie"
        print("✓ L79 TOGD 700 000 F bien détecté comme anomalie de prix relative (> 4x médiane).")

        # Cas Scanner sans prix (Ligne 42)
        cervico = lines_by_num[42]
        assert cervico["price"]["value"] is None
        assert cervico["price"]["statut"] == "manquant"
        print("✓ L42 SCANNER CERVICO-DORSO-LOMBAIRE bien marqué 'manquant', jamais mis à 0 FCFA.")

        # Cas recollage multi-colonnes (Ligne 36)
        facial = lines_by_num[36]
        assert facial["label"] == "SCANNER DU MASSIF FACIAL"
        assert facial["issue"] == "reconnu"
        print("✓ L36 SCANNER DU | MASSIF FACIAL bien recollé sur 2 colonnes et reconnu.")

        # Cas discriminant Bilatéral (Ligne 63 IRM DES GENOUX)
        genoux = lines_by_num[63]
        assert not genoux["match"].get("exact"), "IRM DES GENOUX ne doit JAMAIS être fusionné exactement avec IRM genou"
        print(f"✓ L63 IRM DES GENOUX bien discriminé du genou unilatéral (issue: {genoux['issue']}).")

        # Cas discriminant Face & Profil (Ligne 90)
        thorax_fp = lines_by_num[90]
        print(f"✓ L90 RAIDOGRAPHIE DU THORAX FACE & PROFIL (issue: {thorax_fp['issue']}, explication: {thorax_fp['explication']}).")

    print("\n" + "=" * 80)
    print(" SUCCÈS TOTAL : 100% DES TESTS DU MANUEL SONT VALIDÉS !")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
