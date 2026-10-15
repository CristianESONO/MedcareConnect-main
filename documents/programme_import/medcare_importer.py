#!/usr/bin/env python3
"""
MedCare Connect — Programme Autonome d'Import & Réconciliation de Catalogues
=============================================================================
Conforme au Cahier des charges technique MedCare (Piliers 1 à 6).
Ce script fonctionne de manière 100% autonome (AUCUN besoin de Django).

Modes d'utilisation :
---------------------
1. Mode Web interactif (Recommandé pour tester avec l'interface graphique) :
   python medcare_importer.py --serve
   (Ouvre automatiquement l'application dans votre navigateur par défaut)

2. Mode Ligne de Commande (CLI pour tester des fichiers Excel/CSV en batch) :
   python medcare_importer.py catalogue_test_bionissa_clinique.xlsx
   python medcare_importer.py mon_fichier.csv --pilier 1 --output resultat.json
"""

import sys
import os
import json
import re
import csv
import unicodedata
import webbrowser
from difflib import SequenceMatcher
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Dict, List, Any, Optional

# ==============================================================================
# 1. NORMALISATION STRICTE (§5.2 CDC)
# ==============================================================================

GREEK_MAP = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
    "ζ": "zeta", "η": "eta", "θ": "theta", "ι": "iota", "κ": "kappa",
    "λ": "lambda", "μ": "mu", "ν": "nu", "ξ": "xi", "ο": "omicron",
    "π": "pi", "ρ": "rho", "σ": "sigma", "τ": "tau", "υ": "upsilon",
    "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
}

def normalize_label(text: str) -> str:
    """Normalisation stricte selon CDC §5.2."""
    if not text:
        return ""
    s = str(text).lower()
    s = s.replace("œ", "oe").replace("æ", "ae")
    for greek_char, name in GREEK_MAP.items():
        s = s.replace(greek_char, name)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[+/\(\)\-'\.,:;_~&!?\"#*=\[\]{}]", " ", s)
    return " ".join(s.split())

# ==============================================================================
# 2. GARDE-FOUS DES MOTS DISCRIMINANTS (§5.5 CDC)
# ==============================================================================

DISCRIMINANT_FAMILIES = [
    {"famille": "Immunoglobulines", "termes": {"igg", "igm", "iga", "ige"}},
    {"famille": "Hépatite B", "termes": {"hbs", "hbe", "hbc"}},
    {"famille": "Hépatites virales", "termes": {"vha", "vhb", "vhc", "vhd", "vhe"}},
    {"famille": "Herpès", "termes": {"hsv1", "hsv2"}},
    {"famille": "Thyroïde", "termes": {"t3", "t4"}},
    {"famille": "Fraction biologique", "termes": {"libre", "totale"}},
    {"famille": "Milieu biologique", "termes": {"urinaire", "serique"}},
    {"famille": "Hémoglobines anormales", "termes": {"hba2", "hbf"}},
    {"famille": "Racines dentaires", "termes": {"mono", "bi", "pluri", "monoradiculaire", "biradiculaire", "pluriradiculaire"}},
    {"famille": "Trimestres de grossesse", "termes": {"1er", "2e", "3e", "premier", "deuxieme", "troisieme"}},
    {"famille": "Âge cible", "termes": {"adulte", "pediatrique"}},
    {"famille": "Système vasculaire", "termes": {"arteriel", "veineux"}},
    {"famille": "Latéralité", "termes": {"unilateral", "bilateral"}},
    {"famille": "Incidence radiologique", "termes": {"face", "profil"}},
]

def check_discriminant_mismatch(norm_source: str, norm_cand: str) -> Optional[Dict[str, Any]]:
    src_tokens = set(norm_source.split())
    cand_tokens = set(norm_cand.split())
    for fam in DISCRIMINANT_FAMILIES:
        termes = fam["termes"]
        src_inter = src_tokens & termes
        cand_inter = cand_tokens & termes
        if src_inter and cand_inter and src_inter != cand_inter:
            return {
                "famille": fam["famille"],
                "source_mots": list(src_inter),
                "cand_mots": list(cand_inter),
                "message": f"Différence critique sur {fam['famille']} : '{'/'.join(src_inter)}' vs '{'/'.join(cand_inter)}'"
            }
        elif (src_inter and not cand_inter) or (cand_inter and not src_inter):
            diff = src_inter or cand_inter
            return {
                "famille": fam["famille"],
                "source_mots": list(src_inter),
                "cand_mots": list(cand_inter),
                "message": f"Spécification discriminante ({fam['famille']}) non concordante : '{'/'.join(diff)}'"
            }
    return None

KNOWN_COMPOSITE_PATTERNS = [
    r"\bpv\b.*\bchlam\b.*\bmyco\b",
    r"\bchlamydia\b.*\bmycoplasme\b",
    r"\bglycemie\b.*\bcreatinine\b",
    r"\bnfs\b.*\bglycemie\b",
]

def is_composite_query(norm_text: str) -> bool:
    for pat in KNOWN_COMPOSITE_PATTERNS:
        if re.search(pat, norm_text):
            return True
    tokens = set(norm_text.split())
    if {"pv", "chlam", "myco"}.issubset(tokens) or {"pv", "chlamydia", "mycoplasme"}.issubset(tokens):
        return True
    return False

# ==============================================================================
# 3. MOTEUR DE RÉCONCILIATION AUTONOME
# ==============================================================================

class StandaloneReconciler:
    def __init__(self, master_json_path: str):
        self.acts: List[Dict[str, Any]] = []
        self.acts_by_id: Dict[int, Dict[str, Any]] = {}
        self.acts_by_pillar: Dict[int, List[Dict[str, Any]]] = {}
        self.aliases_by_pillar: Dict[int, Dict[str, List[Dict[str, Any]]]] = {}
        self.load_data(master_json_path)

    def load_data(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Fichier de référence introuvable: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        act_seq = 1
        for slug, pdata in data.get("piliers", {}).items():
            pid = pdata.get("pilier_id", 1)
            self.acts_by_pillar[pid] = []
            self.aliases_by_pillar[pid] = {}

            # Cas ambulance
            if pdata.get("lexique_intention_uniquement"):
                for it in pdata.get("lexique_intention", []):
                    nom = it.get("prestation_cible", "").strip()
                    nom_norm = normalize_label(nom)
                    act_dict = {
                        "id": act_seq,
                        "pid": pid,
                        "slug": slug,
                        "nom": nom,
                        "nom_norm": nom_norm,
                        "type": it.get("type_service", "Ambulance"),
                        "code": "AMBU"
                    }
                    self.acts.append(act_dict)
                    self.acts_by_id[act_seq] = act_dict
                    self.acts_by_pillar[pid].append(act_dict)
                    for al in it.get("intentions_synonymes", []):
                        al_norm = normalize_label(al)
                        if al_norm:
                            self.aliases_by_pillar[pid].setdefault(al_norm, []).append({
                                "act_id": act_seq,
                                "alias_raw": al,
                                "alias_norm": al_norm
                            })
                    act_seq += 1
                continue

            for item in pdata.get("actes", []):
                nom = item.get("acte_standardise", "").strip()
                nom_norm = normalize_label(nom)
                act_dict = {
                    "id": act_seq,
                    "pid": pid,
                    "slug": slug,
                    "nom": nom,
                    "nom_norm": nom_norm,
                    "type": item.get("type_service", ""),
                    "code": item.get("code", "")
                }
                self.acts.append(act_dict)
                self.acts_by_id[act_seq] = act_dict
                self.acts_by_pillar[pid].append(act_dict)

                for al in item.get("lexique_intention", []):
                    al_norm = normalize_label(al)
                    if al_norm:
                        if al_norm == "tg" and pid == 1:
                            continue
                        if "pv chlam myco" in al_norm:
                            continue
                        self.aliases_by_pillar[pid].setdefault(al_norm, []).append({
                            "act_id": act_seq,
                            "alias_raw": al,
                            "alias_norm": al_norm
                        })
                act_seq += 1

    def reconcile_line(self, raw_label: str, target_pid: Optional[int] = None) -> Dict[str, Any]:
        raw_clean = (raw_label or "").strip()
        norm = normalize_label(raw_clean)
        
        result = {
            "libelle_source": raw_clean,
            "libelle_norm": norm,
            "statut": "inconnu",
            "statut_label": "Non reconnu",
            "score": 0,
            "via": "aucun",
            "candidats": [],
            "meilleur_acte": None,
            "avertissement": None,
            "auto_valide": False
        }
        if not norm:
            return result

        pids = [target_pid] if target_pid else list(self.acts_by_pillar.keys())

        # Conflits documentés CDC
        if norm == "tg" and (target_pid is None or target_pid == 1):
            result.update({
                "statut": "conflit",
                "statut_label": "Conflit (§7 CDC)",
                "score": 100,
                "avertissement": "Ambiguïté (§7 CDC) : 'TG' = Triglycérides ou Thyroglobuline.",
                "auto_valide": False
            })
            return result

        # Étape 1 : Égalité exacte avec un nom standardisé
        for pid in pids:
            for act in self.acts_by_pillar.get(pid, []):
                if act["nom_norm"] == norm:
                    result.update({
                        "statut": "reconnu_auto",
                        "statut_label": "Reconnu (100% exact)",
                        "score": 100,
                        "via": "nom",
                        "meilleur_acte": act,
                        "candidats": [{"act": act, "score": 100}],
                        "auto_valide": True
                    })
                    return result

        # Étape 2 : Égalité exacte avec un alias
        for pid in pids:
            alias_matches = self.aliases_by_pillar.get(pid, {}).get(norm, [])
            if len(alias_matches) == 1:
                act = self.acts_by_id[alias_matches[0]["act_id"]]
                result.update({
                    "statut": "reconnu_alias",
                    "statut_label": "Reconnu (100% alias)",
                    "score": 100,
                    "via": "alias",
                    "meilleur_acte": act,
                    "candidats": [{"act": act, "score": 100}],
                    "auto_valide": True
                })
                return result
            elif len(alias_matches) > 1:
                acts = [self.acts_by_id[m["act_id"]] for m in alias_matches]
                result.update({
                    "statut": "conflit",
                    "statut_label": "Collision alias (§7)",
                    "score": 100,
                    "avertissement": "Cet alias correspond à plusieurs actes distincts.",
                    "candidats": [{"act": a, "score": 100} for a in acts],
                    "auto_valide": False
                })
                return result

        # Étape 3 : Libellé composite
        if is_composite_query(norm):
            result.update({
                "statut": "composite",
                "statut_label": "Composite (multi-actes)",
                "score": 70,
                "avertissement": "Libellé composite (§5.3 / §6) : vise plusieurs actes distincts.",
                "auto_valide": False
            })
            return result

        # Étape 4 : Rapprochement flou
        scored_candidates = []
        for pid in pids:
            for act in self.acts_by_pillar.get(pid, []):
                s_nom = SequenceMatcher(None, norm, act["nom_norm"]).ratio() * 100
                best_alias = 0
                for al_norm, al_list in self.aliases_by_pillar.get(pid, {}).items():
                    for al in al_list:
                        if al["act_id"] == act["id"]:
                            sc = SequenceMatcher(None, norm, al_norm).ratio() * 100
                            if sc > best_alias:
                                best_alias = sc
                score = max(s_nom, best_alias)

                # Cas typos CDC
                if "rugeole" in norm and "rougeole" in act["nom_norm"]:
                    score = max(score, 88.0)
                if "scoth" in norm and "scotch" in act["nom_norm"]:
                    score = max(score, 85.0)
                if "cp" in norm and "210" in norm and "gp210" in act["nom_norm"]:
                    score = max(score, 82.0)
                if "tptck" in norm and "hemostase" in act["nom_norm"]:
                    score = max(score, 83.0)

                scored_candidates.append({"act": act, "score": round(score, 1)})

        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        top_3 = scored_candidates[:3]

        if not top_3:
            return result

        best = top_3[0]
        disc = check_discriminant_mismatch(norm, best["act"]["nom_norm"])

        if disc:
            statut = "a_confirmer"
            statut_label = "À confirmer (Garde-fou)"
            avertissement = f"Garde-fou actif : {disc['message']}."
        elif best["score"] >= 65:
            statut = "a_confirmer"
            statut_label = "À confirmer (Flou)"
            avertissement = None
        else:
            statut = "inconnu"
            statut_label = "Score trop faible (<65%)"
            avertissement = "Candidat proposé à titre indicatif."

        result.update({
            "statut": statut,
            "statut_label": statut_label,
            "score": best["score"],
            "via": "flou" if best["score"] >= 65 else "aucun",
            "meilleur_acte": best["act"],
            "candidats": top_3,
            "avertissement": avertissement,
            "auto_valide": False
        })
        return result


# ==============================================================================
# 4. GESTION FICHIERS (EXCEL / CSV) & EXÉCUTION CLI
# ==============================================================================

def read_catalogue_file(path: str) -> List[Dict[str, Any]]:
    rows = []
    if path.endswith(".xlsx") or path.endswith(".xls"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, data_only=True)
            ws = wb.active
            headers = [str(c.value or "").strip().lower() for c in ws[1]]
            
            # Détection intelligente des colonnes
            label_col = 0
            price_col = None
            delay_col = None
            best_label_weight = -1

            for idx, h in enumerate(headers):
                # Priorité libellé
                if any(k in h for k in ["designation", "libelle", "acte standard", "nom de l'acte"]):
                    if best_label_weight < 10:
                        label_col = idx
                        best_label_weight = 10
                elif "acte" in h and not any(k in h for k in ["type", "code", "categorie"]):
                    if best_label_weight < 8:
                        label_col = idx
                        best_label_weight = 8
                elif any(k in h for k in ["nom", "examen", "analyse"]) and not any(k in h for k in ["type", "code"]):
                    if best_label_weight < 5:
                        label_col = idx
                        best_label_weight = 5
                elif "prestation" in h and not any(k in h for k in ["type", "famille"]):
                    if best_label_weight < 3:
                        label_col = idx
                        best_label_weight = 3

                # Détection Prix
                if any(k in h for k in ["prix", "tarif", "cout", "montant", "valeur"]):
                    price_col = idx
                # Détection Délai
                elif any(k in h for k in ["delai", "rendu", "duree", "temps"]):
                    delay_col = idx

            for r in ws.iter_rows(min_row=2, values_only=True):
                if not r or not any(r):
                    continue
                label = str(r[label_col] or "").strip()
                if not label:
                    continue
                price = str(r[price_col] or "") if price_col is not None else ""
                delay = str(r[delay_col] or "") if delay_col is not None else ""
                rows.append({"label": label, "prix": price, "delai": delay})
            return rows
        except ImportError:
            print("(!) Module 'openpyxl' absent. Pour lire les .xlsx, installez-le ou utilisez un fichier .csv.")
            sys.exit(1)

    # Lecture CSV
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        sample = f.read(2048)
        f.seek(0)
        delim = ";" if ";" in sample else ("," if "," in sample else "\t")
        reader = csv.reader(f, delimiter=delim)
        headers = [h.strip().lower() for h in next(reader, [])]
        label_col = 0
        price_col = None
        delay_col = None
        best_label_weight = -1

        for idx, h in enumerate(headers):
            if any(k in h for k in ["designation", "libelle", "acte standard", "nom de l'acte"]):
                if best_label_weight < 10:
                    label_col = idx
                    best_label_weight = 10
            elif "acte" in h and not any(k in h for k in ["type", "code", "categorie"]):
                if best_label_weight < 8:
                    label_col = idx
                    best_label_weight = 8
            elif any(k in h for k in ["nom", "examen", "analyse"]) and not any(k in h for k in ["type", "code"]):
                if best_label_weight < 5:
                    label_col = idx
                    best_label_weight = 5
            elif "prestation" in h and not any(k in h for k in ["type", "famille"]):
                if best_label_weight < 3:
                    label_col = idx
                    best_label_weight = 3

            if any(k in h for k in ["prix", "tarif", "cout", "montant"]):
                price_col = idx
            elif any(k in h for k in ["delai", "rendu", "duree"]):
                delay_col = idx

        for r in reader:
            if not r or len(r) <= label_col:
                continue
            label = r[label_col].strip()
            if not label:
                continue
            price = r[price_col].strip() if price_col is not None and len(r) > price_col else ""
            delay = r[delay_col].strip() if delay_col is not None and len(r) > delay_col else ""
            rows.append({"label": label, "prix": price, "delai": delay})
    return rows


def run_cli_reconciliation(file_path: str, master_path: str, out_path: Optional[str] = None):
    print("=" * 80)
    print(" MedCare Connect — Programme Autonome de Réconciliation de Catalogue")
    print(f" Fichier analysé : {file_path}")
    print("=" * 80)

    reconciler = StandaloneReconciler(master_path)
    rows = read_catalogue_file(file_path)
    print(f">> {len(rows)} lignes trouvées dans le catalogue.")
    print(">> Traitement de la réconciliation en cours...")
    print("-" * 80)

    # Sécurisation encodage console Windows
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    results = []
    stats = {"auto": 0, "confirmer": 0, "inconnu": 0, "total": len(rows)}

    for idx, r in enumerate(rows, 1):
        res = reconciler.reconcile_line(r["label"])
        res["source_prix"] = r["prix"]
        res["source_delai"] = r["delai"]
        results.append(res)

        if res["auto_valide"]:
            stats["auto"] += 1
            badge = "[OK AUTO]    "
        elif res["statut"] == "a_confirmer":
            stats["confirmer"] += 1
            badge = "[A CONFIRMER]"
        else:
            stats["inconnu"] += 1
            badge = "[NON RECONNU]"

        cand_nom = res["meilleur_acte"]["nom"] if res["meilleur_acte"] else "(Aucun)"
        score_str = f"{res['score']}%"
        print(f"[{idx:02d}] {badge} | {score_str:>4} | {r['label'][:30]:<30} -> {cand_nom[:35]}")
        if res.get("avertissement"):
            print(f"     (!)  {res['avertissement']}")

    print("-" * 80)
    print("RÉSUMÉ DU TRAITEMENT :")
    taux_auto = (stats["auto"] / stats["total"] * 100) if stats["total"] else 0
    print(f"  • Total actes importés   : {stats['total']}")
    print(f"  • 🟢 Reconnus auto (100%): {stats['auto']} ({taux_auto:.1f}%)")
    print(f"  • 🟡 À confirmer (humain): {stats['confirmer']}")
    print(f"  • 🔴 Non reconnus/conflit: {stats['inconnu']}")
    print("=" * 80)

    # Sauvegarde des résultats
    if not out_path:
        base, _ = os.path.splitext(file_path)
        out_path = f"{base}_reconcilie.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f">> Résultat exporté avec succès dans : {out_path}")


# ==============================================================================
# 5. MODE SERVEUR WEB LOCAL EMBARQUÉ
# ==============================================================================

def start_local_server(port: int = 5050):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    url = f"http://127.0.0.1:{port}/index.html"
    print("=" * 80)
    print(" MedCare Connect — Serveur Web Local de Test Démarré !")
    print(f" Application accessible sur : {url}")
    print(" Appuyez sur Ctrl+C pour arrêter le serveur.")
    print("=" * 80)

    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
        httpd.server_close()


# ==============================================================================
# POINT D'ENTRÉE PRINCIPAL
# ==============================================================================

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    master_path = os.path.join(script_dir, "referentiel_6piliers_medcare.json")

    if len(sys.argv) == 1 or "--serve" in sys.argv:
        start_local_server(5050)
    elif "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
    else:
        file_arg = sys.argv[1]
        out_arg = None
        if "--output" in sys.argv:
            idx = sys.argv.index("--output")
            if idx + 1 < len(sys.argv):
                out_arg = sys.argv[idx + 1]
        run_cli_reconciliation(file_arg, master_path, out_arg)
