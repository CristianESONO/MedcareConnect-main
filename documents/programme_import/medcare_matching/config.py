import re

STOP_WORDS = {
    'de', 'du', 'des', 'la', 'le', 'les', 'et', 'au', 'aux', 'en', 'sur', 'sous', 'avec', 'par', 'pour', 'un', 'une'
}

PILLARS = {
    'bio': {
        'id': 'bio',
        'name': 'Biologie médicale',
        'abbrev': {
            'ac': 'anticorps',
            'ag': 'antigene',
            'cv': 'charge virale',
            'bu': 'bandelette urinaire',
            'hb': 'hemoglobine',
            'hiv': 'vih',
            'hcv': 'vhc',
            'hbv': 'vhb',
            'atb': 'antibiogramme',
            'sedim': 'sedimentation',
            'us': 'ultrasensible',
            'nfs': 'nfs hemogramme',
            'fcv': 'frottis cervico vaginal',
            'fcu': 'frottis cervico vaginal',
            'eal': 'bilan lipidique',
            'trigly': 'triglycerides',
        },
        'disc': [
            'igg', 'igm', 'iga', 'ige', 't3', 't4', 'ft3', 'ft4',
            'recherche', 'serologie', 'pcr', 'urinaire', 'urine',
            'plasmatique', 'serique', 'total', 'conjugue', 'libre',
            'direct', 'indirect', '24h', 'quantitatif', 'qualitatif'
        ],
        'generic': ['bilan', 'serologie', 'dosage', 'examen', 'analyse']
    },
    'img': {
        'id': 'img',
        'name': 'Imagerie médicale',
        'abbrev': {
            'echo': 'echographie',
            'radio': 'radiographie',
            'rx': 'radiographie',
            'tdm': 'scanner',
            'pulm': 'thorax pulmonaire',
            'pulmonaire': 'thorax pulmonaire',
            'tap': 'thoraco abdomino pelvien',
            'abdo': 'abdominale',
            'genoux': 'genou bilateral',
            'epaules': 'epaule bilateral',
            'hanches': 'hanche bilateral',
            'mains': 'main bilateral',
            'pieds': 'pied bilateral'
        },
        'disc': [
            'echographie', 'scanner', 'irm', 'radiographie',
            'face', 'profil', 'bilateral', 'droit', 'gauche',
            'injection', 'doppler', 'angio', 'angioscanner',
            'arteriel', 'arterio', 'veineux', 'controle',
            'endovaginal', 'transcranien'
        ],
        'generic': ['echographie', 'scanner', 'irm', 'radiographie', 'examen', 'doppler']
    },
    'exp': {
        'id': 'exp',
        'name': 'Explorations fonctionnelles',
        'abbrev': {
            'ecg': 'electrocardiogramme',
            'eeg': 'electroencephalogramme',
            'emg': 'electromyogramme',
            'efr': 'explorations fonctionnelles respiratoires',
            'fOGD': 'fibroscopie oeso gastro duodenale',
            'fogd': 'fibroscopie oeso gastro duodenale'
        },
        'disc': [
            'ecg', 'eeg', 'emg', 'audiometrie', 'efr', 'holter', 'mapa',
            'fibroscopie', 'endoscopie', 'coloscopie', 'spirometrie',
            'polysomnographie', 'tympanometrie', 'repos', 'effort'
        ],
        'generic': ['exploration', 'bilan', 'test', 'enregistrement', 'mesure']
    },
    'ambu': {
        'id': 'ambu',
        'name': 'Ambulance & Transport sanitaire',
        'abbrev': {
            'vsl': 'vehicule sanitaire leger',
            'vsav': 'vehicule secours assistance victimes',
            'samu': 'transport medicalise urgence',
            'reanim': 'ambulance reanimation'
        },
        'disc': [
            'vsl', 'vsav', 'medicalisee', 'paramedicalisee', 'reanimation',
            'simple', 'urgence', 'transfert', 'rapatriement', 'brancardage',
            'agglo', 'region', 'interurbain', 'aeroport'
        ],
        'generic': ['transport', 'ambulance', 'evacuation', 'trajet']
    },
    'soins': {
        'id': 'soins',
        'name': 'Soins spécialisés',
        'abbrev': {
            'chimio': 'chimiotherapie',
            'kine': 'kinesitherapie'
        },
        'disc': [
            'dialyse', 'hemodialyse', 'chimiotherapie', 'perfusion', 'pansement',
            'injection', 'reeducation', 'kinesitherapie', 'domicile', 'catheter',
            'picc', 'chambre implantable', 'stomatherapie'
        ],
        'generic': ['seance', 'soin', 'acte', 'traitement', 'consultation']
    },
    'dent': {
        'id': 'dent',
        'name': 'Soins dentaires',
        'abbrev': {
            'odf': 'orthodontie',
            'pap': 'prothese amovible partielle',
            'pac': 'prothese amovible complete',
            'ccm': 'couronne ceramo metallique'
        },
        'disc': [
            'detartrage', 'extraction', 'avulsion', 'composite', 'couronne',
            'bridge', 'implant', 'prothese', 'endodontie', 'inlay', 'onlay',
            'sagesse', 'pulpotomie', 'parodontie', 'orthodontie', 'blanchiment',
            'resine', 'stellite', 'monoradiculaire', 'biradiculaire', 'pluriradiculaire'
        ],
        'generic': ['soin', 'consultation', 'chirurgie', 'traitement']
    }
}

MODALITIES = ['echographie', 'scanner', 'irm', 'radiographie']

SECTION_MAP = [
    {'re': re.compile(r'echograph', re.I), 'pillar': 'img', 'term': 'echographie', 'types': ['Échographie', 'Écho-doppler']},
    {'re': re.compile(r'doppler', re.I), 'pillar': 'img', 'term': 'echographie doppler', 'types': ['Écho-doppler']},
    {'re': re.compile(r'scanner|tdm|tomodensito', re.I), 'pillar': 'img', 'term': 'scanner', 'types': ['Scanner']},
    {'re': re.compile(r'\birm\b', re.I), 'pillar': 'img', 'term': 'irm', 'types': ['IRM']},
    {'re': re.compile(r'radiograph|\bradio\b', re.I), 'pillar': 'img', 'term': 'radiographie', 'types': ['Radiographie']},
    {'re': re.compile(r'mammograph', re.I), 'pillar': 'img', 'term': '', 'types': ['Radiologie spéciale']},
    {'re': re.compile(r'examens?\s+speciaux|radiologie\s+speciale', re.I), 'pillar': 'img', 'term': '', 'types': ['Radiologie spéciale', 'Scanner']},
    {'re': re.compile(r'hemato|hemostase|coagul|biochim|ionogram|urinaire|vitamine|cardiaque|endocrin|hormon|fertilit|spermio|tumora|immuno|allergo|serolog|virolog|bacterio|parasito|mycolog|moleculaire|pcr|toxico|gaz du sang|cytopath|genetique|biologie|analyses?', re.I), 'pillar': 'bio', 'term': '', 'types': []},
    {'re': re.compile(r'ecg|eeg|emg|audiometr|holter|mapa|efr|spirometr|endoscop|fibroscop|coloscop|tympanometr|polysomno', re.I), 'pillar': 'exp', 'term': 'exploration', 'types': ['Explorations fonctionnelles']},
    {'re': re.compile(r'ambulance|transport|vsl|vsav|rapatriement|evacuation', re.I), 'pillar': 'ambu', 'term': 'transport', 'types': ['Ambulance & Transport']},
    {'re': re.compile(r'pansement|injection|perfusion|dialyse|chimiotherap|kinesitherap|reeducation|soins? infirmier', re.I), 'pillar': 'soins', 'term': 'soin', 'types': ['Soins spécialisés']},
    {'re': re.compile(r'dent|dentaire|detartrage|extraction|avulsion|orthodont|prothese dentaire|implant dentaire|gingiv|endodont', re.I), 'pillar': 'dent', 'term': 'dentaire', 'types': ['Soins dentaires']}
]

DEFAULT_THRESHOLDS = {
    'prop': 0.60,
    'auto': 0.95,
    'margin': 0.10
}
