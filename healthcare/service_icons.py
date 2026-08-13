"""
Icônes des piliers (familles de soins / ServiceMedical) — alignées démo structures Thior.
"""
from __future__ import annotations

# Nom exact des piliers MedCare (catalog_pillars.PILLARS_FROM_DOCS)
SERVICE_MEDICAL_ICONS: dict[str, str] = {
    "Biologie médicale": "🧬",
    "Imagerie médicale": "🖥",
    "Explorations fonctionnelles": "⚡",
    "Ambulance médicalisée": "🚑",
    "Soins spécialisés": "🩺",
    "Soins dentaires": "🦷",
}

# Libellés alternatifs (démo / anciennes données)
_SERVICE_ALIASES: dict[str, str] = {
    "services d'ambulance": "Ambulance médicalisée",
    "service d'ambulance": "Ambulance médicalisée",
    "ambulance": "Ambulance médicalisée",
}

DEFAULT_SERVICE_ICON = "🏥"

# Slugs des 6 piliers — icônes affichage (prioritaires sur le champ DB)
OFFICIAL_PILIER_ICONS_BY_SLUG: dict[str, str] = {
    "biologie-medicale": "🧬",
    "imagerie-medicale": "🖥",
    "explorations-fonctionnelles": "⚡",
    "ambulance-medicalisee": "🚑",
    "soins-specialises": "🩺",
    "soins-dentaires": "🦷",
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


import unicodedata as _ud


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
    (("hématologie", "hémostase", "coagulation"), "🩸"),
    (("biochimie", "ionogramme"), "🧪"),
    (("immunologie", "auto-immun"), "🛡️"),
    (("sérologie", "virologie"), "🦠"),
    (("bactériologie", "coproculture", "hémoculture"), "🔬"),
    (("parasitologie", "mycologie", "paludisme"), "🪱"),
    (("endocrino", "fertilité", "amp"), "⚗️"),
    (("gaz du sang", "acido"), "💨"),
    (("anatomopath", "histologie", "cytologie"), "🔬"),
    (("moléculaire", " pcr"), "🧬"),
    (("toxicologie", "marqueurs tumoraux"), "⚠️"),
    (("radiographie", " radio"), "🩻"),
    (("échographie", "écho", "doppler"), "📡"),
    (("scanner", "tdm"), "🖥️"),
    (("irm",), "🧲"),
    (("interventionnelle", "biopsie"), "🎯"),
    (("cardiologie", "ecg", "holter", "mapa"), "❤️"),
    (("pneumologie", "spirom", "efr", "sommeil"), "🫁"),
    (("gastro", "endoscop", "coloscop", "manométrie"), "🫃"),
    (("neurologie", "eeg", "emg", "potentiels"), "🧠"),
    (("orl", "audiom", "vestibulaire"), "👂"),
    (("ophtalm", "oct", "fond d"), "👁️"),
    (("dermatologie", "dermoscop"), "🧴"),
    (("gynécologie", "obstét", "colposcop"), "🤰"),
    (("urologie", "cystoscop", "urodynam"), "💧"),
    (("néphrologie", "dialyse"), "💉"),
    (("andrologie", "sperm"), "👨‍⚕️"),
    (("orthopédie", "arthroscop"), "🦴"),
    (("kinésithérapie", "rééduc"), "🏃"),
    (("oncologie", "radiothérapie", "chimio"), "🎗️"),
    (("psychologie", "psychiatrie", "santé mentale"), "🧘"),
    (("médecine générale", "infirmier"), "🩺"),
    (("dentaire", "dent", "orthodont", "implant", "endodont"), "🦷"),
    (("ambulance", "smur", "évacuation", "rapatriement"), "🚑"),
    (("stomatologie", "buccale"), "🦷"),
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
        return stored[:12]
    return icon_for_service_name(getattr(service, "name", "") or "")


def icon_for_subfamily_label(label: str) -> str:
    """Icône indicative pour une sous-famille (type niveau 2) dans le tableau catalogue."""
    low = _normalize_name(label)
    if not low or low == "sans sous-famille":
        return "📂"
    for keywords, icon in _SUBFAMILY_KEYWORDS:
        if any(k in low for k in keywords):
            return icon
    return "🏷️"


def icons_for_pillars_data() -> list[tuple[str, str]]:
    """Paires (nom pilier, icône) pour migrations / chargement catalogue."""
    return list(SERVICE_MEDICAL_ICONS.items())
