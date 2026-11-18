"""
Script de synchronisation automatique du référentiel médical complet (1 836+ actes des 6 piliers)
depuis les modèles Django vers les outils d'importation autonomes.
Génère :
- documents/programme_import/referentiel_6piliers_medcare.json
- documents/programme_import/referentiel_data.js
- documents/programme_import/referentiel_onboarding.json
- programme_import_standalone/referentiel_6piliers_medcare.json
- programme_import_standalone/referentiel_data.js
"""
import os
import sys
import json
import re
import unicodedata

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medcare_connect.settings')
django.setup()

from healthcare.models import ActeMedical, ServiceMedical
from healthcare.prestataire_catalogue import prestataire_leaf_actes_queryset
from healthcare.catalog_excel import MEDICAL_SYNONYMS
from healthcare.reconciliation_engine import normalize_label

def build_referential():
    leaf_qs = prestataire_leaf_actes_queryset().select_related('service_medical_category', 'parent_service').order_by(
        'service_medical_category__order',
        'service_medical_category__name',
        'parent_service__name',
        'name'
    )
    
    actes_list = list(leaf_qs)
    print(f"Chargement de {len(actes_list)} actes feuilles du référentiel...")

    # Piliers officiels (1 à 6)
    piliers_meta = [
        {"id": 1, "slug": "biologie-medicale", "nom": "Biologie médicale", "icon": "flask"},
        {"id": 2, "slug": "imagerie-medicale", "nom": "Imagerie médicale", "icon": "photo"},
        {"id": 3, "slug": "explorations-fonctionnelles", "nom": "Explorations fonctionnelles", "icon": "activity"},
        {"id": 4, "slug": "ambulance-medicalisee", "nom": "Ambulance & Transport sanitaire", "icon": "ambulance"},
        {"id": 5, "slug": "soins-specialises", "nom": "Soins spécialisés", "icon": "stethoscope"},
        {"id": 6, "slug": "soins-dentaires", "nom": "Soins dentaires", "icon": "dental"}
    ]
    piliers_by_id = {p["id"]: p for p in piliers_meta}
    piliers_by_slug = {p["slug"]: p for p in piliers_meta}

    # Lexique d'intention externe
    lex_data = {}
    lex_path = os.path.join(base_dir, "lexique_intention_medcare.json")
    if os.path.exists(lex_path):
        try:
            with open(lex_path, "r", encoding="utf-8") as f:
                lex_data = json.load(f)
        except Exception as e:
            print(f"Avertissement : lecture lexique_intention_medcare.json : {e}")

    # Indexation
    by_norm_name = {}
    actes_by_pillar = {p["slug"]: [] for p in piliers_meta}
    js_actes = []
    global_aliases = {}  # alias_norm -> list of act_ids
    act_to_aliases = {}  # act_id -> set of alias strings

    for a in actes_list:
        cat = a.service_medical_category
        pid = cat.id if cat else 1
        pslug = cat.slug if cat and cat.slug in piliers_by_slug else "biologie-medicale"
        
        type_serv = a.parent_service.name if a.parent_service else (cat.name if cat else "Général")
        norm_name = normalize_label(a.name)
        # Préférer l'acte avec un code s'il y a doublon de nom
        if norm_name not in by_norm_name or (a.code and not ActeMedical.objects.get(pk=by_norm_name[norm_name]).code):
            by_norm_name[norm_name] = a.pk
        act_to_aliases[a.pk] = set()

        is_panel = "+" in a.name or " et " in a.name or " / " in a.name and "panel" in type_serv.lower()

        # Alias naturel depuis les séparateurs (uniquement pour les actes atomiques)
        if not is_panel:
            parts = [normalize_label(p) for p in re.split(r"[/()\[\]\-]", a.name) if normalize_label(p)]
            for p in parts:
                if len(p) >= 3 and p != norm_name:
                    act_to_aliases[a.pk].add(p)
                    global_aliases.setdefault(p, []).append(a.pk)

        # Alias exact du nom
        global_aliases.setdefault(norm_name, []).append(a.pk)

        js_actes.append({
            "id": a.pk,
            "pid": pid,
            "nom": a.name,
            "type": type_serv,
            "code": a.code or "",
            "ref_prix": float(a.reference_price) if a.reference_price is not None else None,
            "delai": a.rdv_prerequisites or ""
        })

    # Intégration MEDICAL_SYNONYMS
    for std_name, syn_list in MEDICAL_SYNONYMS.items():
        n_std = normalize_label(std_name)
        target_id = by_norm_name.get(n_std)
        if not target_id:
            for n_act, aid in by_norm_name.items():
                if n_std in n_act or n_act in n_std:
                    target_id = aid
                    break
        if target_id:
            for syn in syn_list:
                n_syn = normalize_label(syn)
                if n_syn:
                    act_to_aliases[target_id].add(n_syn)
                    global_aliases.setdefault(n_syn, []).append(target_id)

    # Intégration Lexique d'Intention
    for variant, meta in lex_data.items():
        n_var = normalize_label(variant)
        tgt_name = meta.get("acte") or meta.get("prestation") or ""
        n_tgt = normalize_label(tgt_name)
        target_id = by_norm_name.get(n_tgt)
        if not target_id:
            for n_act, aid in by_norm_name.items():
                if n_tgt and (n_tgt in n_act or n_act in n_tgt):
                    target_id = aid
                    break
        if target_id and n_var:
            act_to_aliases[target_id].add(n_var)
            global_aliases.setdefault(n_var, []).append(target_id)

    # Arbitrage CDC §7 & Résolution des collisions sur alias identiques
    # Si un alias pointe vers plusieurs actes qui ont le même nom normalisé ou dont un a un code
    act_map_by_pk = {a.pk: a for a in actes_list}
    clean_aliases = {}
    for k, ids in global_aliases.items():
        uniq_ids = sorted(list(set(ids)))
        if len(uniq_ids) > 1:
            # Vérifier si ce sont des doublons du même nom médical
            names = set(normalize_label(act_map_by_pk[i].name) for i in uniq_ids if i in act_map_by_pk)
            # Priorité à l'acte avec code ou à l'acte dont le nom normalisé correspond le plus
            coded = [i for i in uniq_ids if i in act_map_by_pk and act_map_by_pk[i].code]
            if len(names) == 1 and coded:
                clean_aliases[k] = [coded[0]]
                continue
            # Pour "nfs", la référence officielle est NFS (hémogramme)
            if k == "nfs":
                nfs_act = next((i for i in uniq_ids if "hemogramme" in normalize_label(act_map_by_pk[i].name)), uniq_ids[0])
                clean_aliases[k] = [nfs_act]
                continue
            # Pour "tptck", la référence officielle est le bilan d'hémostase
            if "tptck" in k:
                tp_act = next((i for i in uniq_ids if "hemostase" in normalize_label(act_map_by_pk[i].name)), uniq_ids[0])
                clean_aliases[k] = [tp_act]
                continue
        clean_aliases[k] = uniq_ids

    # Construire la liste inverse propre depuis clean_aliases
    act_to_clean_aliases = {a.pk: [] for a in actes_list}
    for alias_str, ids in clean_aliases.items():
        if len(ids) == 1:
            aid = ids[0]
            if aid in act_to_clean_aliases:
                act_to_clean_aliases[aid].append(alias_str)

    # Construction du JSON des 6 piliers
    piliers_dict = {}
    for p in piliers_meta:
        piliers_dict[p["slug"]] = {
            "pilier_id": p["id"],
            "pilier_slug": p["slug"],
            "pilier_nom": p["nom"],
            "lexique_intention_uniquement": False,
            "nb_actes": 0,
            "actes": []
        }

    for a in actes_list:
        cat = a.service_medical_category
        pslug = cat.slug if cat and cat.slug in piliers_dict else "biologie-medicale"
        type_serv = a.parent_service.name if a.parent_service else (cat.name if cat else "Général")
        aliases_list = sorted(act_to_clean_aliases.get(a.pk, []))

        piliers_dict[pslug]["actes"].append({
            "id": a.pk,
            "type_service": type_serv,
            "code": a.code or "",
            "acte_standardise": a.name,
            "actes_composants": [],
            "lexique_intention": aliases_list,
            "tarif_fcfa_indicatif": float(a.reference_price) if a.reference_price is not None else None,
            "delai_indicatif": a.rdv_prerequisites or ""
        })

    for pslug in piliers_dict:
        piliers_dict[pslug]["nb_actes"] = len(piliers_dict[pslug]["actes"])

    full_referentiel_json = {
        "plateforme": "MedCare Connect",
        "version": "2.1",
        "date_generation": "2026-10-29",
        "description": "Référentiel Médical Officiel MedCare 6 Piliers synchronisé avec la base de données Django",
        "total_actes": len(actes_list),
        "total_aliases": len(clean_aliases),
        "piliers": piliers_dict
    }

    # Fichiers cibles
    targets_json = [
        os.path.join(base_dir, "documents", "programme_import", "referentiel_6piliers_medcare.json"),
        os.path.join(base_dir, "documents", "programme_import", "referentiel_onboarding.json"),
        os.path.join(base_dir, "programme_import_standalone", "referentiel_6piliers_medcare.json"),
    ]

    for p in targets_json:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(full_referentiel_json, f, ensure_ascii=False, indent=2)
        print(f"✓ Écrit : {p} ({len(actes_list)} actes)")

    # Fichiers JS pour les interfaces web standalone
    js_content = f"// Référentiel Médical MedCare 6 Piliers synchronisé avec la base de données ({len(actes_list)} actes, {len(clean_aliases)} alias)\n"
    js_content += f"window.MEDCARE_REF = {json.dumps({'version': '2.1', 'total_actes': len(actes_list), 'piliers': piliers_meta, 'actes': js_actes, 'aliases': clean_aliases}, ensure_ascii=False)};\n"

    targets_js = [
        os.path.join(base_dir, "documents", "programme_import", "referentiel_data.js"),
        os.path.join(base_dir, "programme_import_standalone", "referentiel_data.js"),
    ]

    for p in targets_js:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(js_content)
        print(f"✓ Écrit : {p} ({len(js_actes)} actes JS, {len(clean_aliases)} alias)")

if __name__ == "__main__":
    build_referential()
