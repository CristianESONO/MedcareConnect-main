#!/usr/bin/env python3
"""
MedCare Connect — Programme Autonome d'Import & Réconciliation de Catalogues
=============================================================================
Conforme au Manuel d'Architecture Onboarding MedCare (Octobre 2026).
Fonctionne de manière 100% autonome et intègre le moteur medcare_matching.

Modes d'utilisation :
---------------------
1. Mode Web local (Recommandé pour tester avec l'interface graphique) :
   python medcare_importer.py --serve
   (Ouvre automatiquement le Portail Hub dans votre navigateur par défaut)

2. Mode Ligne de Commande (CLI pour tester des fichiers Excel/ODS/CSV en batch) :
   python medcare_importer.py ACTES_ET_TARIFICATIONS.ods
   python medcare_importer.py mon_fichier.xlsx --pilier img --output resultat.json
   python medcare_importer.py --test
"""

import sys
import os
import json
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Optional

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from medcare_matching import ReconciliationEngine

def run_cli_reconciliation(file_path: str, ref_path: str, output_path: Optional[str] = None, pilier: Optional[str] = None, rule: str = 'V1'):
    if not os.path.exists(file_path):
        print(f"❌ Erreur : Fichier introuvable '{file_path}'")
        sys.exit(1)

    print("=" * 80)
    print(f" MEDCARE CONNECT — RÉCONCILIATION DU FICHIER : {os.path.basename(file_path)}")
    print("=" * 80)
    print(f"• Fichier source : {file_path}")
    print(f"• Référentiel    : {ref_path}")
    print(f"• Règle moteur   : {rule} ({'Prudente' if rule == 'V1' else 'Forme élargie'})")

    engine = ReconciliationEngine(ref_path)
    result = engine.reconcile_file(file_path, default_pillar=pilier, rule=rule)
    s = result["summary"]

    print("\n" + "-" * 80)
    print(" 📊 SYNTHÈSE GLOBALE DE L'INGESTION & DU RAPPROCHEMENT")
    print("-" * 80)
    print(f"  • Lignes totales lues        : {s['total_lines']} (dont {s['total_rows']} lignes brutes)")
    print(f"  • Rubriques / Sections vues  : {len(s['sections'])} -> {', '.join(s['sections'])}")
    print(f"  • Actes médicaux extraits    : {s['actes_count']}")
    print(f"    🟢 Reconnus automatiquement: {s['reconnus']} ({round(s['reconnus']/s['actes_count']*100, 1)}%)")
    print(f"    🟡 À confirmer (doutes)    : {s['a_confirmer']} ({round(s['a_confirmer']/s['actes_count']*100, 1)}%)")
    print(f"    🔴 Inconnus / Hors réf.    : {s['inconnus']} ({round(s['inconnus']/s['actes_count']*100, 1)}%)")
    print(f"  • Prix manquants (non 0 FCFA): {s['prix_manquants']}")
    print(f"  • Anomalies prix (>4x médian): {s['prix_anomalies']}")

    print("\n" + "-" * 80)
    print(" 🔍 EXTRAIT DES DÉCISIONS PAR LIGNE")
    print("-" * 80)
    print(f"{'Lig':<4} | {'Libellé source':<32} | {'Statut':<12} | {'Prix':<10} | {'Acte MedCare retenu / Explication'}")
    print("-" * 80)

    for l in result["lines"]:
        if l["kind"] != "acte":
            continue
        status_icon = "🟢" if l["issue"] == "reconnu" else ("🟡" if l["issue"] == "a_confirmer" else "🔴")
        p = l["price"]
        p_str = f"{p['value']} F" if p.get("value") is not None else (p.get("statut") or "—")
        if p.get("statut") == "anomalie":
            p_str += " ⚠️"

        cand = l.get("candidat_retenu")
        act_name = cand["acte"]["name"] if cand else "Aucun"
        exp = l.get("explication", "")

        lbl = l["label"]
        if len(lbl) > 30:
            lbl = lbl[:29] + "…"

        info = f"{act_name} ({exp})" if l["issue"] != "reconnu" else act_name
        if len(info) > 45:
            info = info[:44] + "…"

        print(f"{l['num']:<4} | {lbl:<32} | {status_icon} {l['issue']:<9} | {p_str:<10} | {info}")

    # Export
    out_file = output_path or f"{os.path.splitext(file_path)[0]}_reconcilie.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print(f"✓ Rapport complet et données d'audit enregistrés dans : {out_file}")
    print("=" * 80)

def start_local_server(port: int = 5050, host: str = "0.0.0.0"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    server_address = (host, port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    display_host = "127.0.0.1" if host == "0.0.0.0" else host
    url = f"http://{display_host}:{port}/index.html"
    print("=" * 80)
    print(" MedCare Connect — Serveur Web Local de Test Démarré !")
    print(f" Écoute sur : http://{host}:{port}/")
    print(f" Portail accessible sur : {url}")
    print(" Appuyez sur Ctrl+C pour arrêter le serveur.")
    print("=" * 80)

    try:
        if host in ("127.0.0.1", "localhost", "0.0.0.0"):
            webbrowser.open(url)
    except Exception:
        pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
        httpd.server_close()

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ref_path = os.path.join(script_dir, "referentiel_onboarding.json")
    if not os.path.exists(ref_path):
        ref_path = os.path.join(script_dir, "referentiel_6piliers_medcare.json")

    if "--test" in sys.argv:
        from test_onboarding import run_tests
        run_tests()
        sys.exit(0)

    if "--serve" in sys.argv:
        port_val = 5050
        host_val = "0.0.0.0"
        if "--port" in sys.argv:
            idx = sys.argv.index("--port")
            if idx + 1 < len(sys.argv):
                port_val = int(sys.argv[idx + 1])
        start_local_server(port=port_val, host=host_val)
    elif len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        file_arg = sys.argv[1]
        out_arg = None
        if "--output" in sys.argv:
            idx = sys.argv.index("--output")
            if idx + 1 < len(sys.argv):
                out_arg = sys.argv[idx + 1]
        pilier_arg = None
        if "--pilier" in sys.argv:
            idx = sys.argv.index("--pilier")
            if idx + 1 < len(sys.argv):
                pilier_arg = sys.argv[idx + 1]
        rule_arg = "V2" if "--v2" in sys.argv else "V1"
        run_cli_reconciliation(file_arg, ref_path, out_arg, pilier_arg, rule_arg)
    else:
        # Par défaut sans argument : propose le menu
        print("Usage:")
        print("  python medcare_importer.py --serve                     (lance le serveur web)")
        print("  python medcare_importer.py --test                      (lance la suite de tests)")
        print("  python medcare_importer.py ACTES_ET_TARIFICATIONS.ods  (réconcilie en CLI)")
        print("  python medcare_importer.py mon_fichier.xlsx --pilier img")
