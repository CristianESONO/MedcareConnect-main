import re
import unicodedata
from typing import Dict, List, Any
from .config import STOP_WORDS, PILLARS

GREEK_MAP = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
    "ζ": "zeta", "η": "eta", "θ": "theta", "ι": "iota", "κ": "kappa",
    "λ": "lambda", "μ": "mu", "ν": "nu", "ξ": "xi", "ο": "omicron",
    "π": "pi", "ρ": "rho", "σ": "sigma", "τ": "tau", "υ": "upsilon",
    "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
}

def strip_accents(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = s.replace("œ", "oe").replace("æ", "ae")
    for g, name in GREEK_MAP.items():
        s = s.replace(g, name)
    norm = unicodedata.normalize('NFD', s)
    return "".join(c for c in norm if unicodedata.category(c) != 'Mn')

def stem(w: str) -> str:
    if len(w) <= 3:
        return w
    if w.endswith('ales'):
        return w[:-1].rstrip('e')
    if w.endswith('ale'):
        return w[:-1]
    if re.search(r'iennes?$', w):
        return re.sub(r'iennes?$', 'ien', w)
    if re.search(r'ees?$', w):
        return re.sub(r'ees?$', 'e', w)
    if re.search(r'ines?$', w) and len(w) > 5:
        return w.rstrip('s')
    if re.search(r'[^s]s$', w) and len(w) > 4:
        return w[:-1]
    return w

def normalize(raw: str, pillar_id: str = None) -> Dict[str, Any]:
    if raw is None:
        raw = ""
    s = strip_accents(raw).lower()
    # Enlever d' et l'
    s = re.sub(r"\b([dl])['\u2019]\s*", "", s)
    # Compacter 24 h -> 24h
    s = re.sub(r"(\d+)\s*(h|j|min)\b", r"\1\2", s)
    # Acronymes: n.f.s -> nfs
    s = re.sub(r"\b([a-z0-9])\.(?=[a-z0-9]\b)", r"\1", s)
    s = re.sub(r"\b([a-z0-9])\.(?=\s|$)", r"\1", s)
    
    composite = bool(re.search(r"[a-z)]\s*\+\s*[a-z(]", s) or re.search(r"\bbilan\b", s))
    
    # Remplacer ponctuations par espaces, préserver + et /
    s = re.sub(r"[^a-z0-9+\/\s]", " ", s)
    s = re.sub(r"[+\/]", " + ", s)
    s = re.sub(r"\s+", " ", s).strip()
    
    ab = PILLARS.get(pillar_id, {}).get('abbrev', {}) if pillar_id else {}
    words = [ab.get(w, w) for w in s.split() if w]
    full = " ".join(words)
    full = re.sub(r"\s*\+\s*", " + ", full).strip()
    
    sig = [stem(w) for w in words if w != '+' and w not in STOP_WORDS and len(w) > 0]
    key = " ".join(sorted(sig))
    compact = "".join(sig)
    
    return {
        "raw": raw,
        "full": full,
        "sig": sig,
        "key": key,
        "compact": compact,
        "composite": composite
    }
