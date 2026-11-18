"""
seed_demo_acts.py — Injecte dans la DB tous les actes et catégories de la démo
(DEMO_DESKTOP_PATIENT.html) en utilisant exactement les mêmes noms.

Usage (depuis la racine du projet) :
    python seed_demo_acts.py

Ce script est IDEMPOTENT : il utilise get_or_create, donc tu peux le relancer
sans risque de doublons.
"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medcare_connect.settings")

import django
django.setup()

from healthcare.models import ServiceMedical, ActeMedical

# ============================================================
# Arbre des actes — noms EXACTS comme dans DEMO_DESKTOP_PATIENT.html
# ============================================================
DEMO_TREE = {
    "Biologie medicale": {
        "pillar_name": "Biologie médicale",
        "categories": {
            "Hématologie": [
                "NFS / Hémogramme", "Réticulocytes", "VS", "Frottis sanguin",
                "Groupe ABO/Rhésus", "RAI", "Test de Coombs direct",
                "Test de Coombs indirect", "Électrophorèse de l'hémoglobine",
                "Vitamine B12", "Folates (B9)", "Fer sérique", "Ferritine",
                "Transferrine / CST",
            ],
            "Hémostase / Coagulation": [
                "TP / INR", "TCA", "Fibrinogène", "D-Dimères",
                "Temps de thrombine (TT)", "Activité anti-Xa",
                "Dosage facteur VIII", "Dosage facteur IX",
            ],
            "Biochimie & Ionogramme": [
                "Glycémie à jeun", "HbA1c", "Urée sanguine", "Créatininémie",
                "Natrémie", "Kaliémie", "Chlorémie", "Calcémie", "Phosphorémie",
                "Magnésémie", "ASAT", "ALAT", "GGT", "PAL", "Bilirubine totale",
                "Bilirubine conjuguée", "Albumine", "Protéines totales",
                "Électrophorèse des protéines", "Lipase", "Amylase", "CRP",
                "Procalcitonine", "Cholestérol total", "HDL", "LDL",
                "Triglycérides", "Apolipoprotéines A/B", "Lactates",
            ],
            "Immunologie & Auto-immunité": [
                "ANA / AAN", "FR (facteur rhumatoïde)", "Anti-CCP",
                "Complément C3", "Complément C4", "IgG / IgA / IgM",
                "Anti-dsDNA", "Anti-Sm", "Anti-RNP", "Anti-SSA / SSB",
                "Anticoagulant lupique", "Anticardiolipines IgG/IgM",
                "Anti-β2GP1", "ANCA MPO/PR3",
            ],
            "Sérologie & Virologie": [
                "VIH Ag/Ac", "Charge virale VIH", "HBsAg", "Anti-HBs",
                "Anti-HBc total", "Anti-HBc IgM", "HBeAg / Anti-HBe",
                "ADN VHB (charge virale HBV)", "Anti-VHC",
                "ARN VHC (charge virale HCV)", "Syphilis VDRL", "Syphilis TPHA",
                "Dengue NS1/IgM/IgG", "Chikungunya IgM/IgG",
                "Toxoplasmose IgG/IgM", "Rubéole IgG/IgM",
                "CMV IgG/IgM", "EBV (Epstein-Barr)",
            ],
            "Bactériologie": [
                "ECBU + antibiogramme", "Coproculture", "Hémocultures",
                "ECB plaies / pus", "Prélèvement vaginal / cervico-vaginal",
                "ECBE / expectorations", "Culture crachats", "Recherche BK / BAAR",
            ],
            "Parasitologie & Mycologie": [
                "Goutte épaisse / TDR paludisme",
                "Examen parasitologique des selles", "Filariose sanguine",
                "Bilharziose (urines/selles)", "Examen mycologique peau/ongles",
                "Recherche Candida",
            ],
            "Endocrinologie": [
                "TSH", "FT4", "FT3", "Anti-TPO", "Anti-Thyroglobuline",
                "Aldostéronémie", "Rénine", "Cortisol", "Prolactine",
                "FSH", "LH", "Estradiol", "Progestérone", "Testostérone", "AMH",
            ],
            "Fertilité / AMP": [
                "Spermogramme", "Spermocytogramme",
                "Test de migration-survie (TMS)",
                "Spermoculture + antibiogramme", "AMH (réserve ovarienne)",
            ],
            "Gaz du sang & Acido-basique": [
                "Gaz du sang artériel", "Gaz du sang capillaire",
                "Lactates artériels",
            ],
            "Anatomopathologie": [
                "Examen anapath. pièce opératoire",
                "Examen anapath. biopsie",
                "Immunohistochimie",
                "Immunofluorescence directe",
            ],
            "Cytologie": [
                "Cytologie liquide pleural", "Cytologie ascite",
                "Cytologie LCR", "Cytologie urinaire",
                "Frottis cervico-vaginal (FCV)", "Cytoponction thyroïde",
                "Cytoponction ganglion",
            ],
            "Biologie moléculaire / PCR": [
                "PCR Chlamydia / Gonocoque", "PCR HPV (génotypage)",
                "PCR BK", "GeneXpert MTB/RIF", "PCR respiratoires multiplex",
            ],
            "Toxicologie": [
                "Drogues urinaires (panel)", "Alcoolémie",
                "Paracétamol plasmatique", "Carboxyhémoglobine",
                "Métaux lourds",
            ],
            "Marqueurs tumoraux": [
                "PSA total", "PSA libre", "CEA", "AFP",
                "CA 125", "CA 19-9", "CA 15-3", "βHCG quantitatif",
            ],
        },
    },
    "Imagerie medicale": {
        "pillar_name": "Imagerie médicale",
        "categories": {
            "Radiographie": [
                "Radio thorax", "Radio abdomen (ASP)", "Radio rachis cervical",
                "Radio rachis dorsal", "Radio rachis lombaire", "Radio bassin",
                "Radio membre — genou", "Radio membre — épaule",
                "Radio membre — cheville / pied", "Radio crâne",
            ],
            "Échographie": [
                "Échographie abdominale", "Échographie pelvienne",
                "Échographie endovaginale", "Échographie obstétricale T1",
                "Échographie morphologique T2", "Échographie T3 (biométrie)",
                "Échographie thyroïdienne", "Échographie testiculaire",
                "Échographie parties molles", "Mammographie",
            ],
            "Échodoppler": [
                "Échodoppler veineux membres inférieurs",
                "Échodoppler artériel membres inférieurs",
                "Échodoppler carotidien + vertébral",
                "Écho-cœur (échocardiographie transthoracique)",
            ],
            "Scanner (TDM)": [
                "Scanner cérébral sans injection",
                "Scanner cérébral avec injection",
                "Scanner thoracique",
                "Scanner TAP (thoraco-abdomino-pelvien)",
                "Scanner sinus",
                "Angio-TDM cérébral",
            ],
            "IRM": [
                "IRM cérébrale sans injection", "IRM cérébrale avec injection",
                "IRM rachis cervical", "IRM rachis lombaire",
                "IRM abdomen / pelvis", "IRM prostate", "IRM cardiaque",
            ],
            "Biopsies guidées": [
                "Biopsie hépatique (écho-guidée)",
                "Biopsie mammaire (écho-guidée)",
                "Biopsie rénale (écho-guidée)",
                "Biopsie pulmonaire (scanner-guidée)",
                "Biopsie thyroïdienne (écho-guidée)",
                "Biopsie ganglionnaire",
                "Biopsie osseuse (scanner-guidée)",
            ],
            "Ponctions guidées": [
                "Ponction pleurale (écho-guidée)",
                "Ponction abdominale / ascite",
                "Ponction articulaire genou",
                "Ponction articulaire épaule / hanche",
                "Ponction mammaire diagnostique",
            ],
            "Drainages guidés": [
                "Drainage pleural (thoracique)",
                "Drainage abdominal / abcès",
                "Drainage biliaire",
                "Néphrostomie (drainage urinaire)",
            ],
        },
    },
    "Explorations fonctionnelles": {
        "pillar_name": "Explorations fonctionnelles",
        "categories": {
            "Cardiologie": [
                "ECG standard 12 dérivations",
                "Épreuve d'effort (test effort cardiaque)",
                "Holter ECG 24h",
                "Holter tensionnel MAPA 24h",
                "Tilt test (table basculante)",
                "Test de marche 6 minutes",
            ],
            "Pneumologie": [
                "EFR / Spirométrie standard",
                "Spirométrie + bronchodilatateur",
                "Pléthysmographie corps entier",
                "Test de diffusion DLCO",
                "Oxymétrie nocturne",
                "Polygraphie ventilatoire (apnées du sommeil)",
            ],
            "Gastro-entérologie": [
                "FOGD (fibroscopie gastrique)", "Coloscopie",
                "Rectosigmoïdoscopie", "Manométrie œsophagienne",
                "pH-métrie œsophagienne",
                "Test respiratoire à l'hydrogène",
            ],
            "Neurologie": [
                "EEG standard", "EEG de sommeil",
                "EMG (électromyogramme)",
                "Potentiels évoqués visuels (PEV)",
                "Potentiels évoqués auditifs (PEA)",
                "Potentiels évoqués somesthésiques (PES)",
            ],
            "ORL": [
                "Audiométrie tonale", "Audiométrie vocale",
                "Impédancemétrie (tympanométrie)",
                "Tests vestibulaires VNG", "Fibroscopie ORL",
            ],
            "Ophtalmologie": [
                "Acuité visuelle + réfraction", "Fond d'œil",
                "OCT (tomographie optique cohérente)",
                "Champ visuel automatisé", "Pachymétrie cornéenne",
                "Topographie cornéenne", "Biométrie oculaire",
            ],
            "Dermatologie": [
                "Dermoscopie", "Cartographie des nævus",
                "Tests allergologiques cutanés",
            ],
            "Gynécologie": [
                "Hystérosalpingographie (HSG)",
                "Hystéroscopie diagnostique",
                "Colposcopie", "Monitoring ovulatoire",
            ],
            "Urologie": [
                "Débitmétrie urinaire", "Bilan urodynamique complet",
            ],
            "Andrologie / Fertilité": [
                "Spermogramme (exploration fonctionnelle)",
                "Spermocytogramme", "Test de migration-survie",
                "Bilan infertilité masculine",
            ],
            "Hématologie clinique": [
                "Myélogramme", "Biopsie ostéo-médullaire",
                "Test de fragilité osmotique",
            ],
        },
    },
    "Ambulance medicalisee": {
        "pillar_name": "Ambulance médicalisée",
        "categories": {
            "Transport sanitaire": [
                "Ambulance simple",
                "Ambulance médicalisée avec infirmier",
                "Ambulance médicalisée avec médecin",
                "Transport réanimatoire",
                "Évacuation sanitaire",
            ],
            "Rapatriement": [
                "Rapatriement national",
                "Rapatriement international",
            ],
            "Couverture & assistance": [
                "Couverture médicale sportive",
                "Couverture médicale de manifestation publique",
                "Assistance médicale sur site",
            ],
        },
    },
    "Soins specialises": {
        "pillar_name": "Soins spécialisés",
        "categories": {
            "Médecine générale": [
                "Suture plaie simple", "Suture plaie complexe",
                "Incision & drainage abcès cutané",
                "Nébulisation thérapeutique", "Oxygénothérapie",
            ],
            "Cardiologie": [
                "ECG à domicile", "Pose / retrait Holter ECG",
                "Surveillance post-urgence cardiaque",
            ],
            "ORL": [
                "Lavage d'oreille", "Extraction bouchon de cérumen",
                "Ablation corps étranger ORL", "Cautérisation épistaxis",
                "Pose / retrait mèche nasale",
            ],
            "Ophtalmologie": [
                "Retrait corps étranger oculaire", "Lavage oculaire médical",
                "Laser YAG", "Laser rétinien", "Injection intravitréenne",
            ],
            "Dermatologie": [
                "Cryothérapie cutanée", "Exérèse lésion cutanée bénigne",
                "Électrocoagulation", "Biopsie cutanée",
                "Peeling médical", "Laser dermatologique",
            ],
            "Gynécologie": [
                "Pose DIU (stérilet)", "Retrait DIU",
                "Pose implant contraceptif", "Retrait implant",
                "Biopsie gynécologique", "Cryothérapie cervicale",
                "Aspiration endo-utérine",
            ],
            "Urologie": [
                "Sondage vésical", "Changement de sonde",
                "Instillation vésicale",
            ],
            "Soins infirmiers": [
                "Pansement simple", "Pansement complexe",
                "Perfusion IV", "Injection IM / SC",
                "Surveillance glycémique", "Soins de plaies chroniques",
                "Nursing médicalisé",
            ],
            "Rhumatologie / Orthopédie": [
                "Infiltration articulaire genou",
                "Infiltration articulaire épaule",
                "Viscosupplémentation", "Injection PRP",
                "Ponction articulaire évacuatrice",
                "Immobilisation orthopédique",
            ],
            "Pédiatrie": [
                "Nébulisation pédiatrique", "Lavage nasal médicalisé",
                "Soins plaies pédiatriques", "Réhydratation orale supervisée",
                "Perfusion pédiatrique",
            ],
            "Kinésithérapie": [
                "Rééducation post-traumatique",
                "Rééducation post-opératoire genou",
                "Rééducation lombalgie / cervicalgie",
                "Kiné respiratoire adulte",
                "Kiné respiratoire pédiatrique",
                "Rééducation post-AVC",
                "Rééducation périnéale post-partum",
                "Drainage lymphatique manuel",
                "Kinésithérapie à domicile",
            ],
            "Dialyse / Néphrologie": [
                "Hémodialyse chronique", "Hémodialyse aiguë",
                "Dialyse péritonéale", "Soins cathéter de dialyse",
            ],
            "Psychologie": [
                "Consultation de psychologie initiale",
                "Séance de psychologie de suivi",
                "Thérapie individuelle", "Thérapie de couple",
                "Thérapie familiale", "Téléconsultation psychologique",
            ],
            "Psychiatrie": [
                "Consultation psychiatrique initiale",
                "Consultation psychiatrique de suivi",
                "Évaluation psychiatrique diagnostique",
                "Ajustement traitement psychotrope",
                "Téléconsultation psychiatrique",
            ],
            "Oncologie / Radiothérapie": [
                "Consultation d'oncologie médicale",
                "Administration chimiothérapie ambulatoire",
                "Séance de radiothérapie",
                "Soins palliatifs ambulatoires",
            ],
        },
    },
    "Soins dentaires": {
        "pillar_name": "Soins dentaires",
        "categories": {
            "Consultations dentaires": [
                "Consultation dentaire standard",
                "Consultation dentaire spécialisée",
                "Consultation d'urgence dentaire",
                "Bilan bucco-dentaire complet",
            ],
            "Soins conservateurs": [
                "Détartrage complet",
                "Détartrage + polissage + fluoration",
                "Traitement carie (composite)",
                "Obturation amalgame",
            ],
            "Endodontie": [
                "Traitement endodontique mono-radiculaire",
                "Traitement endodontique bi-radiculaire",
                "Traitement endodontique multi-radiculaire",
                "Reprise endodontique",
            ],
            "Chirurgie dentaire": [
                "Extraction simple",
                "Extraction chirurgicale",
                "Extraction dent de sagesse incluse",
                "Drainage abcès dentaire",
            ],
            "Prothèses": [
                "Couronne céramique / zirconium",
                "Bridge 3 éléments",
                "Prothèse amovible partielle",
                "Prothèse complète",
            ],
            "Implantologie": [
                "Consultation implantaire",
                "Pose d'implant dentaire",
                "Greffe osseuse",
                "Couronne sur implant",
            ],
            "Orthodontie": [
                "Appareil orthodontique fixe (arcade)",
                "Appareil amovible",
                "Gouttières transparentes (aligneurs)",
                "Contention post-orthodontie",
            ],
            "Esthétique dentaire": [
                "Blanchiment dentaire professionnel",
                "Facette céramique (par dent)",
                "Smile design (consultation + plan)",
            ],
        },
    },
}

# ============================================================
# Injection en base de données (idempotente)
# ============================================================

PRICE_BANDS = {
    "Biologie médicale":       (4_000, 28_000),
    "Imagerie médicale":       (15_000, 150_000),
    "Explorations fonctionnelles": (8_000, 45_000),
    "Ambulance médicalisée":   (15_000, 120_000),
    "Soins spécialisés":       (5_000, 45_000),
    "Soins dentaires":         (8_000, 90_000),
}

import hashlib
from decimal import Decimal


def ref_price(pillar_name, acte_name):
    lo, hi = PRICE_BANDS.get(pillar_name, (5_000, 30_000))
    h = int(hashlib.md5(("%s|%s" % (pillar_name, acte_name)).encode()).hexdigest()[:8], 16)
    val = lo + (h % (hi - lo + 1))
    return Decimal((val // 500) * 500)


created_cats = 0
updated_cats = 0
created_acts = 0
skipped_acts = 0

for _key, pillar_data in DEMO_TREE.items():
    pillar_name = pillar_data["pillar_name"]

    # Récupère le pilier (ServiceMedical) — doit déjà exister
    try:
        svc = ServiceMedical.objects.get(name=pillar_name)
    except ServiceMedical.DoesNotExist:
        print("  ERREUR : Pilier introuvable : %s" % pillar_name)
        continue

    for cat_name, actes in pillar_data["categories"].items():
        # Catégorie (niveau 2)
        cat_obj, cat_created = ActeMedical.objects.get_or_create(
            name=cat_name,
            service_medical_category=svc,
            level=2,
            defaults={"parent_service": None, "description": "", "is_active": True},
        )
        if cat_created:
            created_cats += 1
        else:
            updated_cats += 1

        # Actes (niveau 3)
        for acte_name in actes:
            acte_name = acte_name.strip()
            exists = ActeMedical.objects.filter(
                name=acte_name,
                service_medical_category=svc,
                parent_service=cat_obj,
                level=3,
            ).exists()
            if exists:
                skipped_acts += 1
                continue

            # Vérifie si un acte de même nom mais catégorie différente existe
            # (pas grave, on crée quand même avec la bonne parenté)
            price = ref_price(pillar_name, acte_name)
            ActeMedical.objects.create(
                name=acte_name,
                service_medical_category=svc,
                parent_service=cat_obj,
                level=3,
                reference_price=price,
                description="",
                is_active=True,
            )
            created_acts += 1

print("")
print("=== RÉSULTATS ===")
print("Catégories créées  : %d" % created_cats)
print("Catégories existantes : %d" % updated_cats)
print("Actes créés        : %d" % created_acts)
print("Actes déjà présents: %d" % skipped_acts)
print("")
print("Total actes niveau 3 en DB : %d" % ActeMedical.objects.filter(level=3).count())
print("Total catégories niveau 2  : %d" % ActeMedical.objects.filter(level=2).count())
print("")
print("Terminé ! Relancez le serveur si nécessaire.")
