# flake8: noqa: E501
"""
6 piliers Medcare — source : documents/SEGMENTATION_DES_SERVICES (1).pdf

Cartographie modèle :
  - Niveau 1 (pilier) → ServiceMedical
  - Niveau 2 (type de service) → ActeMedical, level=2, parent_service=None
  - Niveau 3 (acte) → ActeMedical, level=3, parent_service = niveau 2
"""

PILLARS_FROM_DOCS = [
    {
        "name": "Biologie médicale",
        "order": 1,
        "icon": "🧬",
        "types": [
            {
                "name": "Hématologie",
                "actes": [
                    "NFS / Hémogramme",
                    "Réticulocytes",
                    "VS (vitesse de sédimentation)",
                    "Frottis sanguin",
                    "Groupe ABO/Rh",
                    "RAI",
                    "Test de Coombs direct",
                    "Test de Coombs indirect",
                    "Électrophorèse de l'hémoglobine",
                    "Vitamine B12",
                    "Folates",
                    "Fer sérique",
                    "Ferritine",
                    "Transferrine / CST",
                ],
            },
            {
                "name": "Hémostase / Coagulation",
                "actes": [
                    "TP / INR",
                    "TCA",
                    "Fibrinogène",
                    "D-Dimères",
                    "Temps de thrombine (TT)",
                    "Activité anti-Xa",
                    "Dosage facteurs VIII, IX",
                ],
            },
            {
                "name": "Biochimie & Ionogramme",
                "actes": [
                    "Glycémie",
                    "HbA1c",
                    "Lactates",
                    "Urée",
                    "Créatinine",
                    "Natrémie",
                    "Kaliémie",
                    "Chlorémie",
                    "Calcémie",
                    "Phosphorémie",
                    "Magnésémie",
                    "ASAT",
                    "ALAT",
                    "GGT",
                    "PAL",
                    "Bilirubine totale",
                    "Bilirubine conjuguée",
                    "Albumine",
                    "Protéine totale",
                    "Électrophorèse des protéines",
                    "Lipase",
                    "Amylase",
                    "CRP",
                    "Procalcitonine",
                    "Cholestérol total",
                    "HDL",
                    "LDL",
                    "Triglycérides",
                    "Apolipoprotéines A",
                    "Apolipoprotéines B",
                ],
            },
            {
                "name": "Immunologie & Auto-immunité",
                "actes": [
                    "ANA (AAN)",
                    "Facteur rhumatoïde (FR)",
                    "Anti-CCP",
                    "C3, C4",
                    "Immunoglobulines IgG/IgA/IgM",
                    "Anti-dsDNA, Anti-Sm, Anti-RNP, Anti-SSA/SSB",
                    "Anticoagulant lupique (LA)",
                    "Anticardiolipines IgG/IgM",
                    "Anti-β2GP1 IgG/IgM",
                    "ANCA (MPO/PR3)",
                    "Panel dermatomyosite (Anti-Jo1, Mi-2, SRP, MDA5, TIF1γ, NXP2, PL7/PL12)",
                ],
            },
            {
                "name": "Sérologie & Virologie",
                "actes": [
                    "VIH Ag/Ac",
                    "Charge virale VIH",
                    "HBsAg",
                    "Anti-HBs",
                    "Anti-HBc total",
                    "Anti-HBc IgM",
                    "HBeAg",
                    "Anti-HBe",
                    "ADN VHB / charge virale HBV",
                    "Anti-VHC",
                    "ARN VHC / charge virale HCV",
                    "Syphilis (VDRL, TPHA)",
                    "Dengue NS1/IgM/IgG",
                    "Chikungunya IgM/IgG",
                    "Rubéole",
                    "Toxoplasmose",
                    "CMV",
                    "EBV",
                ],
            },
            {
                "name": "Bactériologie",
                "actes": [
                    "ECBU + antibiogramme",
                    "Coproculture",
                    "Hémocultures",
                    "ECB prélèvements plaies/pus + culture",
                    "Prélèvement vaginal / cervico-vaginal + culture",
                    "ECBE / examen cytobactériologique des expectorations",
                    "Culture de crachats",
                ],
            },
            {
                "name": "Parasitologie & Mycologie",
                "actes": [
                    "Recherche BK / crachats BAAR",
                    "Goutte épaisse / TDR paludisme",
                    "Examen parasitologique des selles",
                    "Filariose",
                    "Bilharziose (urines/selles)",
                    "Examen mycologique peau/ongles",
                    "Recherche Candida",
                ],
            },
            {
                "name": "Endocrinologie (biologie)",
                "actes": [
                    "TSH, FT4 (± FT3)",
                    "Anti-TPO / Anti-Tg",
                    "Aldostéronémie",
                    "Rénine",
                    "Métanéphrines plasmatiques",
                    "Métanéphrines urinaires",
                    "Cortisol",
                    "Prolactine",
                    "FSH, LH",
                    "Estradiol",
                    "Progestérone",
                    "Testostérone",
                ],
            },
            {
                "name": "Fertilité / AMP",
                "actes": [
                    "AMH",
                    "Spermogramme",
                    "Spermocytogramme",
                    "Test de migration-survie (TMS)",
                    "Spermoculture",
                ],
            },
            {
                "name": "Gaz du sang & Acido-basique",
                "actes": [
                    "Gaz du sang artériel",
                    "Gaz du sang capillaire",
                    "Lactates (gaz du sang)",
                ],
            },
            {
                "name": "Anatomopathologie (histologie)",
                "actes": [
                    "Examen anatomopathologique de pièce opératoire",
                    "Examen anatomopathologique de pièce de biopsie",
                    "Immunohistochimie",
                    "Immunofluorescence",
                ],
            },
            {
                "name": "Cytologie (cytopathologie)",
                "actes": [
                    "Cytologie (ponctions, liquides : pleural, ascite, LCR, urines, etc.)",
                    "Cytologie cervico-vaginale (frottis)",
                    "Cytoponction (thyroïde, ganglion, etc.)",
                ],
            },
            {
                "name": "Biologie moléculaire / PCR",
                "actes": [
                    "PCR Chlamydia / Gonocoque",
                    "PCR HPV",
                    "PCR BK",
                    "GeneXpert MTB/RIF (tuberculose)",
                    "PCR respiratoires",
                ],
            },
            {
                "name": "Toxicologie",
                "actes": [
                    "Drogues urinaires (panel)",
                    "Alcoolémie",
                    "Paracétamol / salicylés",
                    "Carboxyhémoglobine",
                ],
            },
            {
                "name": "Marqueurs tumoraux",
                "actes": [
                    "Métaux lourds",
                    "PSA libre",
                    "CEA",
                    "AFP",
                    "CA 125",
                    "CA 19-9",
                    "CA 15-3",
                    "βHCG",
                ],
            },
        ],
    },
    {
        "name": "Imagerie médicale",
        "order": 2,
        "icon": "🖥",
        "types": [
            {
                "name": "Radiographie",
                "actes": [
                    "Radiographie thorax",
                    "Radiographie abdomen (ASP)",
                    "Radiographie rachis cervical",
                    "Radiographie rachis dorsal",
                    "Radiographie rachis lombaire",
                    "Radiographie membres",
                    "Radiographie bassin",
                    "Radiographie crâne",
                ],
            },
            {
                "name": "Échographie",
                "actes": [
                    "Échographie abdominale",
                    "Échographie pelvienne",
                    "Échographie obstétricale",
                    "Échographie thyroïdienne",
                    "Échographie testiculaire",
                    "Échographie parties molles",
                    "Échographie musculo-squelettique",
                ],
            },
            {
                "name": "Échodoppler",
                "actes": [
                    "Échodoppler veineux MI",
                    "Échodoppler artériel MI",
                    "Échodoppler carotidien",
                    "Échodoppler cardiaque (écho cœur)",
                ],
            },
            {
                "name": "Scanner (TDM)",
                "actes": [
                    "TDM cérébral",
                    "TDM thoracique",
                    "TDM TAP (thoraco-abdomino-pelvien)",
                    "TDM sinus",
                    "Angio-TDM",
                ],
            },
            {
                "name": "IRM",
                "actes": [
                    "IRM cérébrale",
                    "IRM rachis complet",
                    "IRM abdomen / pelvis",
                    "IRM prostate",
                    "IRM cardiaque",
                ],
            },
            {
                "name": "Imagerie interventionnelle",
                "actes": [
                    "Biopsie pulmonaire (scanner-guidée)",
                    "Biopsie hépatique (écho / scanner)",
                    "Biopsie rénale (écho / scanner)",
                    "Biopsie mammaire (stéréotaxie / écho)",
                    "Biopsie thyroïdienne (écho)",
                    "Biopsie ganglionnaire (écho / scanner)",
                    "Biopsie osseuse (scanner-guidée)",
                    "Biopsie ORL",
                    "Ponction pleurale (écho / scanner)",
                    "Ponction péricardique",
                    "Ponction abdominale / ascite",
                    "Ponction articulaire (genou, épaule, hanche)",
                    "Ponction mammaire diagnostique",
                    "Drainage pleural (thoracique)",
                    "Drainage abdominal / rétro-péritonéal",
                    "Drainage biliaire",
                    "Drainage urinaire (néphrostomie)",
                    "Drainage kystique / abcès",
                ],
            },
        ],
    },
    {
        "name": "Explorations fonctionnelles",
        "order": 3,
        "icon": "⚡",
        "types": [
            {
                "name": "Cardiologie",
                "actes": [
                    "ECG",
                    "Épreuve d'effort",
                    "Holter ECG",
                    "Holter tensionnel (MAPA)",
                    "Tilt test",
                    "Test de marche 6 minutes",
                ],
            },
            {
                "name": "Pneumologie",
                "actes": [
                    "EFR / Spirométrie",
                    "Spirométrie avec bronchodilatateur",
                    "Pléthysmographie",
                    "Test de diffusion (DLCO)",
                    "Oxymétrie nocturne",
                    "Polysomnographie",
                    "Polygraphie ventilatoire (apnées du sommeil)",
                ],
            },
            {
                "name": "Gastro-entérologie",
                "actes": [
                    "FOGD",
                    "Coloscopie",
                    "Rectosigmoïdoscopie",
                    "Manométrie œsophagienne",
                    "pH-métrie œsophagienne",
                    "Test respiratoire à l'hydrogène",
                ],
            },
            {
                "name": "Neurologie",
                "actes": [
                    "EEG standard",
                    "EEG de sommeil",
                    "EMG",
                    "Potentiels évoqués visuels (PEV)",
                    "Potentiels évoqués auditifs (PEA)",
                    "Potentiels évoqués somesthésiques (PES)",
                ],
            },
            {
                "name": "ORL",
                "actes": [
                    "Fibroscopie ORL",
                    "Audiométrie tonale",
                    "Audiométrie vocale",
                    "Impédancemétrie",
                    "Tests vestibulaires (VNG, calorique)",
                ],
            },
            {
                "name": "Ophtalmologie",
                "actes": [
                    "Acuité visuelle",
                    "Fond d'œil",
                    "OCT",
                    "Champ visuel",
                    "Pachymétrie",
                    "Topographie cornéenne",
                    "Biométrie oculaire",
                ],
            },
            {
                "name": "Dermatologie",
                "actes": [
                    "Dermoscopie",
                    "Cartographie des nævus",
                    "Tests allergologiques cutanés",
                ],
            },
            {
                "name": "Gynécologie",
                "actes": [
                    "Hystéroscopie diagnostique",
                    "Hystérosalpingographie (HSG)",
                    "Colposcopie",
                    "Monitoring ovulatoire",
                    "Exploration infertilité féminine",
                ],
            },
            {
                "name": "Urologie",
                "actes": [
                    "Débitmétrie urinaire",
                    "Bilan urodynamique",
                    "Cystoscopie diagnostique",
                ],
            },
            {
                "name": "Andrologie / Fertilité",
                "actes": [
                    "Spermogramme",
                    "Spermocytogramme",
                    "Test de migration-survie (TMS)",
                    "Bilan fonctionnel infertilité masculine",
                ],
            },
            {
                "name": "Hématologie (explorations)",
                "actes": [
                    "Myélogramme",
                    "Biopsie ostéo-médullaire",
                    "Test de fragilité osmotique",
                ],
            },
            {
                "name": "Orthopédie",
                "actes": [
                    "Arthroscopie diagnostique",
                ],
            },
        ],
    },
    {
        "name": "Ambulance médicalisée",
        "order": 4,
        "icon": "🚑",
        "types": [
            {
                "name": "Ambulance simple",
                "actes": [
                    "Transport domicile → structure de soins",
                    "Transport structure → domicile",
                    "Transport inter-structures non urgent",
                ],
            },
            {
                "name": "Ambulance médicalisée",
                "actes": [
                    "Transport avec infirmier",
                    "Transport avec médecin",
                ],
            },
            {
                "name": "Équipe SMUR / Réanimation mobile",
                "actes": [
                    "Intervention SMUR pré-hospitalière",
                    "Transport réanimatoire",
                    "Évacuation sanitaire médicalisée urgente",
                ],
            },
            {
                "name": "Transport sanitaire spécialisé",
                "actes": [
                    "Évacuation inter-hospitalière médicalisée",
                    "Rapatriement sanitaire national",
                    "Rapatriement sanitaire international",
                    "Transport médicalisé longue distance",
                ],
            },
            {
                "name": "Couverture médicale & évènementielle",
                "actes": [
                    "Couverture médicale d'évènements sportifs",
                    "Couverture médicale de manifestations publiques",
                    "Couverture médicale de concerts / rassemblements",
                    "Assistance médicale sur site",
                ],
            },
        ],
    },
    {
        "name": "Soins spécialisés",
        "order": 5,
        "icon": "🩺",
        "types": [
            {
                "name": "Médecine générale",
                "actes": [
                    "Suture plaie simple",
                    "Suture plaie complexe",
                    "Incision & drainage abcès cutané",
                    "Nébulisation thérapeutique",
                    "Oxygénothérapie",
                ],
            },
            {
                "name": "Cardiologie",
                "actes": [
                    "ECG à domicile",
                    "Pose / retrait Holter",
                    "Surveillance post-urgence cardiaque",
                ],
            },
            {
                "name": "ORL",
                "actes": [
                    "Lavage d'oreille",
                    "Extraction bouchon de cérumen",
                    "Ablation corps étranger ORL",
                    "Cautérisation épistaxis simple",
                    "Pose / retrait mèche nasale",
                ],
            },
            {
                "name": "Ophtalmologie",
                "actes": [
                    "Retrait corps étranger superficiel",
                    "Lavage oculaire médical",
                    "Laser YAG",
                    "Laser rétinien",
                    "Injection intravitréenne",
                    "Tonométrie thérapeutique",
                ],
            },
            {
                "name": "Dermatologie",
                "actes": [
                    "Cryothérapie",
                    "Exérèse lésion cutanée bénigne",
                    "Électrocoagulation",
                    "Biopsie cutanée",
                    "Pansement dermatologique spécialisé",
                    "Peeling médical",
                    "Laser dermatologique",
                ],
            },
            {
                "name": "Gynécologie",
                "actes": [
                    "Pose DIU",
                    "Retrait DIU",
                    "Pose implant contraceptif",
                    "Retrait implant",
                    "Cryothérapie cervicale",
                    "Aspiration endo-utérine",
                ],
            },
            {
                "name": "Urologie",
                "actes": [
                    "Sondage vésical",
                    "Changement de sonde",
                    "Instillation vésicale",
                ],
            },
            {
                "name": "Soins infirmiers",
                "actes": [
                    "Pansement simple",
                    "Pansement complexe",
                    "Perfusion IV / Injection IM / SC",
                    "Surveillance glycémique",
                    "Soins de plaies chroniques / post-opératoires",
                    "Nursing médicalisé",
                ],
            },
            {
                "name": "Rhumatologie / Orthopédie",
                "actes": [
                    "Infiltration articulaire",
                    "Infiltration péri-articulaire",
                    "Viscosupplémentation",
                    "Injection PRP",
                    "Ponction articulaire évacuatrice",
                    "Immobilisation orthopédique",
                ],
            },
            {
                "name": "Pédiatrie",
                "actes": [
                    "Nébulisation pédiatrique",
                    "Lavage nasal médicalisé",
                    "Soins plaies pédiatriques",
                    "Réhydratation orale supervisée",
                    "Perfusion pédiatrique",
                ],
            },
            {
                "name": "Kinésithérapie / Rééducation",
                "actes": [
                    "Rééducation post-traumatique",
                    "Rééducation post-opératoire",
                    "Rééducation lombalgie / cervicalgie",
                    "Kiné respiratoire adulte",
                    "Kiné respiratoire pédiatrique / nourrisson",
                    "Rééducation post-AVC",
                    "Rééducation périnéale post-partum",
                    "Drainage lymphatique manuel",
                ],
            },
            {
                "name": "Psychologie / Santé mentale",
                "actes": [
                    "Consultation de psychologie",
                    "Suivi psychologique",
                    "Thérapie individuelle",
                    "Thérapie de couple",
                    "Thérapie familiale",
                ],
            },
            {
                "name": "Psychiatrie",
                "actes": [
                    "Consultation psychiatrique initiale",
                    "Consultation psychiatrique de suivi",
                    "Consultation d'urgence psychiatrique",
                    "Ajustement traitement psychotrope",
                ],
            },
            {
                "name": "Neurologie",
                "actes": [
                    "Injection toxine botulique",
                    "Ponction lombaire",
                ],
            },
            {
                "name": "Oncologie / Radiothérapie",
                "actes": [
                    "Consultation d'oncologie médicale",
                    "Administration chimiothérapie ambulatoire",
                    "Radiothérapie externe conformationnelle",
                    "Séance de radiothérapie",
                    "Soins palliatifs ambulatoires",
                ],
            },
            {
                "name": "Néphrologie / Dialyse",
                "actes": [
                    "Hémodialyse chronique (séance)",
                    "Hémodialyse aiguë",
                    "Dialyse péritonéale",
                    "Surveillance fistule artério-veineuse",
                ],
            },
        ],
    },
    {
        "name": "Soins dentaires",
        "order": 6,
        "icon": "🦷",
        "types": [
            {
                "name": "Consultations dentaires",
                "actes": [
                    "Consultation dentaire standard",
                    "Consultation spécialisée",
                    "Consultation d'urgence dentaire",
                    "Bilan bucco-dentaire",
                ],
            },
            {
                "name": "Soins conservateurs & prévention",
                "actes": [
                    "Détartrage",
                    "Polissage",
                    "Traitement des caries",
                    "Obturation composite",
                    "Obturation amalgame",
                ],
            },
            {
                "name": "Endodontie",
                "actes": [
                    "Traitement mono-radiculaire",
                    "Traitement bi-radiculaire",
                    "Traitement multi-radiculaire",
                    "Reprise endodontique",
                ],
            },
            {
                "name": "Chirurgie dentaire & orale",
                "actes": [
                    "Extraction simple",
                    "Extraction chirurgicale",
                    "Dent de sagesse incluse",
                    "Drainage abcès buccal",
                    "Incision drainage abcès buccal",
                    "Biopsie muqueuse buccale",
                ],
            },
            {
                "name": "Prothèses dentaires",
                "actes": [
                    "Couronne céramique",
                    "Couronne zircon",
                    "Bridge (par élément)",
                    "Prothèse amovible partielle",
                    "Prothèse complète",
                ],
            },
            {
                "name": "Implantologie",
                "actes": [
                    "Consultation implantaire",
                    "Pose d'implant",
                    "Greffe osseuse",
                    "Couronne implantaire",
                ],
            },
            {
                "name": "Orthodontie",
                "actes": [
                    "Appareil fixe (bagues)",
                    "Appareil amovible",
                    "Gouttières transparentes",
                    "Contentions",
                ],
            },
            {
                "name": "Dentisterie esthétique",
                "actes": [
                    "Blanchiment dentaire",
                    "Facettes",
                    "Smile design",
                ],
            },
        ],
    },
]
