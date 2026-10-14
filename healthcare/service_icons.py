"""
Icônes des piliers (familles de soins / ServiceMedical) — Tabler Icons professionnels.
"""
from __future__ import annotations

import unicodedata as _ud
from django.utils.safestring import mark_safe

# Nom exact des piliers MedCare (catalog_pillars.PILLARS_FROM_DOCS)
SERVICE_MEDICAL_ICONS: dict[str, str] = {
    "Biologie médicale": mark_safe('<i class="ti ti-flask"></i>'),
    "Imagerie médicale": mark_safe('<i class="ti ti-scan"></i>'),
    "Explorations fonctionnelles": mark_safe('<i class="ti ti-activity"></i>'),
    "Ambulance médicalisée": mark_safe('<i class="ti ti-ambulance"></i>'),
    "Soins spécialisés": mark_safe('<i class="ti ti-stethoscope"></i>'),
    "Soins dentaires": mark_safe('<i class="ti ti-dental"></i>'),
}

# Libellés alternatifs (démo / anciennes données)
_SERVICE_ALIASES: dict[str, str] = {
    "services d'ambulance": "Ambulance médicalisée",
    "service d'ambulance": "Ambulance médicalisée",
    "ambulance": "Ambulance médicalisée",
}

DEFAULT_SERVICE_ICON = mark_safe('<i class="ti ti-building-hospital"></i>')

# Slugs des 6 piliers — icônes affichage (prioritaires sur le champ DB)
OFFICIAL_PILIER_ICONS_BY_SLUG: dict[str, str] = {
    "biologie-medicale": mark_safe('<i class="ti ti-flask"></i>'),
    "imagerie-medicale": mark_safe('<i class="ti ti-scan"></i>'),
    "explorations-fonctionnelles": mark_safe('<i class="ti ti-activity"></i>'),
    "ambulance-medicalisee": mark_safe('<i class="ti ti-ambulance"></i>'),
    "soins-specialises": mark_safe('<i class="ti ti-stethoscope"></i>'),
    "soins-dentaires": mark_safe('<i class="ti ti-dental"></i>'),
}

# Libellés compacts grille mobile (démo MOBILE PATIENT)
SERVICE_MOBILE_SHORT: dict[str, tuple[str, str]] = {
    "Biologie médicale": ("Biologie", "Analyses & labo"),
    "Imagerie médicale": ("Imagerie", "Radio, écho, IRM"),
    "Explorations fonctionnelles": ("Explorations", "ECG, EEG, EFR…"),
    "Ambulance médicalisée": ("Ambulance", "Transport médical"),
    "Soins spécialisés": ("Soins", "Kiné, soins spéc."),
    "Soins dentaires": ("Dentaire", "Soins dentaires"),
}


def strip_leading_emoji(text: str) -> str:
    """Retire les emojis/symboles Unicode en début de chaîne."""
    if not text:
        return ""
    return "".join(
        c for c in text
        if _ud.category(c) not in ("So", "Sm", "Sk", "Sc", "Cs", "Co", "Cn")
    ).strip()


def mobile_labels_for_service(name: str) -> tuple[str, str]:
    """Retourne (label court, sous-titre) pour la grille mobile."""
    if not name:
        return ("Famille", "")
    clean = strip_leading_emoji(name)
    if clean in SERVICE_MOBILE_SHORT:
        return SERVICE_MOBILE_SHORT[clean]
    if name in SERVICE_MOBILE_SHORT:
        return SERVICE_MOBILE_SHORT[name]
    short = clean.split(" médicale")[0].split(" médicalisée")[0].strip()
    if len(short) > 14:
        short = short[:12].rstrip() + "…"
    return (short or clean or name, "")


# Sous-familles (types niveau 2) — pastille tableau catalogue
_SUBFAMILY_KEYWORDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("hématologie", "hémostase", "coagulation"), '<i class="ti ti-droplet"></i>'),
    (("biochimie", "ionogramme"), '<i class="ti ti-flask"></i>'),
    (("immunologie", "auto-immun"), '<i class="ti ti-shield"></i>'),
    (("sérologie", "virologie"), '<i class="ti ti-virus"></i>'),
    (("bactériologie", "coproculture", "hémoculture"), '<i class="ti ti-microscope"></i>'),
    (("parasitologie", "mycologie", "paludisme"), '<i class="ti ti-bug"></i>'),
    (("endocrino", "fertilité", "amp"), '<i class="ti ti-test-pipe"></i>'),
    (("gaz du sang", "acido"), '<i class="ti ti-wind"></i>'),
    (("anatomopath", "histologie", "cytologie"), '<i class="ti ti-microscope"></i>'),
    (("moléculaire", " pcr"), '<i class="ti ti-dna"></i>'),
    (("toxicologie", "marqueurs tumoraux"), '<i class="ti ti-alert-triangle"></i>'),
    (("radiographie", " radio"), '<i class="ti ti-viewport-wide"></i>'),
    (("échographie", "écho", "doppler"), '<i class="ti ti-radar"></i>'),
    (("scanner", "tdm"), '<i class="ti ti-device-desktop"></i>'),
    (("irm",), '<i class="ti ti-magnet"></i>'),
    (("interventionnelle", "biopsie"), '<i class="ti ti-target"></i>'),
    (("cardiologie", "ecg", "holter", "mapa"), '<i class="ti ti-heart"></i>'),
    (("pneumologie", "spirom", "efr", "sommeil"), '<i class="ti ti-lungs"></i>'),
    (("gastro", "endoscop", "coloscop", "manométrie"), '<i class="ti ti-stomach"></i>'),
    (("neurologie", "eeg", "emg", "potentiels"), '<i class="ti ti-brain"></i>'),
    (("orl", "audiom", "vestibulaire"), '<i class="ti ti-ear"></i>'),
    (("ophtalm", "oct", "fond d"), '<i class="ti ti-eye"></i>'),
    (("dermatologie", "dermoscop"), '<i class="ti ti-sparkles"></i>'),
    (("gynécologie", "obstét", "colposcop"), '<i class="ti ti-woman"></i>'),
    (("urologie", "cystoscop", "urodynam"), '<i class="ti ti-droplet-half-2"></i>'),
    (("néphrologie", "dialyse"), '<i class="ti ti-needle"></i>'),
    (("andrologie", "sperm"), '<i class="ti ti-user"></i>'),
    (("orthopédie", "arthroscop"), '<i class="ti ti-bone"></i>'),
    (("kinésithérapie", "rééduc"), '<i class="ti ti-walk"></i>'),
    (("oncologie", "radiothérapie", "chimio"), '<i class="ti ti-ribbon"></i>'),
    (("psychologie", "psychiatrie", "santé mentale"), '<i class="ti ti-mood-smile"></i>'),
    (("médecine générale", "infirmier"), '<i class="ti ti-stethoscope"></i>'),
    (("dentaire", "dent", "orthodont", "implant", "endodont"), '<i class="ti ti-dental"></i>'),
    (("ambulance", "smur", "évacuation", "rapatriement"), '<i class="ti ti-ambulance"></i>'),
    (("stomatologie", "buccale"), '<i class="ti ti-dental"></i>'),
)


def _normalize_name(name: str) -> str:
    return (name or "").strip().lower()


def icon_for_service_name(name: str) -> str:
    if not name:
        return DEFAULT_SERVICE_ICON
    clean = strip_leading_emoji(name)
    if clean in SERVICE_MEDICAL_ICONS:
        return SERVICE_MEDICAL_ICONS[clean]
    if name in SERVICE_MEDICAL_ICONS:
        return SERVICE_MEDICAL_ICONS[name]
    low = _normalize_name(clean)
    if low in _SERVICE_ALIASES:
        return SERVICE_MEDICAL_ICONS.get(_SERVICE_ALIASES[low], DEFAULT_SERVICE_ICON)
    for pillar_name, icon in SERVICE_MEDICAL_ICONS.items():
        if _normalize_name(pillar_name) == low:
            return icon
    return DEFAULT_SERVICE_ICON


def icon_for_service_medical(service) -> str:
    """Retourne l'icône pilier officielle (slug), sinon DB, sinon mapping nom."""
    if service is None:
        return DEFAULT_SERVICE_ICON
    slug = (getattr(service, "slug", None) or "").strip()
    if slug in OFFICIAL_PILIER_ICONS_BY_SLUG:
        return OFFICIAL_PILIER_ICONS_BY_SLUG[slug]
    stored = (getattr(service, "icon", None) or "").strip()
    if stored:
        if stored.startswith("<i ") or stored.startswith("ti "):
            if stored.startswith("ti "):
                return mark_safe(f'<i class="{stored}"></i>')
            return mark_safe(stored)
    return icon_for_service_name(getattr(service, "name", "") or "")


def icon_for_subfamily_label(label: str) -> str:
    """Icône indicative pour une sous-famille (type niveau 2) dans le tableau catalogue."""
    low = _normalize_name(label)
    if not low or low == "sans sous-famille":
        return mark_safe('<i class="ti ti-folder"></i>')
    for keywords, icon in _SUBFAMILY_KEYWORDS:
        if any(k in low for k in keywords):
            return mark_safe(icon)
    return mark_safe('<i class="ti ti-tag"></i>')


def icons_for_pillars_data() -> list[tuple[str, str]]:
    """Paires (nom pilier, icône) pour migrations / chargement catalogue."""
    return list(SERVICE_MEDICAL_ICONS.items())
