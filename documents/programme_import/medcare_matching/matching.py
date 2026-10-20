import math
from typing import List, Dict, Any, Set, Tuple, Optional
from .config import PILLARS, MODALITIES, DEFAULT_THRESHOLDS

def jaro(a: str, b: str) -> float:
    if a == b:
        return 1.0
    la, lb = len(a), len(b)
    if not la or not lb:
        return 0.0
    md = max(0, max(la, lb) // 2 - 1)
    ma = [False] * la
    mb = [False] * lb
    m = 0
    for i in range(la):
        lo = max(0, i - md)
        hi = min(i + md + 1, lb)
        for j in range(lo, hi):
            if not mb[j] and a[i] == b[j]:
                ma[i] = True
                mb[j] = True
                m += 1
                break
    if not m:
        return 0.0
    t = 0
    k = 0
    for i in range(la):
        if ma[i]:
            while not mb[k]:
                k += 1
            if a[i] != b[k]:
                t += 1
            k += 1
    return (m / la + m / lb + (m - t / 2.0) / m) / 3.0

def jaro_winkler(a: str, b: str) -> float:
    j = jaro(a, b)
    p = 0
    while p < 4 and p < len(a) and p < len(b) and a[p] == b[p]:
        p += 1
    return j + p * 0.1 * (1.0 - j)

def trigrams(s: str) -> Set[str]:
    g = set()
    x = "  " + s + " "
    for i in range(len(x) - 2):
        g.add(x[i:i + 3])
    return g

def dice(set_a: Set[str], set_b: Set[str]) -> float:
    n = len(set_a & set_b)
    total = len(set_a) + len(set_b)
    return (2.0 * n) / total if total > 0 else 0.0

def word_weight(w: str, pillar_id: str) -> float:
    p = PILLARS.get(pillar_id)
    if not p:
        return 1.0
    if w in p.get('generic', []):
        return 0.35
    if w in p.get('disc', []):
        return 0.5
    return 1.0

def soft_tokens(tokens_a: List[str], tokens_b: List[str], pillar_id: str) -> Tuple[float, float]:
    """Dice souple pondéré + Jaccard exact pondéré selon manuel §8.2."""
    if not tokens_a or not tokens_b:
        return 0.0, 0.0

    wa = sum(word_weight(a, pillar_id) for a in tokens_a)
    wb = sum(word_weight(b, pillar_id) for b in tokens_b)
    used = [False] * len(tokens_b)
    sum_weight = 0.0
    exact_weight = 0.0

    for a in tokens_a:
        best_v = 0.0
        best_i = -1
        for i, b in enumerate(tokens_b):
            if used[i]:
                continue
            if a == b:
                v = 1.0
            elif len(a) > 3 and len(b) > 3:
                v = jaro_winkler(a, b)
            else:
                v = 0.0
            if v > best_v:
                best_v = v
                best_i = i

        if best_i >= 0 and best_v >= 0.88:
            used[best_i] = True
            w = (word_weight(a, pillar_id) + word_weight(tokens_b[best_i], pillar_id)) / 2.0
            sum_weight += best_v * w
            if best_v == 1.0:
                exact_weight += w

    denom = wa + wb
    denom_jac = wa + wb - exact_weight
    dice_val = (2.0 * sum_weight) / denom if denom > 0 else 0.0
    jac_val = exact_weight / denom_jac if denom_jac > 0 else 0.0
    return dice_val, jac_val

def specific_compact(sig: List[str], pillar_id: str) -> str:
    sp = [w for w in sig if word_weight(w, pillar_id) > 0.4]
    target = sp if sp else sig
    return "".join(target)

def has_fuzzy(words_set: Set[str], target: str) -> bool:
    if target in words_set:
        return True
    if len(target) <= 3:
        return False
    for x in words_set:
        if len(x) > 3 and jaro_winkler(x, target) >= 0.90:
            return True
    return False

def disc_conflicts(tokens_a: List[str], tokens_b: List[str], pillar_id: str) -> List[str]:
    """Détection des conflits sur mots discriminants (§8.2)."""
    p_disc = PILLARS.get(pillar_id, {}).get('disc', [])
    sa = set(tokens_a)
    sb = set(tokens_b)
    out = []

    for w in p_disc:
        if w in MODALITIES:
            continue
        if has_fuzzy(sa, w) != has_fuzzy(sb, w):
            out.append(w)

    # Mots courts ou chiffrés (T3/T4, 25-OH, etc.)
    all_tokens = set(tokens_a + tokens_b)
    for w in all_tokens:
        if (len(w) == 1 and w.isalpha()) or any(c.isdigit() for c in w):
            if (w in sa) != (w in sb) and w not in out:
                out.append(w)

    # Modalités d'imagerie : conflit uniquement si les 2 côtés en nomment une et pas la même
    ma = [m for m in MODALITIES if has_fuzzy(sa, m)]
    mb = [m for m in MODALITIES if has_fuzzy(sb, m)]
    if ma and mb and sorted(ma) != sorted(mb):
        combined = list(dict.fromkeys(ma + mb))
        out.append("/".join(combined))

    return out

def score_entry(norm_source: Dict[str, Any], entry_norm: Dict[str, Any], act_kind: str, pillar_id: str) -> Dict[str, Any]:
    """Calcule le score exact selon la formule S = 0.5 T_set + 0.3 JW + 0.2 J_sig - P_disc - P_comp (§8.2)."""
    st_dice, st_jac = soft_tokens(norm_source['sig'], entry_norm['sig'], pillar_id)
    jw_val = jaro_winkler(
        specific_compact(norm_source['sig'], pillar_id),
        specific_compact(entry_norm['sig'], pillar_id)
    )
    s = 0.5 * st_dice + 0.3 * jw_val + 0.2 * st_jac

    dc = disc_conflicts(norm_source['sig'], entry_norm['sig'], pillar_id)
    s -= 0.25 * len(dc)

    # Pénalité composite
    comp = norm_source['composite'] != (act_kind == 'bilan' or entry_norm['composite'])
    if comp:
        s -= 0.20

    s_clamped = max(0.0, min(1.0, s))
    return {
        "score": s_clamped,
        "st_dice": st_dice,
        "jw": jw_val,
        "st_jac": st_jac,
        "disc": dc,
        "comp": comp
    }

def classify(m: Dict[str, Any], rule: str = 'V1', th: Dict[str, float] = None) -> str:
    """Classement en 3 issues (reconnu / a_confirmer / inconnu) selon manuel §8.3."""
    if th is None:
        th = DEFAULT_THRESHOLDS
    cands = m.get('cands', [])
    if not cands:
        return 'inconnu'
    if m.get('exact'):
        return 'reconnu'

    c1 = cands[0]
    c2 = cands[1] if len(cands) > 1 else None
    margin = c1['score'] - (c2['score'] if c2 else 0.0)

    if rule == 'V2':
        if (c1['score'] >= th['auto'] and
            margin >= th['margin'] and
            not c1.get('disc') and
            not c1.get('comp')):
            return 'reconnu'

    if c1['score'] >= th['prop']:
        return 'a_confirmer'

    return 'inconnu'

def explain(m: Dict[str, Any], issue: str, th: Dict[str, float] = None) -> str:
    cands = m.get('cands', [])
    if not cands:
        return 'aucun candidat'
    if m.get('exact'):
        return m.get('method', 'exact')

    c1 = cands[0]
    parts = [f"flou {round(c1['score'] * 100)} %"]
    if len(cands) > 1:
        margin = round((c1['score'] - cands[1]['score']) * 100)
        parts.append(f"marge {margin}")
    if c1.get('disc'):
        parts.append(f"conflit : {', '.join(c1['disc'])}")
    if c1.get('comp'):
        parts.append("bilan / acte")
    if issue == 'reconnu':
        parts.append("équivalence de forme")
    return " · ".join(parts)
