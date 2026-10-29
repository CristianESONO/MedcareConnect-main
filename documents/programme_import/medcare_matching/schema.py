import re
from typing import List, Dict, Any, Optional
from .config import SECTION_MAP
from .normalizer import strip_accents

def parse_price(v: Any) -> Dict[str, Any]:
    """Parse et valide un prix selon les règles du manuel §7.2."""
    if v is None or str(v).strip() == "":
        return {"value": None, "statut": "manquant"}

    if isinstance(v, (int, float)):
        if v < 0:
            return {"value": None, "statut": "anomalie", "note": "négatif"}
        return {"value": round(v), "statut": "renseigne"}

    s_raw = str(v).strip()
    s = strip_accents(s_raw).upper()

    if re.search(r"DEVIS|VARIABLE", s):
        return {"value": None, "statut": "sur_devis"}

    if re.search(r"GRATUIT|OFFERT", s):
        return {"value": 0, "statut": "renseigne", "note": "gratuit, à confirmer"}

    # Nettoyage des devises et espaces
    s = re.sub(r"F\s*CFA|FCFA|CFA|XOF|FRANCS?|\bF\b|F$", "", s)
    s = re.sub(r"[\s\xa0]", "", s)

    # Cas des séparateurs de milliers
    if re.match(r"^\d{1,3}([.,]\d{3})+$", s):
        s = re.sub(r"[.,]", "", s)

    s = s.replace(",", ".")
    try:
        val = float(s)
        if val < 0:
            return {"value": None, "statut": "anomalie", "note": "négatif"}
        return {"value": round(val), "statut": "renseigne"}
    except (ValueError, TypeError):
        return {"value": None, "statut": "anomalie", "note": f"illisible : {v}"}

def parse_tariff_cell(val: Any) -> Dict[str, Any]:
    """Parse une cellule tarifaire (comptant, ipm ou assurance) selon les règles médicales MedCare."""
    if val is None:
        return {"value": None, "statut": "to_confirm"}
    if isinstance(val, (int, float)):
        v = float(val)
        return {"value": round(v), "statut": "covered"} if v > 0 else {"value": None, "statut": "to_confirm"}

    s = str(val).strip()
    if not s or s.lower() in {"-", "/", "nc", "n/c", "null", "none", "à confirmer", "a confirmer", ""}:
        return {"value": None, "statut": "to_confirm"}

    s_lower = s.lower()
    excluded_keywords = ["exclu", "non pris en charge", "non couvert", "hors convention", "refus", "non", "aucun"]
    if any(k in s_lower for k in excluded_keywords):
        return {"value": None, "statut": "excluded"}

    clean = re.sub(r"[^\d,\.]", "", s).replace(",", ".")
    try:
        prix = float(clean)
        return {"value": round(prix), "statut": "covered"} if prix > 0 else {"value": None, "statut": "to_confirm"}
    except ValueError:
        return {"value": None, "statut": "to_confirm"}

def is_price_like(v: Any) -> bool:
    if isinstance(v, (int, float)):
        return True
    s = str(v or "").strip()
    if not s:
        return False
    return bool(re.match(r"^\s*\d[\d\s.,\xa0]*\s*(F|FCFA|CFA|XOF)?\s*$", s, re.I))

def is_header_word(v: Any) -> bool:
    s = strip_accents(str(v or "")).strip().lower()
    return bool(re.search(r"\b(prix|tarifs?|montant|cout|co[uû]t|pu|prix unitaire|comptant|ipm|assurance)\b", s))

def is_label_header(v: Any) -> bool:
    s = strip_accents(str(v or "")).lower()
    s = re.sub(r"[^a-z\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return bool(re.match(r"^(actes?|examens?|designation|libelle|prestations?|analyses?|nom|intitule)(\s+(de\s+l\s*)?(acte|examen|analyse))?$", s, re.I))

def section_info(label: str) -> Optional[Dict[str, Any]]:
    s = strip_accents(label).lower()
    for sec in SECTION_MAP:
        if sec['re'].search(s):
            return sec
    return None

def contextualize(label: str, sec: Optional[Dict[str, Any]]) -> str:
    """Complète le libellé avec le contexte de section (§6.3)."""
    if not sec or not sec.get('term'):
        return label
    s = strip_accents(label).lower()
    head = sec['term'].split()[0][:6]
    if head in s or re.search(r"angio|uro|colo|scan|irm|radio|echo|doppler|mammo", s):
        return label
    return f"{sec['term']} {label}"

def is_attribute_header(v: Any) -> bool:
    s = strip_accents(str(v or "")).lower()
    s = re.sub(r"[^a-z\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return bool(re.match(r"^(type|types?|type prestation|types? prestations?|categories?|familles?|descriptions?|commentaires?|remarques?|observations?|code|codes?|id|num|reference)$", s, re.I))

def detect_schema(rows: List[List[Any]]) -> Dict[str, Any]:
    """Détection du schéma avec support Multi-Tarifs (Comptant, IPM, Assurance)."""
    if not rows:
        return {"ncol": 0, "roles": [], "confidence": 0}

    ncol = max(len(r) for r in rows)
    roles = ["vide"] * ncol

    # 1. Recherche d'en-tête explicite dans les 10 premières lignes
    header_found = False
    for r_idx, r in enumerate(rows[:10]):
        norm_r = [strip_accents(str(c or "")).lower() for c in r]
        has_label = any(is_label_header(c) for c in norm_r)
        has_price = any(is_header_word(c) for c in norm_r)
        if has_label and (has_price or len([c for c in norm_r if c]) >= 2):
            header_found = True
            for c_idx, c_val in enumerate(norm_r):
                if not c_val:
                    continue
                if is_label_header(c_val) and "libelle" not in roles:
                    roles[c_idx] = "libelle"
                elif "ipm" in c_val:
                    roles[c_idx] = "prix_ipm"
                elif "assurance" in c_val:
                    roles[c_idx] = "prix_assurance"
                elif any(w in c_val for w in ("comptant", "public", "cash")) or (is_header_word(c_val) and "prix_comptant" not in roles and "prix" not in roles):
                    roles[c_idx] = "prix_comptant"
                elif any(w in c_val for w in ("delai", "duree", "temps")):
                    roles[c_idx] = "delai"
                elif is_attribute_header(c_val):
                    roles[c_idx] = "attribut"
            break

    # Si pas d'en-tête explicite détecté, analyse statistique des colonnes
    if not header_found or "libelle" not in roles:
        prof = [{"text": 0, "price": 0, "len": 0, "header": 0, "labelHeader": 0, "attrHeader": 0} for _ in range(ncol)]

        for r_idx, r in enumerate(rows):
            for c in range(ncol):
                v = r[c] if c < len(r) else None
                if v is None or str(v).strip() == "":
                    continue
                if is_header_word(v):
                    prof[c]["header"] += 1
                    continue
                if is_label_header(v):
                    prof[c]["labelHeader"] += 1
                    continue
                if is_attribute_header(v):
                    prof[c]["attrHeader"] += 1
                    continue
                if is_price_like(v):
                    prof[c]["price"] += 1
                else:
                    prof[c]["text"] += 1
                    prof[c]["len"] += len(str(v).strip())

        price_col = -1
        pmax = 0
        for c, p in enumerate(prof):
            sc = p["price"] + 3 * p["header"]
            if sc > pmax:
                pmax = sc
                price_col = c

        label_col = -1
        lmax = 0
        for c, p in enumerate(prof):
            if c == price_col:
                continue
            sc = p["text"] * min(1.0, (p["len"] / (p["text"] or 1)) / 6.0) + 3 * p["labelHeader"] - 5 * p["attrHeader"]
            if sc > lmax:
                lmax = sc
                label_col = c

        delai_col = -1
        for c, p in enumerate(prof):
            if c in (price_col, label_col):
                continue
            n = 0
            for r in rows:
                v = r[c] if c < len(r) else None
                if v and re.search(r"\b(\d+\s*(h|j|min|jours?|heures?)|rdv|immediat|urgence)\b", strip_accents(str(v)), re.I):
                    n += 1
            if n >= 3 and delai_col < 0:
                delai_col = c

        roles = []
        for c in range(ncol):
            if c == label_col:
                roles.append("libelle")
            elif c == price_col:
                roles.append("prix_comptant")
            elif c == delai_col:
                roles.append("delai")
            elif prof[c]["attrHeader"] > 0:
                roles.append("attribut")
            elif prof[c]["text"] > 0 and prof[c]["text"] < len(rows) * 0.4:
                roles.append("texte")
            elif prof[c]["text"] > 0:
                roles.append("attribut")
            else:
                roles.append("vide")

    return {
        "ncol": ncol,
        "roles": roles,
        "confidence": 0.9 if header_found else 0.7
    }

def read_rows(rows: List[List[Any]], roles: List[str], file_pillar: Optional[str] = None) -> Dict[str, Any]:
    """Lit et type les lignes brutes avec gestion Tri-Tarifs (Comptant, IPM, Assurance)."""
    label_cols = [c for c, r in enumerate(roles) if r in ("libelle", "texte")]
    comptant_col = roles.index("prix_comptant") if "prix_comptant" in roles else (roles.index("prix") if "prix" in roles else -1)
    ipm_col = roles.index("prix_ipm") if "prix_ipm" in roles else -1
    assurance_col = roles.index("prix_assurance") if "prix_assurance" in roles else -1
    delai_col = roles.index("delai") if "delai" in roles else -1

    out = []
    section = None
    prev_empty = True

    for i, r in enumerate(rows):
        cells = []
        for c in label_cols:
            if c < len(r):
                v = r[c]
                if v is not None and str(v).strip() != "" and not is_price_like(v):
                    cells.append(str(v).strip())

        label = re.sub(r"\s+", " ", " ".join(cells)).strip()
        pv = r[comptant_col] if comptant_col >= 0 and comptant_col < len(r) else None
        empty = (not label) and (pv is None or str(pv).strip() == "")

        if empty:
            out.append({"num": i + 1, "kind": "vide"})
            prev_empty = True
            continue

        if is_label_header(label) and (pv is None or is_header_word(pv)):
            out.append({"num": i + 1, "kind": "entete", "label": label})
            prev_empty = True
            section = None
            continue

        price_empty = pv is None or str(pv).strip() == ""
        sec = section_info(label) if label else None
        is_section = label and (
            (pv is not None and is_header_word(pv)) or
            (price_empty and prev_empty and (sec or (comptant_col >= 0 and label == label.upper())) and len(label.split()) <= 3)
        )

        if is_section:
            section = {"label": label, "info": sec}
            out.append({
                "num": i + 1,
                "kind": "section",
                "label": label,
                "pillar": sec["pillar"] if sec else None
            })
            prev_empty = False
            continue

        info = section["info"] if section else None
        pillar = (info["pillar"] if info else None) or file_pillar

        # Multi-Tarifs
        pv_ipm = r[ipm_col] if ipm_col >= 0 and ipm_col < len(r) else None
        pv_ass = r[assurance_col] if assurance_col >= 0 and assurance_col < len(r) else None

        t_comptant = parse_tariff_cell(pv)
        t_ipm = parse_tariff_cell(pv_ipm) if ipm_col >= 0 else {"value": None, "statut": "to_confirm"}
        t_ass = parse_tariff_cell(pv_ass) if assurance_col >= 0 else {"value": None, "statut": "to_confirm"}

        out.append({
            "num": i + 1,
            "kind": "acte",
            "label": label,
            "section": section["label"] if section else "",
            "ctx": contextualize(label, info),
            "price": parse_price(pv),
            "priceRaw": str(pv) if pv is not None else "",
            "prix_comptant": t_comptant["value"],
            "prix_ipm": t_ipm["value"],
            "status_ipm": t_ipm["statut"],
            "prix_assurance": t_ass["value"],
            "status_assurance": t_ass["statut"],
            "delai": str(r[delai_col]) if delai_col >= 0 and delai_col < len(r) and r[delai_col] is not None else "",
            "pillar": pillar,
            "types": info["types"] if info and "types" in info else None,
            "merged": len(cells) > 1
        })
        prev_empty = False

    # Lignes avant le premier en-tête = titre du document
    hi = -1
    for k, l in enumerate(out):
        if hi < 0 and l["kind"] == "entete":
            hi = k
            break
    if hi > 0:
        for k in range(hi):
            if out[k]["kind"] != "vide":
                out[k] = {"num": out[k]["num"], "kind": "titre", "label": out[k].get("label", "")}

    # Déterminer pilier majoritaire
    votes = {}
    for l in out:
        if l["kind"] == "section" and l.get("pillar"):
            votes[l["pillar"]] = votes.get(l["pillar"], 0) + 1
    maj_pillar = max(votes, key=votes.get) if votes else file_pillar

    for l in out:
        if l["kind"] == "acte" and not l.get("pillar"):
            l["pillar"] = maj_pillar

    # Contrôle de vraisemblance des prix (> 4 x médiane de la section)
    by_sec = {}
    for l in out:
        if l["kind"] == "acte" and l["price"].get("value"):
            by_sec.setdefault(l["section"], []).append(l["price"]["value"])

    for l in out:
        if l["kind"] == "acte" and l["price"].get("value"):
            prices = sorted(by_sec.get(l["section"], []))
            if len(prices) >= 4:
                med = prices[len(prices) // 2]
                if med > 0 and l["price"]["value"] > 4 * med:
                    l["price"]["statut"] = "anomalie"
                    l["price"]["note"] = f"prix {round(l['price']['value'] / med)} × la médiane de la section"

    return {
        "lines": out,
        "pillar": maj_pillar
    }
