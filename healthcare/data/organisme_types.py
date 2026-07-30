"""
Types d'établissement prestataire — liste de référence MedCare Connect.

Alignée sur les plans d'abonnement (Starter mono-pilier, Essentiel, Pro)
et le parcours d'inscription prestataire.
"""

from __future__ import annotations

# (order, name, description courte pour l'inscription)
CANONICAL_ORGANISME_TYPES: list[tuple[int, str, str]] = [
    (10,  "Praticien indépendant",               "Paramédical solo (domicile ou cabinet) — choisissez votre profession ci-dessous"),
    (20,  "Laboratoire d'analyses médicales",     "Analyses biologiques et biologie médicale"),
    (30,  "Centre d'imagerie médicale",           "Radiologie, échographie, scanner, IRM"),
    (40,  "Centre d'exploration fonctionnelle",   "EFR, ECG, électromyogramme, audiométrie…"),
    (50,  "Cabinet ou centre dentaire",           "Soins dentaires et parodontologie"),
    (60,  "Centre de dialyse",                   "Séances d'hémodialyse"),
    (70,  "Centre de santé mentale",             "Psychiatrie, psychologie, addictologie"),
    (80,  "Service ambulancier",                 "Transport médicalisé, SMUR, VSL"),
    (90,  "Centre de santé",                     "Structure polyvalente de proximité"),
    (100, "Clinique",                            "Clinique privée ou polyclinique"),
    (110, "Hôpital",                             "Établissement hospitalier public ou privé"),
]

# Alias historiques (seed / démo) → nom canonique
LEGACY_TYPE_ALIASES: dict[str, str] = {
    "Cabinet médical":             "Praticien indépendant",
    "Cabinet Médical":             "Praticien indépendant",
    "Cabinet dentaire":            "Cabinet ou centre dentaire",
    "Cabinet de kinésithérapie":   "Praticien indépendant",
    "Cabinet santé mentale":       "Centre de santé mentale",
    "Laboratoire":                 "Laboratoire d'analyses médicales",
    "Centre d'imagerie":           "Centre d'imagerie médicale",
    "Centre de Santé":             "Centre de santé",
    "Pharmacie":                   "Centre de santé",
}

