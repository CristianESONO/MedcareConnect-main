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
    {'re': re.compile(r'hemato|hemostase|coagul|biochim|ionogram|urinaire|vitamine|cardiaque|endocrin|hormon|fertilit|spermio|tumora|immuno|allergo|serolog|virolog|bacterio|parasito|mycolog|moleculaire|pcr|toxico|gaz du sang|cytopath|genetique|biologie|analyses?', re.I), 'pillar': 'bio', 'term': '', 'types': []}
]

DEFAULT_THRESHOLDS = {
    'prop': 0.60,
    'auto': 0.95,
    'margin': 0.10
}
