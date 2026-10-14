"""
Module de gestion du Lexique d'Intention MedCare.
Permet de mapper en temps réel les intentions, variantes réelles et termes usuels
des utilisateurs (patients et structures) vers les actes standardisés et piliers MedCare.
"""
from __future__ import annotations
import json
import os
import re
import unicodedata
from functools import lru_cache
from typing import Dict, Any, List, Optional

LEXIQUE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lexique_intention_medcare.json")

def normalize_text(text: str) -> str:
    """Normalise un texte (minuscule, sans accents, sans ponctuations superflues)."""
    if not text:
        return ""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())

@lru_cache(maxsize=1)
def get_lexique_data() -> Dict[str, Any]:
    """Charge le fichier JSON du lexique d'intention avec mise en cache mémoire."""
    if os.path.exists(LEXIQUE_PATH):
        try:
            with open(LEXIQUE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def resolve_intent(query: str) -> Optional[Dict[str, Any]]:
    """
    Recherche l'intention médicale correspondante dans le lexique.
    Supporte la correspondance exacte, par sous-chaîne et par mots-clés.
    """
    if not query:
        return None
        
    query_norm = normalize_text(query)
    lexique = get_lexique_data()
    
    # 1. Correspondance exacte
    for term, data in lexique.items():
        if normalize_text(term) == query_norm:
            return {
                "terme_reconnu": term,
                "score": 1.0,
                **data
            }
            
    # 2. Terme inclus avec limites de mots
    best_match = None
    best_len = 0
    q_tokens = set(query_norm.split())
    for term, data in lexique.items():
        t_norm = normalize_text(term)
        # Si le terme est exactement un token ou multi-token contenu
        pattern = r"\b" + re.escape(t_norm) + r"\b"
        if re.search(pattern, query_norm):
            if len(t_norm) > best_len:
                best_len = len(t_norm)
                best_match = {
                    "terme_reconnu": term,
                    "score": 0.90,
                    **data
                }
        elif len(query_norm) >= 4 and pattern and re.search(r"\b" + re.escape(query_norm) + r"\b", t_norm):
            if len(t_norm) > best_len:
                best_len = len(t_norm)
                best_match = {
                    "terme_reconnu": term,
                    "score": 0.85,
                    **data
                }
    if best_match:
        return best_match

    # 3. Correspondance de tokens
    q_words = set(w for w in query_norm.split() if len(w) >= 3)
    if q_words:
        for term, data in lexique.items():
            t_words = set(w for w in normalize_text(term).split() if len(w) >= 3)
            intersection = q_words & t_words
            if intersection:
                jaccard = len(intersection) / len(q_words | t_words)
                if jaccard >= 0.4:
                    return {
                        "terme_reconnu": term,
                        "score": round(jaccard, 2),
                        **data
                    }
                    
    return None

def suggest_intentions(query: str, limit: int = 6) -> List[Dict[str, Any]]:
    """Propose une liste d'intentions suggérées pour l'autocomplétion du chatbot."""
    if not query or len(query.strip()) < 2:
        # Suggestions par défaut
        return [
            {"terme": "NFS (hémogramme)", "pilier": "Biologie médicale", "pilier_slug": "biologie-medicale"},
            {"terme": "Scanner abdominal", "pilier": "Imagerie médicale", "pilier_slug": "imagerie-medicale"},
            {"terme": "Électrocardiogramme (ECG)", "pilier": "Explorations fonctionnelles", "pilier_slug": "explorations-fonctionnelles"},
            {"terme": "Transport médicalisé avec médecin", "pilier": "Ambulance médicalisée", "pilier_slug": "ambulance-medicalisee"},
            {"terme": "Consultation à domicile", "pilier": "Soins spécialisés", "pilier_slug": "soins-specialises"},
            {"terme": "Détartrage & Polissage", "pilier": "Soins dentaires", "pilier_slug": "soins-dentaires"},
        ]
        
    query_norm = normalize_text(query)
    lexique = get_lexique_data()
    results = []
    
    for term, data in lexique.items():
        t_norm = normalize_text(term)
        if query_norm in t_norm:
            results.append({
                "terme": term,
                "pilier": data.get("pilier"),
                "pilier_slug": data.get("pilier_slug"),
                "service": data.get("service"),
                "acte": data.get("acte") or data.get("prestation")
            })
            if len(results) >= limit:
                break
                
    return results
