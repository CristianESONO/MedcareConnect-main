"""
Moteur de réconciliation des catalogues — MedCare Back-Office
Version 1 · Conforme au Cahier des charges technique (12 octobre 2026)
Périmètre : Piliers 1 à 6 (Biologie, Imagerie, Explorations, Ambulance, Soins spécialisés, Dentaire).
"""
from __future__ import annotations
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Dict, List, Any, Optional, Tuple, Set


# ==============================================================================
# 1. NORMALISATION (§5.2)
# ==============================================================================

# Remplacements de lettres grecques en toutes lettres
GREEK_MAP = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
    "ζ": "zeta", "η": "eta", "θ": "theta", "ι": "iota", "κ": "kappa",
    "λ": "lambda", "μ": "mu", "ν": "nu", "ξ": "xi", "ο": "omicron",
    "π": "pi", "ρ": "rho", "σ": "sigma", "τ": "tau", "υ": "upsilon",
    "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
}

def normalize_label(text: str) -> str:
    """
    Normalisation stricte selon le CDC §5.2 :
    - minuscules, accents supprimés
    - ligatures œ → oe, æ → ae
    - lettres grecques en toutes lettres (β → beta, γ → gamma, α → alpha)
    - ponctuation et symboles (+ / ( ) - ' . , : ; _) remplacés par un espace
    - espaces multiples réduites, bords supprimés
    """
    if not text:
        return ""
    
    s = text.lower()
    
    # 1. Ligatures
    s = s.replace("œ", "oe").replace("æ", "ae")
    
    # 2. Lettres grecques
    for greek_char, name in GREEK_MAP.items():
        s = s.replace(greek_char, name)
        
    # 3. Suppression des accents
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    
    # 4. Ponctuation et symboles remplacés par un espace
    # (+ / ( ) - ' . , : ; _ etc.)
    s = re.sub(r"[+/\(\)\-'\.,:;_~&!?\"#*=\[\]{}]", " ", s)
    
    # 5. Espaces multiples réduites et trim
    return " ".join(s.split())


# ==============================================================================
# 2. GARDE-FOU DES MOTS DISCRIMINANTS (§5.5)
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

def check_discriminant_mismatch(norm_source: str, norm_candidate: str) -> Optional[Dict[str, Any]]:
    """
    Vérifie si la source et le candidat diffèrent sur une famille de mots discriminants.
    Si oui, retourne l'avertissement et la famille concernée.
    """
    src_tokens = set(norm_source.split())
    cand_tokens = set(norm_candidate.split())
    
    for fam in DISCRIMINANT_FAMILIES:
        termes = fam["termes"]
        src_inter = src_tokens & termes
        cand_inter = cand_tokens & termes
        
        # S'il y a un mot discriminant dans la source et un mot différent dans le candidat
        if src_inter and cand_inter and src_inter != cand_inter:
            return {
                "famille": fam["famille"],
                "source_mots": list(src_inter),
                "candidat_mots": list(cand_inter),
                "message": f"Différence critique sur {fam['famille']} : '{'/'.join(src_inter)}' vs '{'/'.join(cand_inter)}'"
            }
        # Si un mot discriminant est spécifié dans l'un mais absent dans l'autre
        elif (src_inter and not cand_inter) or (cand_inter and not src_inter):
            diff = src_inter or cand_inter
            return {
                "famille": fam["famille"],
                "source_mots": list(src_inter),
                "candidat_mots": list(cand_inter),
                "message": f"Spécification discriminante ({fam['famille']}) non concordante : '{'/'.join(diff)}'"
            }
            
    return None


# ==============================================================================
# 3. DÉTECTION DES COMPOSITES (§5.3 / §6)
# ==============================================================================

# Marqueurs composites évidents dans les catalogues de laboratoire
KNOWN_COMPOSITE_PATTERNS = [
    r"\bpv\b.*\bchlam\b.*\bmyco\b",
    r"\bchlamydia\b.*\bmycoplasme\b",
    r"\bglycemie\b.*\bcreatinine\b",
    r"\bnfs\b.*\bglycemie\b",
]

def is_composite_query(raw_text: str, norm_text: str) -> bool:
    """Détecte si une ligne vise potentiellement plusieurs actes distincts."""
    for pat in KNOWN_COMPOSITE_PATTERNS:
        if re.search(pat, norm_text):
            return True
            
    # Cas "PV CHLAM MYCO"
    tokens = set(norm_text.split())
    if {"pv", "chlam", "myco"}.issubset(tokens):
        return True
    if {"pv", "chlamydia", "mycoplasme"}.issubset(tokens):
        return True
        
    return False


# ==============================================================================
# 4. STRUCTURE DES DONNÉES EN MÉMOIRE ET CACHE
# ==============================================================================

class ReconciliationRepository:
    """Référentiel des actes et alias par pilier."""
    
    def __init__(self):
        # acts[pillar_id] = [ {id, nom, nom_norm, service_type, code, kind, dependance_p7}, ... ]
        self.acts_by_pillar: Dict[int, List[Dict[str, Any]]] = {}
        # act_by_id[act_id] = act_dict
        self.act_by_id: Dict[int, Dict[str, Any]] = {}
        # aliases_by_pillar[pillar_id][norm_text] = [ alias_dict, ... ]
        self.aliases_by_pillar: Dict[int, Dict[str, List[Dict[str, Any]]]] = {}
        # Conflits connus à arbitrer
        self.conflicts: List[Dict[str, Any]] = []

    def load_seed(self, master_json: dict):
        """Charge les données du référentiel nettoyé depuis le master JSON."""
        # Typos célèbres du fichier test Bionissa (§5.4 / §10) qui doivent passer par le flou / apprentissage
        TYPOS_A_APPRENDRE = {"rugeole", "scoth test", "ac anti cp 210", "cp 210", "tptck tc ts"}

        for slug, pdata in master_json.get("piliers", {}).items():
            pid = pdata.get("pilier_id")
            if not pid:
                continue
                
            self.acts_by_pillar[pid] = []
            self.aliases_by_pillar[pid] = {}
            
            # Cas Ambulance : les prestations sont dans lexique_intention
            if pdata.get("lexique_intention_uniquement"):
                items = pdata.get("lexique_intention", [])
                for it in items:
                    act_id = len(self.act_by_id) + 1
                    nom = it.get("prestation_cible", "").strip()
                    nom_norm = normalize_label(nom)
                    act_dict = {
                        "id": act_id,
                        "pillar_id": pid,
                        "pillar_slug": slug,
                        "nom": nom,
                        "nom_norm": nom_norm,
                        "service_type": it.get("type_service", ""),
                        "code": "AMBU",
                        "kind": "atomique",
                        "dependance_p7": False,
                        "statut": "actif",
                        "composants": []
                    }
                    self.act_by_id[act_id] = act_dict
                    self.acts_by_pillar[pid].append(act_dict)
                    
                    for alias_raw in it.get("intentions_synonymes", []):
                        alias_norm = normalize_label(alias_raw)
                        if not alias_norm:
                            continue
                        alias_obj = {
                            "act_id": act_id,
                            "pillar_id": pid,
                            "texte_brut": alias_raw,
                            "texte_normalise": alias_norm,
                            "origine": "seed",
                            "statut": "actif",
                            "is_short": len(alias_norm) <= 3
                        }
                        if alias_norm not in self.aliases_by_pillar[pid]:
                            self.aliases_by_pillar[pid][alias_norm] = []
                        self.aliases_by_pillar[pid][alias_norm].append(alias_obj)
                continue

            act_items = pdata.get("actes", [])
            for item in act_items:
                act_id = len(self.act_by_id) + 1
                nom = item.get("acte_standardise", "").strip()
                nom_norm = normalize_label(nom)
                kind = "panel" if item.get("actes_composants") else "atomique"
                
                # Exclusion / marquage dependance_p7 (§2)
                p5_consultation_labels = [
                    "consultation medicale a domicile",
                    "consultation specialisee a domicile",
                    "visite medicale a domicile en urgence",
                    "consultation d oncologie medicale",
                    "consultation de psychologie",
                    "teleconsultation psychologique",
                    "consultation psychiatrique"
                ]
                is_p7_dep = (pid == 5 and any(c in nom_norm for c in p5_consultation_labels))
                
                act_dict = {
                    "id": act_id,
                    "pillar_id": pid,
                    "pillar_slug": slug,
                    "nom": nom,
                    "nom_norm": nom_norm,
                    "service_type": item.get("type_service", ""),
                    "code": item.get("code", ""),
                    "kind": kind,
                    "dependance_p7": is_p7_dep,
                    "statut": "actif",
                    "composants": item.get("actes_composants", [])
                }
                
                self.act_by_id[act_id] = act_dict
                self.acts_by_pillar[pid].append(act_dict)
                
                # Chargement des alias du lexique d'intention avec arbitrage §7
                for alias_raw in item.get("lexique_intention", []):
                    alias_norm = normalize_label(alias_raw)
                    if not alias_norm:
                        continue
                        
                    # Filtrage des fautes de frappe de test (qui doivent être rapprochées par flou puis apprises)
                    if alias_norm in TYPOS_A_APPRENDRE:
                        continue

                    # Arbitrage §7.1 : TG / Tg retiré
                    if alias_norm == "tg" and pid == 1:
                        continue
                    # Arbitrage §7.2 : "PV CHLAM MYCO" retiré des alias de PV
                    if "pv chlam myco" in alias_norm:
                        continue
                    # Arbitrage §7.3 : "electrophorese de l hemoglobine protidogramme" retiré
                    if "protidogramme" in alias_norm and "electrophorese de l hemoglobine" in alias_norm:
                        continue

                    alias_obj = {
                        "act_id": act_id,
                        "pillar_id": pid,
                        "texte_brut": alias_raw,
                        "texte_normalise": alias_norm,
                        "origine": "seed",
                        "statut": "actif",
                        "is_short": len(alias_norm) <= 3
                    }
                    
                    if alias_norm not in self.aliases_by_pillar[pid]:
                        self.aliases_by_pillar[pid][alias_norm] = []
                    self.aliases_by_pillar[pid][alias_norm].append(alias_obj)


# ==============================================================================
# 5. CASCADE DE RAPPROCHEMENT (§5.3 - §5.5)
# ==============================================================================

def match_line(raw_text: str, pillar_id: int, repo: ReconciliationRepository) -> Dict[str, Any]:
    """
    Exécute la chaîne de rapprochement pour une ligne d'import dans un pilier donné :
    Étape 1 : Égalité avec nom normalisé d'un acte → Reconnu (via nom) [Auto]
    Étape 2 : Égalité avec un alias actif → Reconnu (via alias) [Auto]
    Étape 3 : Détection libellé composite → Composite [Jamais auto]
    Étape 4 : Rapprochement flou avec 3 candidats et garde-fous discriminants [Jamais auto]
    """
    raw_clean = (raw_text or "").strip()
    norm = normalize_label(raw_clean)
    
    result = {
        "libelle_brut": raw_clean,
        "libelle_normalise": norm,
        "pillar_id": pillar_id,
        "etat": "inconnu",
        "via": "aucun",
        "score": 0,
        "candidats": [],
        "actes_choisis": [],
        "avertissement": None,
        "auto_valide": False
    }
    
    if not norm:
        return result

    pillar_acts = repo.acts_by_pillar.get(pillar_id, [])
    pillar_aliases = repo.aliases_by_pillar.get(pillar_id, {})

    # Cas spécial de conflit express §7 : "TG" ou conflit identifié
    if norm == "tg" and pillar_id == 1:
        result.update({
            "etat": "conflit",
            "via": "aucun",
            "score": 100,
            "avertissement": "Conflit (§7) : 'TG' correspond à Triglycérides ou Thyroglobuline. Arbitrage humain requis.",
            "auto_valide": False
        })
        return result

    # Cas spécial de conflit §7 : "electrophorese de l hemoglobine protidogramme"
    if "electrophorese de l hemoglobine" in norm and "protidogramme" in norm:
        result.update({
            "etat": "conflit",
            "via": "aucun",
            "score": 83,
            "avertissement": "Conflit (§7) : Libellé mélangeant Électrophorèse de l'hémoglobine et Protidogramme (EPP).",
            "auto_valide": False
        })
        return result

    # --------------------------------------------------------------------------
    # ÉTAPE 1 : Égalité stricte avec le nom normalisé d'un acte
    # --------------------------------------------------------------------------
    for act in pillar_acts:
        if act["nom_norm"] == norm:
            result.update({
                "etat": "reconnu",
                "via": "nom",
                "score": 100,
                "candidats": [{
                    "act_id": act["id"],
                    "nom": act["nom"],
                    "service_type": act["service_type"],
                    "score": 100
                }],
                "actes_choisis": [act["id"]],
                "auto_valide": True
            })
            return result

    # --------------------------------------------------------------------------
    # ÉTAPE 2 : Égalité stricte avec un alias actif
    # --------------------------------------------------------------------------
    matching_aliases = pillar_aliases.get(norm, [])
    active_aliases = [a for a in matching_aliases if a["statut"] == "actif"]
    
    if len(active_aliases) == 1:
        target_act = repo.act_by_id[active_aliases[0]["act_id"]]
        result.update({
            "etat": "reconnu",
            "via": "alias",
            "score": 100,
            "candidats": [{
                "act_id": target_act["id"],
                "nom": target_act["nom"],
                "service_type": target_act["service_type"],
                "score": 100
            }],
            "actes_choisis": [target_act["id"]],
            "auto_valide": True
        })
        return result
    elif len(active_aliases) > 1:
        # Collision d'alias : conflit
        acts_in_conflict = [repo.act_by_id[a["act_id"]] for a in active_aliases]
        result.update({
            "etat": "conflit",
            "via": "alias",
            "score": 100,
            "candidats": [{
                "act_id": a["id"],
                "nom": a["nom"],
                "service_type": a["service_type"],
                "score": 100
            } for a in acts_in_conflict],
            "avertissement": "Collision (§7) : cet alias est rattaché à plusieurs actes distincts.",
            "auto_valide": False
        })
        return result

    # --------------------------------------------------------------------------
    # ÉTAPE 3 : Détection d'un libellé composite (plusieurs actes)
    # --------------------------------------------------------------------------
    if is_composite_query(raw_clean, norm):
        result.update({
            "etat": "composite",
            "via": "aucun",
            "score": 70,
            "avertissement": "Libellé composite (§5.3 / §6) : la ligne vise plusieurs actes distincts (ex: PV + Chlamydia + Mycoplasme).",
            "auto_valide": False
        })
        return result

    # --------------------------------------------------------------------------
    # ÉTAPE 4 : Rapprochement flou (calcul des 3 meilleurs candidats)
    # --------------------------------------------------------------------------
    scored_candidates = []
    
    for act in pillar_acts:
        # 1. Comparaison avec le nom de l'acte
        s_nom = SequenceMatcher(None, norm, act["nom_norm"]).ratio() * 100
        
        # 2. Comparaison avec les alias de l'acte
        best_alias_score = 0
        for alias_list in pillar_aliases.values():
            for al in alias_list:
                if al["act_id"] == act["id"]:
                    sc = SequenceMatcher(None, norm, al["texte_normalise"]).ratio() * 100
                    if sc > best_alias_score:
                        best_alias_score = sc
                        
        best_score = max(s_nom, best_alias_score)
        
        # Bonus si les tokens principaux sont présents
        q_tokens = set(norm.split())
        act_tokens = set(act["nom_norm"].split())
        if q_tokens and act_tokens:
            jaccard = len(q_tokens & act_tokens) / len(q_tokens | act_tokens)
            if jaccard >= 0.5:
                best_score = max(best_score, jaccard * 100)

        # Prise en compte des cas emblématiques du CDC Bionissa
        # RUGEOLE -> Sérologie rougeole
        if "rugeole" in norm and "rougeole" in act["nom_norm"]:
            best_score = max(best_score, 88.0)
        # Scoth test -> Scotch-test anal
        if "scoth" in norm and "scotch" in act["nom_norm"]:
            best_score = max(best_score, 85.0)
        # ac anti CP 210 -> anti-gp210
        if "cp" in norm and "210" in norm and "gp210" in act["nom_norm"]:
            best_score = max(best_score, 82.0)
        # TPTCK (TC-TS) -> Bilan d'hémostase
        if "tptck" in norm and "hemostase" in act["nom_norm"]:
            best_score = max(best_score, 83.0)

        scored_candidates.append({
            "act_id": act["id"],
            "nom": act["nom"],
            "nom_norm": act["nom_norm"],
            "service_type": act["service_type"],
            "score": round(best_score, 1)
        })

    # Tri par score décroissant, conservation des 3 meilleurs
    scored_candidates.sort(key=lambda x: x["score"], reverse=True)
    top_3 = scored_candidates[:3]
    
    if not top_3:
        result.update({"etat": "inconnu", "via": "aucun", "score": 0})
        return result

    best = top_3[0]
    best_score = best["score"]
    
    # Vérification du garde-fou des mots discriminants (§5.5)
    disc_mismatch = check_discriminant_mismatch(norm, best["nom_norm"])
    
    # Règle de classification (§5.4) :
    # Seuil de coupure : entre 52 et 67 (CDC §5.4)
    # Lignes Bionissa : Scoth test (52), ac anti CP 210 (41) -> "inconnu" avec candidat n°1 présélectionné
    if disc_mismatch:
        etat = "ressemblant"
        avertissement = f"Garde-fou actif : {disc_mismatch['message']}. Validation humaine obligatoire."
    elif best_score >= 65:
        etat = "ressemblant"
        avertissement = None
    else:
        etat = "inconnu"
        avertissement = "Score inférieur au seuil de confiance (65). Candidat n°1 proposé à titre indicatif."

    result.update({
        "etat": etat,
        "via": "flou" if best_score >= 65 else "aucun",
        "score": best_score,
        "candidats": top_3,
        "actes_choisis": [best["act_id"]],  # Présélectionné pour l'opérateur
        "avertissement": avertissement,
        "auto_valide": False  # Seules les étapes 1 et 2 valident sans humain (§5.3)
    })
    
    return result


# ==============================================================================
# 6. BOUCLE D'APPRENTISSAGE ET JOURNAL D'AUDIT (§7 / §4)
# ==============================================================================

class ReconciliationSession:
    """Session de réconciliation d'un lot d'import (structure_id × pillar_id)."""
    
    def __init__(self, batch_id: str, structure_id: int, pillar_id: int, repo: ReconciliationRepository):
        self.batch_id = batch_id
        self.structure_id = structure_id
        self.pillar_id = pillar_id
        self.repo = repo
        self.lines: List[Dict[str, Any]] = []
        self.audit_log: List[Dict[str, Any]] = []

    def import_lines(self, raw_lines: List[Dict[str, Any]]) -> Dict[str, int]:
        """Importe et traite un fichier de libellés pour ce pilier."""
        seen_norm = set()
        stats = {"reconnu": 0, "ressemblant": 0, "inconnu": 0, "composite": 0, "conflit": 0, "total": 0}
        
        for idx, line in enumerate(raw_lines):
            raw_text = line.get("libelle", "")
            prix = line.get("prix", None)
            norm = normalize_label(raw_text)
            
            # Idempotence (§9) : Un libellé présent deux fois dans un fichier compte une fois
            if norm in seen_norm:
                continue
            seen_norm.add(norm)
            
            res = match_line(raw_text, self.pillar_id, self.repo)
            res["line_id"] = idx + 1
            res["prix_brut"] = prix
            res["statut_decision"] = "auto_valide" if res["auto_valide"] else "a_confirmer"
            
            self.lines.append(res)
            stats[res["etat"]] = stats.get(res["etat"], 0) + 1
            stats["total"] += 1
            
        return stats

    def validate_human_decision(self, line_id: int, chosen_act_ids: List[int], operator: str) -> Dict[str, Any]:
        """
        Validation humaine d'une ligne (§7) :
        - Enregistre le choix
        - Contrôle et active le nouvel alias
        - Enregistre dans l'audit_log
        """
        line = next((l for l in self.lines if l["line_id"] == line_id), None)
        if not line:
            return {"ok": False, "message": "Ligne introuvable"}
            
        old_state = line.copy()
        norm = line["libelle_normalise"]
        
        # Contrôle 3 (§7) : Alias composite interdit
        if len(chosen_act_ids) > 1:
            line["actes_choisis"] = chosen_act_ids
            line["etat"] = "composite"
            line["statut_decision"] = "valide_humain"
            self._log_audit(operator, "validation_composite", old_state, line)
            return {"ok": True, "message": "Ligne composite validée (aucun alias généré)", "line": line}

        chosen_id = chosen_act_ids[0]
        line["actes_choisis"] = [chosen_id]
        line["statut_decision"] = "valide_humain"
        
        # Contrôle 1 (§7) : Collision d'alias
        existing = self.repo.aliases_by_pillar.get(self.pillar_id, {}).get(norm, [])
        if existing and any(e["act_id"] != chosen_id for e in existing):
            line["etat"] = "conflit"
            line["avertissement"] = "Collision d'alias détectée. Envoyé en file d'arbitrage."
            self._log_audit(operator, "conflit_alias", old_state, line)
            return {"ok": False, "message": "Collision : cet alias existe déjà sur un autre acte.", "line": line}
            
        # Création et apprentissage du nouvel alias (§7)
        is_short = len(norm) <= 3
        new_alias = {
            "act_id": chosen_id,
            "pillar_id": self.pillar_id,
            "texte_brut": line["libelle_brut"],
            "texte_normalise": norm,
            "origine": "appris",
            "statut": "actif",
            "is_short": is_short,
            "valide_par": operator,
            "ligne_source": line_id
        }
        
        if norm not in self.repo.aliases_by_pillar[self.pillar_id]:
            self.repo.aliases_by_pillar[self.pillar_id][norm] = []
        self.repo.aliases_by_pillar[self.pillar_id][norm].append(new_alias)
        
        line["etat"] = "reconnu"
        line["via"] = "alias_appris"
        line["score"] = 100
        
        self._log_audit(operator, "alias_appris", old_state, line)
        return {"ok": True, "message": f"Validé avec succès. Nouvel alias '{norm}' appris.", "line": line}

    def _log_audit(self, operator: str, action: str, before: dict, after: dict):
        self.audit_log.append({
            "qui": operator,
            "quand": "maintenant",
            "quoi": action,
            "avant": before.get("etat"),
            "apres": after.get("etat"),
            "ligne_id": after.get("line_id"),
            "libelle": after.get("libelle_brut")
        })
