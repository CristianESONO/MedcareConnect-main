"""
Types d'établissement prestataire — liste de référence MedCare Connect.

Alignée sur les plans d'abonnement (Starter mono-pilier, Essentiel, Pro)
et le parcours d'inscription prestataire.
"""

from __future__ import annotations

# (order, name, description courte pour l'inscription)
CANONICAL_ORGANISME_TYPES: list[tuple[int, str, str]] = [
    (10, "Praticien indépendant", "Médecin ou structure solo (cabinet, domicile)"),
    (20, "Cabinet médical", "Consultations générales ou spécialisées"),
    (30, "Cabinet dentaire", "Soins dentaires et parodontologie"),
    (40, "Cabinet de kinésithérapie", "Rééducation fonctionnelle, kiné"),
    (50, "Centre de dialyse", "Séances de dialyse"),
    (60, "Cabinet santé mentale", "Psychiatrie, psychologie, addictologie"),
    (70, "Laboratoire", "Analyses biologiques et biologie médicale"),
    (80, "Centre d'imagerie", "Radiologie, échographie, scanner, IRM"),
    (90, "Service ambulancier", "Transport médicalisé, SMUR, VSL"),
    (100, "Centre de santé", "Structure polyvalente de proximité"),
    (110, "Clinique", "Clinique privée ou polyclinique"),
    (120, "Hôpital", "Établissement hospitalier public ou privé"),
    (130, "Pharmacie", "Officine"),
]

# Alias historiques (seed / démo) → nom canonique
LEGACY_TYPE_ALIASES: dict[str, str] = {
    "Cabinet Médical": "Cabinet médical",
    "Centre de Santé": "Centre de santé",
}
