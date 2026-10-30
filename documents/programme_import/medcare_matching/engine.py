import os
import re
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

def is_composite_label(label: str) -> bool:
    s = (label or "").lower()
    for pat in [r"\bpv\b.*\bchlam\b.*\bmyco\b", r"\bchlamydia\b.*\bmycoplasme\b", r"\bglycemie\b.*\bcreatinine\b", r"\bnfs\b.*\bglycemie\b"]:
        if re.search(pat, s):
            return True
    toks = set(re.findall(r"\w+", s))
    if {"pv", "chlam", "myco"}.issubset(toks) or {"pv", "chlamydia", "mycoplasme"}.issubset(toks):
        return True
    return False

def match_line(idx: ReferentialIndex, label: str, ctx_label: str, pillars: List[str], org_id: Optional[str] = None, types: Optional[List[str]] = None) -> Dict[str, Any]:
    """Rapproche une ligne selon la cascade à 6 niveaux du manuel §8.1."""
    if is_composite_label(label):
        return {
            "exact": False,
            "composite": True,
            "method": "composite",
            "cands": [],
            "usedText": label
        }

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
    """Moteur de réconciliation conforme au manuel d'architecture et aux specs Tri-Tarifs."""

    def __init__(self, referentiel_path: str, aliases_path: Optional[str] = None,
                 panels_path: Optional[str] = None):
        with open(referentiel_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extraction des actes selon la structure du fichier référentiel
        if isinstance(data, list):
            actes = data
        elif isinstance(data, dict) and "actes" in data:
            actes = data["actes"]
        elif isinstance(data, dict) and "piliers" in data:
            # Format referentiel_6piliers_medcare.json
            actes = []
            slug_map = {1: "bio", 2: "img", 3: "exp", 4: "ambu", 5: "soins", 6: "dent"}
            for pslug, pdata in data["piliers"].items():
                pid = pdata.get("pilier_id", 1)
                slug = slug_map.get(pid, pslug)
                for item in pdata.get("actes", []):
                    actes.append({
                        "id": item.get('id', len(actes) + 1),
                        "code": item.get('code', ''),
                        "pillar": slug,
                        "type": item.get("type_service", ""),
                        "name": item.get("acte_standardise", ""),
                        "kind": item.get("kind", "acte"),
                        "lexique": item.get("lexique_intention", []),
                        "ref_prix": item.get("tarif_fcfa_indicatif"),
                        "delai": item.get("delai_indicatif", ""),
                        # §Lettre-clé NGAP Sénégal (B, Z, KE, K, KC, C, CS, D, aucune)
                        "lettre_cle": item.get("lettre_cle"),
                        "coefficient": item.get("coefficient"),
                    })
        else:
            actes = []

        aliases = []
        if aliases_path and os.path.exists(aliases_path):
            with open(aliases_path, 'r', encoding='utf-8') as f:
                aliases = json.load(f)

        # Référentiel panels/combinaisons : {acte_id: [composant_id, ...]}
        self.panels_ref: Dict[str, List[Any]] = {}
        if panels_path and os.path.exists(panels_path):
            with open(panels_path, 'r', encoding='utf-8') as f:
                panels_data = json.load(f)
            # Accepte liste [{acte_id, composants:[...]}] ou dict {acte_id: [...]}
            if isinstance(panels_data, list):
                for p in panels_data:
                    self.panels_ref[str(p.get('acte_id', ''))] = p.get('composants', [])
            elif isinstance(panels_data, dict):
                self.panels_ref = {str(k): v for k, v in panels_data.items()}

        self.index = ReferentialIndex(actes, aliases)
        self.actes = actes
        self.aliases = aliases

    # ------------------------------------------------------------------
    # Détection des doublons (deux libellés → même acte → conflit prix)
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_collisions(results: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Retourne {acte_id: [libelle1, libelle2, ...]} pour les actes avec >1 ligne."""
        mapping: Dict[str, List[str]] = {}
        for l in results:
            if l.get('kind') != 'acte':
                continue
            cand = l.get('candidat_retenu')
            if not cand:
                continue
            aid = str(cand['acte'].get('id', ''))
            if not aid:
                continue
            mapping.setdefault(aid, []).append(l['label'])
        return {k: v for k, v in mapping.items() if len(v) > 1}

    # ------------------------------------------------------------------
    # Exports tri-tarifs conformes à la spec Reconciliation 3tarifs
    # ------------------------------------------------------------------
    def build_tariff_rows(self, results: List[Dict[str, Any]], structure_id: str,
                          master_labels: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        Export grille tarifaire : {structure_id, acte_id, acte, regime, montant, pris_en_charge}.
        Une ligne par régime (comptant / ipm / assurance) par acte, dédupliqué.
        Les panels sont exclus (export séparé via build_panel_rows).
        Les doublons : seule la ligne maître est exportée.
        """
        collisions = self._detect_collisions(results)
        seen_ids: set = set()
        out = []

        for l in results:
            if l.get('kind') != 'acte':
                continue
            cand = l.get('candidat_retenu')
            if not cand:
                continue
            aid = str(cand['acte'].get('id', ''))
            if not aid:
                continue

            # Routing panel → export séparé
            if aid in self.panels_ref or l.get('dest') == 'panel':
                continue

            # Doublons : vérifier si cette ligne est la maître
            if aid in collisions and len(collisions[aid]) > 1:
                master_lbl = (master_labels or {}).get(aid, collisions[aid][0])
                if l['label'] != master_lbl:
                    continue  # Ignorer les lignes non-maîtres

            if aid in seen_ids:
                continue
            seen_ids.add(aid)

            act_name = cand['acte'].get('name')
            pc = l.get('prix_comptant')
            pi = l.get('prix_ipm')
            pa = l.get('prix_assurance')
            npc_ipm = l.get('status_ipm') == 'excluded'
            npc_ass = l.get('status_assurance') == 'excluded'

            for regime, montant, npc in [
                ('comptant', pc, False),
                ('ipm',      pi, npc_ipm),
                ('assurance', pa, npc_ass),
            ]:
                out.append({
                    'structure_id': structure_id,
                    'acte_id': int(aid) if aid.isdigit() else aid,
                    'acte': act_name,
                    'regime': regime,
                    'montant': None if npc else montant,
                    'pris_en_charge': not npc,
                })
        return out

    def build_panel_rows(self, results: List[Dict[str, Any]], structure_id: str,
                         master_labels: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        Export panels/combinaisons : {structure_id, acte_id, nom, type, composants, a_composer, tarifs}.
        """
        collisions = self._detect_collisions(results)
        seen_ids: set = set()
        out = []

        for l in results:
            if l.get('kind') != 'acte':
                continue
            cand = l.get('candidat_retenu')
            if not cand:
                continue
            aid = str(cand['acte'].get('id', ''))

            # Uniquement les panels
            is_panel = (aid in self.panels_ref) or l.get('composite') or l.get('dest') == 'panel'
            if not is_panel:
                continue

            if aid in collisions and len(collisions[aid]) > 1:
                master_lbl = (master_labels or {}).get(aid, collisions[aid][0])
                if l['label'] != master_lbl:
                    continue

            if aid in seen_ids:
                continue
            seen_ids.add(aid)

            pc = l.get('prix_comptant')
            pi = l.get('prix_ipm')
            pa = l.get('prix_assurance')
            npc_ipm = l.get('status_ipm') == 'excluded'
            npc_ass = l.get('status_assurance') == 'excluded'

            out.append({
                'structure_id': structure_id,
                'acte_id': int(aid) if aid.isdigit() else aid,
                'nom': cand['acte'].get('name'),
                'type': 'panel',
                'composants': self.panels_ref.get(aid, []),
                'a_composer': aid not in self.panels_ref,
                'tarifs': {
                    'comptant':  {'montant': pc,                     'pris_en_charge': True},
                    'ipm':       {'montant': None if npc_ipm else pi, 'pris_en_charge': not npc_ipm},
                    'assurance': {'montant': None if npc_ass else pa, 'pris_en_charge': not npc_ass},
                },
            })
        return out

    def build_alias_rows(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Export alias validés (lexique global, sans prix) :
        {alias, libelle_source, acte_id, acte_standardise, type}.
        """
        out = []
        seen: set = set()
        for l in results:
            if l.get('kind') != 'acte':
                continue
            if l.get('issue') not in ('reconnu', 'a_confirmer'):
                continue
            cand = l.get('candidat_retenu')
            if not cand:
                continue
            aid = str(cand['acte'].get('id', ''))
            lbl = l['label']
            key = f"{aid}|{lbl}"
            if key in seen:
                continue
            seen.add(key)
            out.append({
                'alias': lbl,
                'libelle_source': lbl,
                'acte_id': int(aid) if aid.isdigit() else aid,
                'acte_standardise': cand['acte'].get('name'),
                'type': cand['acte'].get('type', ''),
            })
        return out

    # ------------------------------------------------------------------
    # Réconciliation principale
    # ------------------------------------------------------------------
    def reconcile_file(self, filepath: str, default_pillar: Optional[str] = None,
                       org_id: Optional[str] = None, rule: str = 'V1',
                       th: Dict[str, float] = None) -> Dict[str, Any]:
        """Lit un fichier de n'importe quel format et le réconcilie entièrement."""
        if th is None:
            th = DEFAULT_THRESHOLDS

        rows = read_any_file(filepath)
        schema = detect_schema(rows)
        parsed = read_rows(rows, schema['roles'], default_pillar)

        lines = parsed['lines']
        all_pillars = ['bio', 'img', 'exp', 'ambu', 'soins', 'dent']
        default_p_list = [default_pillar] if default_pillar else all_pillars

        actes_lines = [l for l in lines if l['kind'] == 'acte']
        results = []

        summary = {
            'total_rows': len(rows),
            'total_lines': len(lines),
            'actes_count': len(actes_lines),
            'reconnus': 0,
            'a_confirmer': 0,
            'inconnus': 0,
            'composites': 0,       # Panels/combinaisons détectés
            'doublons': 0,          # Actes appariés en doublon (conflit prix)
            'comptant_seul': 0,     # Actes sans IPM ET sans assurance (NPC les deux)
            'prix_comptant_manquant': 0,  # Actes dont le prix comptant est absent
            'prix_manquants': 0,
            'prix_anomalies': 0,
            'sections': [l['label'] for l in lines if l['kind'] == 'section']
        }

        for l in lines:
            if l['kind'] != 'acte':
                results.append(l)
                continue

            target_pillars = [l['pillar']] if l.get('pillar') else default_p_list
            m = match_line(self.index, l['label'], l['ctx'], target_pillars, org_id, l.get('types'))
            issue = classify(m, rule, th)
            exp = explain(m, issue, th)

            # Routing panel/composite → dest = 'panel'
            if m.get('composite'):
                summary['composites'] += 1
                cand = m['cands'][0] if m.get('cands') else None
                aid = str(cand['acte'].get('id', '')) if cand else ''
                dest = 'panel' if aid in self.panels_ref else 'panel_non_reconnu'
            else:
                dest = None

            if issue == 'reconnu':
                summary['reconnus'] += 1
            elif issue == 'a_confirmer':
                summary['a_confirmer'] += 1
            elif not m.get('composite'):
                summary['inconnus'] += 1

            # Comptant-seul : NPC IPM ET NPC assurance
            npc_ipm = l.get('status_ipm') == 'excluded'
            npc_ass = l.get('status_assurance') == 'excluded'
            if npc_ipm and npc_ass:
                summary['comptant_seul'] += 1

            # Prix comptant manquant
            if l.get('prix_comptant') is None:
                summary['prix_comptant_manquant'] += 1

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
                'candidat_retenu': m['cands'][0] if m.get('cands') else None,
                'dest': dest,        # 'panel' | 'panel_non_reconnu' | None
            })
            results.append(line_res)

        # Détection des doublons (après réconciliation complète)
        collisions = self._detect_collisions(results)
        doublons_ids = {aid for aid, lbls in collisions.items() if len(lbls) > 1}
        summary['doublons'] = len(doublons_ids)

        # Marquer les lignes en doublon
        for l in results:
            if l.get('kind') != 'acte':
                continue
            cand = l.get('candidat_retenu')
            if not cand:
                continue
            aid = str(cand['acte'].get('id', ''))
            if aid in doublons_ids:
                l['issue_doublon'] = True
                l['doublon_with'] = [lb for lb in collisions[aid] if lb != l['label']]

        return {
            'filepath': filepath,
            'summary': summary,
            'schema': schema,
            'lines': results,
            'collisions': collisions,   # {acte_id: [libelle1, libelle2]}
        }
