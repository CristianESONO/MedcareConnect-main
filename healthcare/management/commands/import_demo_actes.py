from django.core.management.base import BaseCommand
from django.utils.text import slugify
from healthcare.models import ServiceMedical, ActeMedical


class Command(BaseCommand):
    help = 'Importe les actes médicaux depuis le fichier DEMO_DESKTOP_PATIENT.html'

    def handle(self, *args, **options):
        # Données extraites du fichier DEMO_DESKTOP_PATIENT.html
        ACTES_TREE = {
            '1': {
                'label': '🧬 Biologie médicale',
                'cats': {
                    'Hématologie': [
                        'NFS / Hémogramme', 'Réticulocytes', 'VS', 'Frottis sanguin',
                        'Groupe ABO/Rhésus', 'RAI', 'Test de Coombs direct',
                        'Test de Coombs indirect', 'Électrophorèse de l\'hémoglobine',
                        'Vitamine B12', 'Folates (B9)', 'Fer sérique', 'Ferritine',
                        'Transferrine / CST'
                    ],
                    'Hémostase / Coagulation': [
                        'TP / INR', 'TCA', 'Fibrinogène', 'D-Dimères',
                        'Temps de thrombine (TT)', 'Activité anti-Xa',
                        'Dosage facteur VIII', 'Dosage facteur IX'
                    ],
                    'Biochimie & Ionogramme': [
                        'Glycémie à jeun', 'HbA1c', 'Urée sanguine', 'Créatininémie',
                        'Natrémie', 'Kaliémie', 'Chlorémie', 'Calcémie', 'Phosphorémie',
                        'Magnésémie', 'ASAT', 'ALAT', 'GGT', 'PAL',
                        'Bilirubine totale', 'Bilirubine conjuguée', 'Albumine',
                        'Protéines totales', 'Électrophorèse des protéines', 'Lipase',
                        'Amylase', 'CRP', 'Procalcitonine', 'Cholestérol total',
                        'HDL', 'LDL', 'Triglycérides', 'Apolipoprotéines A/B', 'Lactates'
                    ],
                    'Immunologie & Auto-immunité': [
                        'ANA / AAN', 'FR (facteur rhumatoïde)', 'Anti-CCP',
                        'Complément C3', 'Complément C4', 'IgG / IgA / IgM',
                        'Anti-dsDNA', 'Anti-Sm', 'Anti-RNP', 'Anti-SSA / SSB',
                        'Anticoagulant lupique', 'Anticardiolipines IgG/IgM',
                        'Anti-β2GP1', 'ANCA MPO/PR3'
                    ],
                    'Sérologie & Virologie': [
                        'VIH Ag/Ac', 'Charge virale VIH', 'HBsAg', 'Anti-HBs',
                        'Anti-HBc total', 'Anti-HBc IgM', 'HBeAg / Anti-HBe',
                        'ADN VHB (charge virale HBV)', 'Anti-VHC',
                        'ARN VHC (charge virale HCV)', 'Syphilis VDRL',
                        'Syphilis TPHA', 'Dengue NS1/IgM/IgG',
                        'Chikungunya IgM/IgG', 'Toxoplasmose IgG/IgM',
                        'Rubéole IgG/IgM', 'CMV IgG/IgM', 'EBV (Epstein-Barr)'
                    ],
                    'Bactériologie': [
                        'ECBU + antibiogramme', 'Coproculture', 'Hémocultures',
                        'ECB plaies / pus', 'Prélèvement vaginal / cervico-vaginal',
                        'ECBE / expectorations', 'Culture crachats', 'Recherche BK / BAAR'
                    ],
                    'Parasitologie & Mycologie': [
                        'Goutte épaisse / TDR paludisme',
                        'Examen parasitologique des selles', 'Filariose sanguine',
                        'Bilharziose (urines/selles)', 'Examen mycologique peau/ongles',
                        'Recherche Candida'
                    ],
                    'Endocrinologie': [
                        'TSH', 'FT4', 'FT3', 'Anti-TPO', 'Anti-Thyroglobuline',
                        'Aldostéronémie', 'Rénine', 'Cortisol', 'Prolactine', 'FSH',
                        'LH', 'Estradiol', 'Progestérone', 'Testostérone', 'AMH'
                    ],
                    'Fertilité / AMP': [
                        'Spermogramme', 'Spermocytogramme',
                        'Test de migration-survie (TMS)', 'Spermoculture + antibiogramme',
                        'AMH (réserve ovarienne)'
                    ],
                    'Gaz du sang & Acido-basique': [
                        'Gaz du sang artériel', 'Gaz du sang capillaire',
                        'Lactates artériels'
                    ],
                    'Anatomopathologie': [
                        'Examen anapath. pièce opératoire', 'Examen anapath. biopsie',
                        'Immunohistochimie', 'Immunofluorescence directe'
                    ],
                    'Cytologie': [
                        'Cytologie liquide pleural', 'Cytologie ascite', 'Cytologie LCR',
                        'Cytologie urinaire', 'Frottis cervico-vaginal (FCV)',
                        'Cytoponction thyroïde', 'Cytoponction ganglion'
                    ],
                    'Biologie moléculaire / PCR': [
                        'PCR Chlamydia / Gonocoque', 'PCR HPV (génotypage)', 'PCR BK',
                        'GeneXpert MTB/RIF', 'PCR respiratoires multiplex'
                    ],
                    'Toxicologie': [
                        'Drogues urinaires (panel)', 'Alcoolémie',
                        'Paracétamol plasmatique', 'Carboxyhémoglobine', 'Métaux lourds'
                    ],
                    'Marqueurs tumoraux': [
                        'PSA total', 'PSA libre', 'CEA', 'AFP', 'CA 125', 'CA 19-9',
                        'CA 15-3', 'βHCG quantitatif'
                    ],
                }
            },
            '2': {
                'label': '🖥 Imagerie médicale',
                'cats': {
                    'Radiographie': [
                        'Radio thorax', 'Radio abdomen (ASP)', 'Radio rachis cervical',
                        'Radio rachis dorsal', 'Radio rachis lombaire', 'Radio bassin',
                        'Radio membre — genou', 'Radio membre — épaule',
                        'Radio membre — cheville / pied', 'Radio crâne'
                    ],
                    'Échographie': [
                        'Échographie abdominale', 'Échographie pelvienne',
                        'Échographie endovaginale', 'Échographie obstétricale T1',
                        'Échographie morphologique T2', 'Échographie T3 (biométrie)',
                        'Échographie thyroïdienne', 'Échographie testiculaire',
                        'Échographie parties molles', 'Mammographie'
                    ],
                    'Échodoppler': [
                        'Échodoppler veineux membres inférieurs',
                        'Échodoppler artériel membres inférieurs',
                        'Échodoppler carotidien + vertébral',
                        'Écho-cœur (échocardiographie transthoracique)'
                    ],
                    'Scanner (TDM)': [
                        'Scanner cérébral sans injection',
                        'Scanner cérébral avec injection', 'Scanner thoracique',
                        'Scanner TAP (thoraco-abdomino-pelvien)', 'Scanner sinus',
                        'Angio-TDM cérébral'
                    ],
                    'IRM': [
                        'IRM cérébrale sans injection', 'IRM cérébrale avec injection',
                        'IRM rachis cervical', 'IRM rachis lombaire',
                        'IRM abdomen / pelvis', 'IRM prostate', 'IRM cardiaque'
                    ],
                    'Biopsies guidées': [
                        'Biopsie hépatique (écho-guidée)',
                        'Biopsie mammaire (écho-guidée)',
                        'Biopsie rénale (écho-guidée)',
                        'Biopsie pulmonaire (scanner-guidée)',
                        'Biopsie thyroïdienne (écho-guidée)', 'Biopsie ganglionnaire',
                        'Biopsie osseuse (scanner-guidée)'
                    ],
                    'Ponctions guidées': [
                        'Ponction pleurale (écho-guidée)', 'Ponction abdominale / ascite',
                        'Ponction articulaire genou',
                        'Ponction articulaire épaule / hanche',
                        'Ponction mammaire diagnostique'
                    ],
                    'Drainages guidés': [
                        'Drainage pleural (thoracique)', 'Drainage abdominal / abcès',
                        'Drainage biliaire', 'Néphrostomie (drainage urinaire)'
                    ],
                }
            },
            '3': {
                'label': '⚡ Explorations fonctionnelles',
                'cats': {
                    'Cardiologie': [
                        'ECG standard 12 dérivations',
                        'Épreuve d\'effort (test effort cardiaque)', 'Holter ECG 24h',
                        'Holter tensionnel MAPA 24h', 'Tilt test (table basculante)',
                        'Test de marche 6 minutes'
                    ],
                    'Pneumologie': [
                        'EFR / Spirométrie standard', 'Spirométrie + bronchodilatateur',
                        'Pléthysmographie corps entier', 'Test de diffusion DLCO',
                        'Oxymétrie nocturne',
                        'Polygraphie ventilatoire (apnées du sommeil)'
                    ],
                    'Gastro-entérologie': [
                        'FOGD (fibroscopie gastrique)', 'Coloscopie',
                        'Rectosigmoïdoscopie', 'Manométrie œsophagienne',
                        'pH-métrie œsophagienne', 'Test respiratoire à l\'hydrogène'
                    ],
                    'Neurologie': [
                        'EEG standard', 'EEG de sommeil',
                        'EMG (électromyogramme)',
                        'Potentiels évoqués visuels (PEV)',
                        'Potentiels évoqués auditifs (PEA)',
                        'Potentiels évoqués somesthésiques (PES)'
                    ],
                    'ORL': [
                        'Audiométrie tonale', 'Audiométrie vocale',
                        'Impédancemétrie (tympanométrie)',
                        'Tests vestibulaires VNG', 'Fibroscopie ORL'
                    ],
                    'Ophtalmologie': [
                        'Acuité visuelle + réfraction', 'Fond d\'œil',
                        'OCT (tomographie optique cohérente)',
                        'Champ visuel automatisé', 'Pachymétrie cornéenne',
                        'Topographie cornéenne', 'Biométrie oculaire'
                    ],
                    'Dermatologie': [
                        'Dermoscopie', 'Cartographie des nævus',
                        'Tests allergologiques cutanés'
                    ],
                    'Gynécologie': [
                        'Hystérosalpingographie (HSG)',
                        'Hystéroscopie diagnostique', 'Colposcopie',
                        'Monitoring ovulatoire'
                    ],
                    'Urologie': [
                        'Débitmétrie urinaire', 'Bilan urodynamique complet'
                    ],
                    'Andrologie / Fertilité': [
                        'Spermogramme (exploration fonctionnelle)',
                        'Spermocytogramme', 'Test de migration-survie',
                        'Bilan infertilité masculine'
                    ],
                    'Hématologie clinique': [
                        'Myélogramme', 'Biopsie ostéo-médullaire',
                        'Test de fragilité osmotique'
                    ],
                }
            },
            '4': {
                'label': '🚑 Ambulance médicalisée',
                'cats': {
                    'Transport sanitaire': [
                        'Ambulance simple', 'Ambulance médicalisée avec infirmier',
                        'Ambulance médicalisée avec médecin',
                        'Transport réanimatoire', 'Évacuation sanitaire'
                    ],
                    'Rapatriement': [
                        'Rapatriement national', 'Rapatriement international'
                    ],
                    'Couverture & assistance': [
                        'Couverture médicale sportive',
                        'Couverture médicale de manifestation publique',
                        'Assistance médicale sur site'
                    ],
                }
            },
            '5': {
                'label': '🩺 Soins spécialisés',
                'cats': {
                    'Médecine générale': [
                        'Suture plaie simple', 'Suture plaie complexe',
                        'Incision & drainage abcès cutané', 'Nébulisation thérapeutique',
                        'Oxygénothérapie'
                    ],
                    'Cardiologie': [
                        'ECG à domicile', 'Pose / retrait Holter ECG',
                        'Surveillance post-urgence cardiaque'
                    ],
                    'ORL': [
                        'Lavage d\'oreille', 'Extraction bouchon de cérumen',
                        'Ablation corps étranger ORL', 'Cautérisation épistaxis',
                        'Pose / retrait mèche nasale'
                    ],
                    'Ophtalmologie': [
                        'Retrait corps étranger oculaire', 'Lavage oculaire médical',
                        'Laser YAG', 'Laser rétinien', 'Injection intravitréenne'
                    ],
                    'Dermatologie': [
                        'Cryothérapie cutanée', 'Exérèse lésion cutanée bénigne',
                        'Électrocoagulation', 'Biopsie cutanée', 'Peeling médical',
                        'Laser dermatologique'
                    ],
                    'Gynécologie': [
                        'Pose DIU (stérilet)', 'Retrait DIU', 'Pose implant contraceptif',
                        'Retrait implant', 'Biopsie gynécologique',
                        'Cryothérapie cervicale', 'Aspiration endo-utérine'
                    ],
                    'Urologie': [
                        'Sondage vésical', 'Changement de sonde', 'Instillation vésicale'
                    ],
                    'Soins infirmiers': [
                        'Pansement simple', 'Pansement complexe', 'Perfusion IV',
                        'Injection IM / SC', 'Surveillance glycémique',
                        'Soins de plaies chroniques', 'Nursing médicalisé'
                    ],
                    'Rhumatologie / Orthopédie': [
                        'Infiltration articulaire genou',
                        'Infiltration articulaire épaule', 'Viscosupplémentation',
                        'Injection PRP', 'Ponction articulaire évacuatrice',
                        'Immobilisation orthopédique'
                    ],
                    'Pédiatrie': [
                        'Nébulisation pédiatrique', 'Lavage nasal médicalisé',
                        'Soins plaies pédiatriques', 'Réhydratation orale supervisée',
                        'Perfusion pédiatrique'
                    ],
                    'Kinésithérapie': [
                        'Rééducation post-traumatique',
                        'Rééducation post-opératoire genou',
                        'Rééducation lombalgie / cervicalgie', 'Kiné respiratoire adulte',
                        'Kiné respiratoire pédiatrique', 'Rééducation post-AVC',
                        'Rééducation périnéale post-partum',
                        'Drainage lymphatique manuel', 'Kinésithérapie à domicile'
                    ],
                    'Dialyse / Néphrologie': [
                        'Hémodialyse chronique', 'Hémodialyse aiguë',
                        'Dialyse péritonéale', 'Soins cathéter de dialyse'
                    ],
                    'Psychologie': [
                        'Consultation de psychologie initiale',
                        'Séance de psychologie de suivi', 'Thérapie individuelle',
                        'Thérapie de couple', 'Thérapie familiale',
                        'Téléconsultation psychologique'
                    ],
                    'Psychiatrie': [
                        'Consultation psychiatrique initiale',
                        'Consultation psychiatrique de suivi',
                        'Évaluation psychiatrique diagnostique',
                        'Ajustement traitement psychotrope',
                        'Téléconsultation psychiatrique'
                    ],
                    'Oncologie / Radiothérapie': [
                        'Consultation d\'oncologie médicale',
                        'Administration chimiothérapie ambulatoire',
                        'Séance de radiothérapie', 'Soins palliatifs ambulatoires'
                    ],
                }
            },
            '6': {
                'label': '🦷 Soins dentaires',
                'cats': {
                    'Consultations dentaires': [
                        'Consultation dentaire standard',
                        'Consultation dentaire spécialisée',
                        'Consultation d\'urgence dentaire',
                        'Bilan bucco-dentaire complet'
                    ],
                    'Soins conservateurs': [
                        'Détartrage complet', 'Détartrage + polissage + fluoration',
                        'Traitement carie (composite)', 'Obturation amalgame'
                    ],
                    'Endodontie': [
                        'Traitement endodontique mono-radiculaire',
                        'Traitement endodontique bi-radiculaire',
                        'Traitement endodontique multi-radiculaire',
                        'Reprise endodontique'
                    ],
                    'Chirurgie dentaire': [
                        'Extraction simple', 'Extraction chirurgicale',
                        'Extraction dent de sagesse incluse', 'Drainage abcès dentaire'
                    ],
                    'Prothèses': [
                        'Couronne céramique / zirconium', 'Bridge 3 éléments',
                        'Prothèse amovible partielle', 'Prothèse complète'
                    ],
                    'Implantologie': [
                        'Consultation implantaire', 'Pose d\'implant dentaire',
                        'Greffe osseuse', 'Couronne sur implant'
                    ],
                    'Orthodontie': [
                        'Appareil orthodontique fixe (arcade)',
                        'Appareil amovible', 'Gouttières transparentes (aligneurs)',
                        'Contention post-orthodontie'
                    ],
                    'Esthétique dentaire': [
                        'Blanchiment dentaire professionnel',
                        'Facette céramique (par dent)',
                        'Smile design (consultation + plan)'
                    ],
                }
            },
        }

        created_count = 0
        updated_count = 0

        for pilier_key, pilier_data in ACTES_TREE.items():
            # Créer ou mettre à jour le ServiceMedical (pilier)
            pilier_slug = slugify(pilier_data['label'])
            try:
                service = ServiceMedical.objects.get(slug=pilier_slug)
                # Mettre à jour si existe
                service.name = pilier_data['label']
                service.icon = pilier_data['label'].split(' ')[0]
                service.order = int(pilier_key)
                service.is_active = True
                service.save()
                updated_count += 1
            except ServiceMedical.DoesNotExist:
                # Créer nouveau
                service = ServiceMedical.objects.create(
                    name=pilier_data['label'],
                    icon=pilier_data['label'].split(' ')[0],
                    order=int(pilier_key),
                    is_active=True
                )
                created_count += 1

            # Pour chaque catégorie du pilier
            for cat_name, actes_list in pilier_data['cats'].items():
                # Créer ou mettre à jour la catégorie comme ServiceMedical de niveau 2
                cat_slug = slugify(cat_name)
                try:
                    cat_service = ServiceMedical.objects.get(slug=cat_slug)
                    cat_service.icon = '📋'
                    cat_service.order = int(pilier_key) * 100  # Ordre après le pilier
                    cat_service.is_active = True
                    cat_service.save()
                    updated_count += 1
                except ServiceMedical.DoesNotExist:
                    cat_service = ServiceMedical.objects.create(
                        name=cat_name,
                        icon='📋',
                        order=int(pilier_key) * 100,
                        is_active=True
                    )
                    created_count += 1

                # Pour chaque acte de la catégorie
                for acte_name in actes_list:
                    # Créer ou mettre à jour l'ActeMedical
                    acte = ActeMedical.objects.filter(name=acte_name).first()
                    if acte:
                        acte.service_medical_category = service
                        acte.level = 3
                        acte.is_active = True
                        acte.save()
                        updated_count += 1
                    else:
                        acte = ActeMedical.objects.create(
                            name=acte_name,
                            service_medical_category=service,
                            level=3,
                            is_active=True
                        )
                        created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Succès: {created_count} actes créés, {updated_count} mis à jour'
            )
        )
