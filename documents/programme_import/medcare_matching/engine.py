import os
import json
from typing import List, Dict, Any, Optional
from .config import DEFAULT_THRESHOLDS
from .normalizer import normalize
from .schema import detect_schema, read_rows
from .reader import read_any_file
from .matching import (
    trigrams, dice, score_entry, classify, explain
)

class IndexEntry:
    def __init__(self, act: Dict[str, Any], text: str, kind: str, scope: str = 'global', org: str = None, alias: Any = None):
        self.act = act
        self.text = text
        self.kind = kind
        self.scope = scope
        self.org = org
        self.alias = alias
        self.n = normalize(text, act.get('pillar'))
        self.tri = trigrams(self.n['compact'])

class ReferentialIndex:
    def __init__(self, actes: List[Dict[str, Any]], aliases: List[Dict[str, Any]] = None):
        self.actes = actes
        self.by_id: Dict[str, Dict[str, Any]] = {}
        self.entries: List[IndexEntry] = []
        self.exact: Dict[str, List[IndexEntry]] = {}

        for a in actes:
            aid = str(a.get('id'))
            self.by_id[aid] = a
            # Nom principal
            forms = [{'text': a.get('name'), 'kind': 'nom'}]
            # Lexique d'intention
            for x in a.get('lexique', []):
                forms.append({'text': x, 'kind': 'lexique'})

            for f in forms:
                self._add_entry(a, f['text'], f['kind'], 'global', None)

        for al in (aliases or []):
            aid = str(al.get('acteId') or al.get('acte_id'))
            a = self.by_id.get(aid)
            if not a or al.get('statut') == 'suspendu':
                continue
            kind = 'alias' if al.get('statut') == 'actif' else 'alias_candidat'
            self._add_entry(a, al.get('brut') or al.get('alias_brut'), kind, al.get('scope', 'global'), al.get('organisme'), al)

    def _add_entry(self, a: Dict[str, Any], text: str, kind: str, scope: str, org: Optional[str], al: Any = None):
        if not text:
            return
        e = IndexEntry(a, text, kind, scope, org, al)
        if not e.n['sig']:
            return
        self.entries.append(e)
        k = f"{a.get('pillar')}|{e.n['key']}"
        self.exact.setdefault(k, []).append(e)

def exact_lookup(idx: ReferentialIndex, n: Dict[str, Any], pillars: List[str], org_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Recherche exacte selon la cascade §8.1."""
    for p in pillars:
        k = f"{p}|{n['key']}"
        entries = idx.exact.get(k, [])
        if not entries:
            continue

        # Alias de la structure en priorité
        own = [e for e in entries if e.scope == 'structure' and e.org == org_id and e.kind == 'alias']
        if own:
            return {"e": own[0], "method": "alias de la structure"}

        # Nom exact standardisé
        nom = [e for e in entries if e.kind == 'nom']
        if nom:
            return {"e": nom[0], "method": "nom exact"}

        # Alias global ou lexique
        glob = [e for e in entries if (e.kind in ('lexique', 'alias')) and e.scope == 'global']
        ids = set(e.act.get('id') for e in glob)
        if glob and len(ids) == 1:
            method = "alias validé" if glob[0].kind == 'alias' else "lexique"
            return {"e": glob[0], "method": method}

        if len(ids) > 1:
            return {"ambiguous": True}

    return None

def match_line(idx: ReferentialIndex, label: str, ctx_label: str, pillars: List[str], org_id: Optional[str] = None, types: Optional[List[str]] = None) -> Dict[str, Any]:
    """Rapproche une ligne selon la cascade à 6 niveaux du manuel §8.1."""
    tries = [{"text": label, "ctx": False}]
    if ctx_label and ctx_label != label:
        tries.insert(0, {"text": ctx_label, "ctx": True})

    # Étapes 1 à 4 : correspondances exactes
    for t in tries:
        pid = pillars[0]
        n = normalize(t["text"], pid)
        ex = exact_lookup(idx, n, pillars, org_id)
        if ex and ex.get("e"):
            ctx_suffix = " (avec la section)" if t["ctx"] else ""
            return {
                "exact": True,
                "method": ex["method"] + ctx_suffix,
                "cands": [{
                    "acte": ex["e"].act,
                    "score": 1.0,
                    "disc": [],
                    "via": ex["e"].text,
                    "kind": ex["e"].kind
                }],
                "usedText": t["text"]
            }

    # Étape 5 : Rapprochement flou
    pid0 = pillars[0]
    n0 = normalize(tries[-1]["text"], pid0)
    tri0 = trigrams(n0['compact'])

    pool = [
        e for e in idx.entries
        if e.act.get('pillar') in pillars and
        (e.scope == 'global' or e.org == org_id) and
        (not types or e.act.get('type') in types)
    ]

    scored_pre = []
    for e in pool:
        d = dice(tri0, e.tri)
        scored_pre.append((d, e))

    scored_pre.sort(key=lambda x: x[0], reverse=True)
    top_entries = [e for _, e in scored_pre[:60]]

    best_by_act: Dict[str, Dict[str, Any]] = {}
    for e in top_entries:
        sc = score_entry(n0, e.n, e.act.get('kind', 'acte'), e.act.get('pillar'))
        s_val = sc['score']
        if e.kind == 'alias_candidat':
            s_val = min(1.0, s_val + 0.03)

        aid = str(e.act.get('id'))
        if aid not in best_by_act or s_val > best_by_act[aid]['score']:
            best_by_act[aid] = {
                "acte": e.act,
                "score": s_val,
                "disc": sc['disc'],
                "comp": sc['comp'],
                "via": e.text,
                "kind": e.kind
            }

    cands = sorted(best_by_act.values(), key=lambda x: x['score'], reverse=True)[:3]

    # Élargissement si section trop restrictive
    if types and (not cands or cands[0]['score'] < 0.60):
        wide = match_line(idx, label, ctx_label, pillars, org_id, types=None)
        if wide.get('cands') and not wide['cands'][0].get('disc'):
            if not cands or wide['cands'][0]['score'] > cands[0]['score'] + 0.10:
                wide['widened'] = True
                return wide

    return {
        "exact": False,
        "method": "flou",
        "cands": cands,
        "usedText": tries[-1]["text"]
    }

class ReconciliationEngine:
    """Moteur de réconciliation conforme au manuel d'architecture."""
    def __init__(self, referentiel_path: str, aliases_path: Optional[str] = None):
        with open(referentiel_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extraction des actes selon la structure
        if isinstance(data, list):
            actes = data
        elif isinstance(data, dict) and "actes" in data:
            actes = data["actes"]
        elif isinstance(data, dict) and "piliers" in data:
            # Format referentiel_6piliers_medcare.json
            actes = []
            for pslug, pdata in data["piliers"].items():
                pid = pdata.get("pilier_id", 1)
                slug = "bio" if pid == 1 else ("img" if pid == 2 else pslug)
                for item in pdata.get("actes", []):
                    actes.append({
                        "id": f"{slug[0].upper()}{item.get('code', len(actes)+1)}",
                        "pillar": slug,
                        "type": item.get("type_service", ""),
                        "name": item.get("acte_standardise", ""),
                        "kind": item.get("kind", "acte"),
                        "lexique": item.get("lexique_intention", [])
                    })
        else:
            actes = []

        aliases = []
        if aliases_path and os.path.exists(aliases_path):
            with open(aliases_path, 'r', encoding='utf-8') as f:
                aliases = json.load(f)

        self.index = ReferentialIndex(actes, aliases)
        self.actes = actes
        self.aliases = aliases

    def reconcile_file(self, filepath: str, default_pillar: Optional[str] = None, org_id: Optional[str] = None, rule: str = 'V1', th: Dict[str, float] = None) -> Dict[str, Any]:
        """Lit un fichier de n'importe quel format et le réconcilie entièrement."""
        if th is None:
            th = DEFAULT_THRESHOLDS

        rows = read_any_file(filepath)
        schema = detect_schema(rows)
        parsed = read_rows(rows, schema['roles'], default_pillar)

        lines = parsed['lines']
        pillar = parsed['pillar'] or default_pillar or 'bio'

        actes_lines = [l for l in lines if l['kind'] == 'acte']
        results = []

        summary = {
            'total_rows': len(rows),
            'total_lines': len(lines),
            'actes_count': len(actes_lines),
            'reconnus': 0,
            'a_confirmer': 0,
            'inconnus': 0,
            'prix_manquants': 0,
            'prix_anomalies': 0,
            'sections': [l['label'] for l in lines if l['kind'] == 'section']
        }

        for l in lines:
            if l['kind'] != 'acte':
                results.append(l)
                continue

            target_pillars = [l.get('pillar') or pillar]
            m = match_line(self.index, l['label'], l['ctx'], target_pillars, org_id, l.get('types'))
            issue = classify(m, rule, th)
            exp = explain(m, issue, th)

            if issue == 'reconnu':
                summary['reconnus'] += 1
            elif issue == 'a_confirmer':
                summary['a_confirmer'] += 1
            else:
                summary['inconnus'] += 1

            p = l['price']
            if p.get('statut') == 'manquant':
                summary['prix_manquants'] += 1
            elif p.get('statut') == 'anomalie':
                summary['prix_anomalies'] += 1

            line_res = dict(l)
            line_res.update({
                'match': m,
                'issue': issue,
                'explication': exp,
                'candidat_retenu': m['cands'][0] if m.get('cands') else None
            })
            results.append(line_res)

        return {
            'filepath': filepath,
            'summary': summary,
            'schema': schema,
            'lines': results
        }
