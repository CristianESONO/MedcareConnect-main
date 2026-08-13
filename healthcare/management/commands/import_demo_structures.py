from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from healthcare.models import (
    OrganismeDeSante, TypeOrganisme, ActeMedical, PrestataireActe,
    Assurance, PriseEnChargeAssurance, SubscriptionPlan
)
from healthcare.data.catalog_assurances import ASSURANCES_FROM_DOCS

User = get_user_model()


class Command(BaseCommand):
    help = 'Importe les structures depuis le fichier DEMO_DESKTOP_PATIENT.html'

    def handle(self, *args, **options):
        # Données extraites du fichier DEMO_DESKTOP_PATIENT.html
        STRUCTURES = [
            {
                'id': 1,
                'name': 'Laboratoire BioSanté Mermoz',
                'desc': 'Laboratoire d\'analyses médicales de référence à Mermoz, biologie courante et spécialisée, avec prélèvement à domicile.',
                'type': 'Laboratoire d\'analyses médicales',
                'zone': 'Mermoz',
                'horaires': 'Lun–Sam 07h–19h · Dim 08h–13h',
                'assurances': ['CMU', 'IPM', 'CNAM', 'AXA Assurances Sénégal', 'Allianz / SanlamAllianz', 'Privé (paiement direct)'],
                'pioneer': True,
                'actes': {
                    'NFS / Hémogramme': {'prix': 8500, 'delai': '2h'},
                    'Réticulocytes': {'prix': 6000, 'delai': '4h'},
                    'VS': {'prix': 3500, 'delai': '2h'},
                    'Frottis sanguin': {'prix': 5000, 'delai': '24h'},
                    'Groupe ABO/Rhésus': {'prix': 5000, 'delai': '1h'},
                    'RAI': {'prix': 12000, 'delai': '24h'},
                    'Test de Coombs direct': {'prix': 9000, 'delai': '24h'},
                    'Électrophorèse de l\'hémoglobine': {'prix': 18000, 'delai': '48h'},
                    'Vitamine B12': {'prix': 14000, 'delai': '24h'},
                    'Folates (B9)': {'prix': 12000, 'delai': '24h'},
                    'Fer sérique': {'prix': 6000, 'delai': '4h'},
                    'Ferritine': {'prix': 9000, 'delai': '24h'},
                    'Transferrine / CST': {'prix': 10000, 'delai': '24h'},
                    'TP / INR': {'prix': 7500, 'delai': '2h'},
                    'TCA': {'prix': 7500, 'delai': '2h'},
                    'Fibrinogène': {'prix': 9000, 'delai': '2h'},
                    'D-Dimères': {'prix': 18000, 'delai': '4h'},
                    'Temps de thrombine (TT)': {'prix': 8000, 'delai': '4h'},
                    'Glycémie à jeun': {'prix': 3500, 'delai': '1h'},
                    'HbA1c': {'prix': 9000, 'delai': '24h'},
                    'Urée sanguine': {'prix': 4500, 'delai': '2h'},
                    'Créatininémie': {'prix': 4500, 'delai': '2h'},
                    'Natrémie': {'prix': 3500, 'delai': '2h'},
                    'Kaliémie': {'prix': 3500, 'delai': '2h'},
                    'Chlorémie': {'prix': 3500, 'delai': '2h'},
                    'Calcémie': {'prix': 4000, 'delai': '2h'},
                    'ASAT': {'prix': 4500, 'delai': '4h'},
                    'ALAT': {'prix': 4500, 'delai': '4h'},
                    'GGT': {'prix': 4500, 'delai': '4h'},
                    'Bilirubine totale': {'prix': 4000, 'delai': '4h'},
                    'Bilirubine conjuguée': {'prix': 4000, 'delai': '4h'},
                    'Albumine': {'prix': 4000, 'delai': '4h'},
                    'CRP': {'prix': 5500, 'delai': '2h'},
                    'Procalcitonine': {'prix': 22000, 'delai': '4h'},
                    'Cholestérol total': {'prix': 4500, 'delai': '24h'},
                    'HDL': {'prix': 5000, 'delai': '24h'},
                    'LDL': {'prix': 5000, 'delai': '24h'},
                    'Triglycérides': {'prix': 5000, 'delai': '24h'},
                    'VIH Ag/Ac': {'prix': 10000, 'delai': '2h'},
                    'HBsAg': {'prix': 8000, 'delai': '2h'},
                    'Anti-HBs': {'prix': 8000, 'delai': '24h'},
                    'Anti-HBc total': {'prix': 9000, 'delai': '24h'},
                    'Anti-VHC': {'prix': 9000, 'delai': '24h'},
                    'Syphilis VDRL': {'prix': 5000, 'delai': '24h'},
                    'Syphilis TPHA': {'prix': 5000, 'delai': '24h'},
                    'Toxoplasmose IgG/IgM': {'prix': 12000, 'delai': '24h'},
                    'Rubéole IgG/IgM': {'prix': 12000, 'delai': '24h'},
                    'ECBU + antibiogramme': {'prix': 11000, 'delai': '48h'},
                    'Coproculture': {'prix': 12000, 'delai': '48h'},
                    'Hémocultures': {'prix': 20000, 'delai': '72h'},
                    'Prélèvement vaginal / cervico-vaginal': {'prix': 14000, 'delai': '48h'},
                    'Recherche BK / BAAR': {'prix': 12000, 'delai': '72h'},
                    'TSH': {'prix': 12000, 'delai': '24h'},
                    'FT4': {'prix': 10000, 'delai': '24h'},
                    'Cortisol': {'prix': 18000, 'delai': '24h'},
                    'PSA total': {'prix': 12000, 'delai': '24h'},
                    'PSA libre': {'prix': 9000, 'delai': '24h'},
                    'CEA': {'prix': 12000, 'delai': '48h'},
                    'AFP': {'prix': 12000, 'delai': '48h'},
                    'CA 125': {'prix': 15000, 'delai': '48h'},
                    'CA 19-9': {'prix': 15000, 'delai': '48h'},
                    'βHCG quantitatif': {'prix': 12000, 'delai': '24h'},
                    'Goutte épaisse / TDR paludisme': {'prix': 6000, 'delai': '1h'},
                    'Examen parasitologique des selles': {'prix': 7500, 'delai': '48h'},
                }
            },
            {
                'id': 2,
                'name': 'Labo Spécialisé Point E',
                'desc': 'Laboratoire spécialisé au Point E, expert en analyses de haute précision et bilans complexes.',
                'type': 'Laboratoire — Fertilité, Immunologie & PCR',
                'zone': 'Point E',
                'horaires': 'Lun–Ven 07h30–18h · Sam 08h–14h',
                'assurances': ['CMU', 'CNAM', 'IPRES', 'SONAM SA / SONAM Mutuelle', 'Privé (paiement direct)'],
                'pioneer': True,
                'actes': {
                    'ANA / AAN': {'prix': 18000, 'delai': '48h'},
                    'FR (facteur rhumatoïde)': {'prix': 8000, 'delai': '24h'},
                    'Anti-CCP': {'prix': 22000, 'delai': '48h'},
                    'Complément C3': {'prix': 9000, 'delai': '48h'},
                    'Complément C4': {'prix': 9000, 'delai': '48h'},
                    'IgG / IgA / IgM': {'prix': 18000, 'delai': '48h'},
                    'Anti-dsDNA': {'prix': 18000, 'delai': '72h'},
                    'Anti-Sm': {'prix': 15000, 'delai': '72h'},
                    'Anti-RNP': {'prix': 15000, 'delai': '72h'},
                    'Anti-SSA / SSB': {'prix': 18000, 'delai': '72h'},
                    'Anticoagulant lupique': {'prix': 25000, 'delai': '48h'},
                    'Anticardiolipines IgG/IgM': {'prix': 22000, 'delai': '48h'},
                    'ANCA MPO/PR3': {'prix': 38000, 'delai': '72h'},
                    'Charge virale VIH': {'prix': 55000, 'delai': '72h'},
                    'ADN VHB (charge virale HBV)': {'prix': 50000, 'delai': '72h'},
                    'ARN VHC (charge virale HCV)': {'prix': 50000, 'delai': '72h'},
                    'Dengue NS1/IgM/IgG': {'prix': 18000, 'delai': '24h'},
                    'Chikungunya IgM/IgG': {'prix': 18000, 'delai': '48h'},
                    'CMV IgG/IgM': {'prix': 14000, 'delai': '48h'},
                    'EBV (Epstein-Barr)': {'prix': 15000, 'delai': '48h'},
                    'Spermogramme': {'prix': 18000, 'delai': '24h'},
                    'Spermocytogramme': {'prix': 12000, 'delai': '24h'},
                    'Test de migration-survie (TMS)': {'prix': 20000, 'delai': '24h'},
                    'Spermoculture + antibiogramme': {'prix': 18000, 'delai': '48h'},
                    'AMH (réserve ovarienne)': {'prix': 28000, 'delai': '48h'},
                    'FSH': {'prix': 8000, 'delai': '24h'},
                    'LH': {'prix': 8000, 'delai': '24h'},
                    'Estradiol': {'prix': 8000, 'delai': '24h'},
                    'Progestérone': {'prix': 8000, 'delai': '24h'},
                    'Prolactine': {'prix': 10000, 'delai': '24h'},
                    'Testostérone': {'prix': 12000, 'delai': '24h'},
                    'PCR Chlamydia / Gonocoque': {'prix': 30000, 'delai': '48h'},
                    'PCR HPV (génotypage)': {'prix': 35000, 'delai': '48h'},
                    'PCR BK': {'prix': 35000, 'delai': '48h'},
                    'GeneXpert MTB/RIF': {'prix': 40000, 'delai': '48h'},
                    'PCR respiratoires multiplex': {'prix': 45000, 'delai': '48h'},
                    'Goutte épaisse / TDR paludisme': {'prix': 6000, 'delai': '1h'},
                    'Examen parasitologique des selles': {'prix': 7000, 'delai': '48h'},
                    'Filariose sanguine': {'prix': 9000, 'delai': '24h'},
                    'Bilharziose (urines/selles)': {'prix': 9000, 'delai': '48h'},
                    'Examen mycologique peau/ongles': {'prix': 12000, 'delai': '72h'},
                    'Drogues urinaires (panel)': {'prix': 20000, 'delai': '4h'},
                    'Alcoolémie': {'prix': 12000, 'delai': '2h'},
                    'Métaux lourds': {'prix': 45000, 'delai': '72h'},
                    'Activité anti-Xa': {'prix': 22000, 'delai': '4h'},
                    'Gaz du sang artériel': {'prix': 20000, 'delai': '1h'},
                }
            },
            {
                'id': 3,
                'name': 'Labo Anatomopathologie Plateau',
                'type': 'Laboratoire spécialisé — Anapath & Cytologie',
                'zone': 'Plateau',
                'horaires': 'Lun–Ven 08h–17h',
                'assurances': ['IPM', 'AXA Assurances Sénégal', 'Allianz / SanlamAllianz', 'IPRES', 'FNR', 'Privé (paiement direct)'],
                'pioneer': False,
                'actes': {
                    'Examen anapath. pièce opératoire': {'prix': 45000, 'delai': '7 jours'},
                    'Examen anapath. biopsie': {'prix': 35000, 'delai': '5 jours'},
                    'Immunohistochimie': {'prix': 30000, 'delai': '5 jours'},
                    'Immunofluorescence directe': {'prix': 40000, 'delai': '7 jours'},
                    'Cytologie liquide pleural': {'prix': 25000, 'delai': '48h'},
                    'Cytologie ascite': {'prix': 25000, 'delai': '48h'},
                    'Cytologie LCR': {'prix': 28000, 'delai': '48h'},
                    'Cytologie urinaire': {'prix': 20000, 'delai': '48h'},
                    'Frottis cervico-vaginal (FCV)': {'prix': 18000, 'delai': '5 jours'},
                    'Cytoponction thyroïde': {'prix': 45000, 'delai': '5 jours'},
                    'Cytoponction ganglion': {'prix': 40000, 'delai': '5 jours'},
                    'PSA total': {'prix': 13000, 'delai': '24h'},
                    'CA 125': {'prix': 16000, 'delai': '48h'},
                    'CA 19-9': {'prix': 16000, 'delai': '48h'},
                    'CEA': {'prix': 13000, 'delai': '48h'},
                }
            },
            {
                'id': 4,
                'name': 'Centre Imagerie Sacré-Cœur',
                'desc': 'Centre d\'imagerie médicale au Sacré-Cœur : radiologie, échographie, scanner et IRM, avec comptes rendus rapides.',
                'type': 'Imagerie — Écho · Radio · Scanner · IRM',
                'zone': 'Sacré-Cœur',
                'horaires': 'Lun–Sam 07h–20h · Urgences 24h/24',
                'assurances': ['CMU', 'IPM', 'CNAM', 'AXA Assurances Sénégal', 'Allianz / SanlamAllianz', 'Tanel Health (Afiyah)', 'Privé (paiement direct)'],
                'pioneer': True,
                'actes': {
                    'Radio thorax': {'prix': 12000, 'delai': '30min'},
                    'Radio abdomen (ASP)': {'prix': 12000, 'delai': '30min'},
                    'Radio rachis cervical': {'prix': 14000, 'delai': '30min'},
                    'Radio rachis dorsal': {'prix': 14000, 'delai': '30min'},
                    'Radio rachis lombaire': {'prix': 16000, 'delai': '30min'},
                    'Radio bassin': {'prix': 12000, 'delai': '30min'},
                    'Radio membre — genou': {'prix': 14000, 'delai': '30min'},
                    'Radio membre — épaule': {'prix': 14000, 'delai': '30min'},
                    'Radio membre — cheville / pied': {'prix': 14000, 'delai': '30min'},
                    'Radio crâne': {'prix': 12000, 'delai': '30min'},
                    'Échographie abdominale': {'prix': 25000, 'delai': '1h'},
                    'Échographie pelvienne': {'prix': 22000, 'delai': '1h'},
                    'Échographie endovaginale': {'prix': 25000, 'delai': '1h'},
                    'Échographie obstétricale T1': {'prix': 25000, 'delai': '1h'},
                    'Échographie morphologique T2': {'prix': 35000, 'delai': '1h'},
                    'Échographie T3 (biométrie)': {'prix': 30000, 'delai': '1h'},
                    'Échographie thyroïdienne': {'prix': 20000, 'delai': '1h'},
                    'Échographie testiculaire': {'prix': 22000, 'delai': '1h'},
                    'Mammographie': {'prix': 35000, 'delai': '1h'},
                    'Échodoppler veineux membres inférieurs': {'prix': 35000, 'delai': '1h'},
                    'Échodoppler artériel membres inférieurs': {'prix': 35000, 'delai': '1h'},
                    'Échodoppler carotidien + vertébral': {'prix': 38000, 'delai': '1h'},
                    'Écho-cœur (échocardiographie transthoracique)': {'prix': 50000, 'delai': '1h'},
                    'Scanner cérébral sans injection': {'prix': 80000, 'delai': '2h'},
                    'Scanner cérébral avec injection': {'prix': 95000, 'delai': '2h'},
                    'Scanner thoracique': {'prix': 120000, 'delai': '2h'},
                    'Scanner TAP (thoraco-abdomino-pelvien)': {'prix': 150000, 'delai': '2h'},
                    'Scanner sinus': {'prix': 80000, 'delai': '2h'},
                    'Angio-TDM cérébral': {'prix': 160000, 'delai': '2h'},
                    'IRM cérébrale sans injection': {'prix': 185000, 'delai': '48h'},
                    'IRM cérébrale avec injection': {'prix': 215000, 'delai': '48h'},
                    'IRM rachis cervical': {'prix': 180000, 'delai': '48h'},
                    'IRM rachis lombaire': {'prix': 180000, 'delai': '48h'},
                    'IRM abdomen / pelvis': {'prix': 220000, 'delai': '48h'},
                }
            },
            {
                'id': 5,
                'name': 'Imagerie Interventionnelle Mermoz',
                'desc': 'Plateau d\'imagerie interventionnelle à Mermoz pour actes diagnostiques et thérapeutiques guidés par l\'image.',
                'type': 'Centre d\'imagerie interventionnelle',
                'zone': 'Mermoz',
                'horaires': 'Lun–Ven 08h–18h · Sam 08h–13h',
                'assurances': ['IPM', 'AXA Assurances Sénégal', 'Allianz / SanlamAllianz', 'IPRES', 'FNR', 'Privé (paiement direct)'],
                'pioneer': True,
                'actes': {
                    'Biopsie hépatique (écho-guidée)': {'prix': 120000, 'delai': 'Sur RDV'},
                    'Biopsie mammaire (écho-guidée)': {'prix': 95000, 'delai': 'Sur RDV'},
                    'Biopsie rénale (écho-guidée)': {'prix': 110000, 'delai': 'Sur RDV'},
                    'Biopsie pulmonaire (scanner-guidée)': {'prix': 140000, 'delai': 'Sur RDV'},
                    'Biopsie thyroïdienne (écho-guidée)': {'prix': 80000, 'delai': 'Sur RDV'},
                    'Biopsie ganglionnaire': {'prix': 90000, 'delai': 'Sur RDV'},
                    'Biopsie osseuse (scanner-guidée)': {'prix': 130000, 'delai': 'Sur RDV'},
                    'Ponction pleurale (écho-guidée)': {'prix': 80000, 'delai': 'Sur RDV'},
                    'Ponction abdominale / ascite': {'prix': 75000, 'delai': 'Sur RDV'},
                    'Ponction articulaire genou': {'prix': 65000, 'delai': 'Sur RDV'},
                    'Ponction articulaire épaule / hanche': {'prix': 65000, 'delai': 'Sur RDV'},
                    'Ponction mammaire diagnostique': {'prix': 70000, 'delai': 'Sur RDV'},
                    'Drainage pleural (thoracique)': {'prix': 120000, 'delai': 'Sur RDV'},
                    'Drainage abdominal / abcès': {'prix': 100000, 'delai': 'Sur RDV'},
                    'Drainage biliaire': {'prix': 150000, 'delai': 'Sur RDV'},
                    'Néphrostomie (drainage urinaire)': {'prix': 160000, 'delai': 'Sur RDV'},
                    'Mammographie': {'prix': 38000, 'delai': '1h'},
                    'Échodoppler veineux membres inférieurs': {'prix': 38000, 'delai': '1h'},
                }
            },
            {
                'id': 6,
                'name': 'Centre Cardio-Pneumo Fann',
                'desc': 'Centre d\'explorations cardio-pneumologiques à Fann : ECG, épreuves d\'effort et explorations fonctionnelles respiratoires.',
                'type': 'Explorations fonctionnelles — Cardiologie & Pneumologie',
                'zone': 'Fann Résidence',
                'horaires': 'Lun–Sam 08h–18h',
                'assurances': ['CMU', 'IPM', 'CNAM', 'AXA Assurances Sénégal', 'Allianz / SanlamAllianz', 'IPRES', 'Privé (paiement direct)'],
                'pioneer': True,
                'actes': {
                    'ECG standard 12 dérivations': {'prix': 10000, 'delai': '30min'},
                    'Épreuve d\'effort (test effort cardiaque)': {'prix': 75000, 'delai': 'Sur RDV'},
                    'Holter ECG 24h': {'prix': 55000, 'delai': '48h'},
                    'Holter tensionnel MAPA 24h': {'prix': 45000, 'delai': '48h'},
                    'Tilt test (table basculante)': {'prix': 60000, 'delai': 'Sur RDV'},
                    'Test de marche 6 minutes': {'prix': 20000, 'delai': '1h'},
                    'Écho-cœur (échocardiographie transthoracique)': {'prix': 48000, 'delai': '1h'},
                    'EFR / Spirométrie standard': {'prix': 25000, 'delai': '1h'},
                    'Spirométrie + bronchodilatateur': {'prix': 35000, 'delai': '1h'},
                    'Pléthysmographie corps entier': {'prix': 45000, 'delai': 'Sur RDV'},
                    'Test de diffusion DLCO': {'prix': 40000, 'delai': 'Sur RDV'},
                    'Oxymétrie nocturne': {'prix': 35000, 'delai': '48h'},
                    'Polygraphie ventilatoire (apnées du sommeil)': {'prix': 80000, 'delai': '48h'},
                }
            },
            {
                'id': 7,
                'name': 'Centre Neuro-ORL Plateau',
                'type': 'Explorations fonctionnelles — Neurologie, ORL, Ophtalmo',
                'zone': 'Plateau',
                'horaires': 'Lun–Ven 08h–17h30',
                'assurances': ['IPM', 'AXA Assurances Sénégal', 'Allianz / SanlamAllianz', 'Privé (paiement direct)'],
                'pioneer': False,
                'actes': {
                    'EEG standard': {'prix': 45000, 'delai': '48h'},
                    'EEG de sommeil': {'prix': 60000, 'delai': 'Sur RDV'},
                    'EMG (électromyogramme)': {'prix': 60000, 'delai': 'Sur RDV'},
                    'Potentiels évoqués visuels (PEV)': {'prix': 50000, 'delai': 'Sur RDV'},
                    'Potentiels évoqués auditifs (PEA)': {'prix': 50000, 'delai': 'Sur RDV'},
                    'Potentiels évoqués somesthésiques (PES)': {'prix': 50000, 'delai': 'Sur RDV'},
                    'Audiométrie tonale': {'prix': 20000, 'delai': '1h'},
                    'Audiométrie vocale': {'prix': 20000, 'delai': '1h'},
                    'Impédancemétrie (tympanométrie)': {'prix': 18000, 'delai': '1h'},
                    'Tests vestibulaires VNG': {'prix': 55000, 'delai': 'Sur RDV'},
                    'Fibroscopie ORL': {'prix': 35000, 'delai': 'Sur RDV'},
                    'Acuité visuelle + réfraction': {'prix': 15000, 'delai': '1h'},
                    'Fond d\'œil': {'prix': 20000, 'delai': '1h'},
                    'OCT (tomographie optique cohérente)': {'prix': 45000, 'delai': '1h'},
                    'Champ visuel automatisé': {'prix': 30000, 'delai': '1h'},
                    'Pachymétrie cornéenne': {'prix': 25000, 'delai': '1h'},
                    'Topographie cornéenne': {'prix': 30000, 'delai': '1h'},
                    'Biométrie oculaire': {'prix': 35000, 'delai': '1h'},
                    'Hystérosalpingographie (HSG)': {'prix': 55000, 'delai': 'Sur RDV'},
                    'Hystéroscopie diagnostique': {'prix': 75000, 'delai': 'Sur RDV'},
                    'Colposcopie': {'prix': 45000, 'delai': 'Sur RDV'},
                    'Débitmétrie urinaire': {'prix': 20000, 'delai': '1h'},
                    'Bilan urodynamique complet': {'prix': 80000, 'delai': 'Sur RDV'},
                }
            },
            {
                'id': 8,
                'name': 'AMBUCare Sénégal',
                'desc': 'Service d\'ambulance et de transport sanitaire 24h/24 à Dakar : transport médicalisé, réanimation mobile, rapatriement et couverture d\'évènements.',
                'type': 'Ambulance médicalisée — Transport & SMUR',
                'zone': 'Dakar (toutes zones)',
                'horaires': '24h/24 · 7j/7',
                'assurances': ['CMU', 'IPM', 'CNAM', 'AXA Assurances Sénégal', 'Allianz / SanlamAllianz', 'Privé (paiement direct)'],
                'pioneer': True,
                'actes': {
                    'Ambulance simple': {'prix': 10000, 'delai': 'Immédiat'},
                    'Ambulance médicalisée avec infirmier': {'prix': 25000, 'delai': 'Immédiat'},
                    'Ambulance médicalisée avec médecin': {'prix': 45000, 'delai': 'Immédiat'},
                    'Transport réanimatoire': {'prix': 90000, 'delai': 'Urgence'},
                    'Évacuation sanitaire': {'prix': 120000, 'delai': 'Urgence'},
                    'Rapatriement national': {'prix': 200000, 'delai': 'Sur devis'},
                    'Rapatriement international': {'prix': 0, 'delai': 'Sur devis'},
                    'Couverture médicale sportive': {'prix': 75000, 'delai': 'Sur réservation'},
                    'Couverture médicale de manifestation publique': {'prix': 90000, 'delai': 'Sur réservation'},
                    'Assistance médicale sur site': {'prix': 60000, 'delai': 'Sur réservation'},
                }
            },
            {
                'id': 9,
                'name': 'Clinique Suma Assistance',
                'desc': 'Clinique privée pluridisciplinaire aux Almadies, ouverte 24h/24, pour soins spécialisés et prise en charge d\'urgence.',
                'type': 'Clinique privée — Soins spécialisés pluridisciplinaires',
                'zone': 'Almadies',
                'horaires': '24h/24 · 7j/7',
                'assurances': ['CMU', 'IPM', 'CNAM', 'AXA Assurances Sénégal', 'Allianz / SanlamAllianz', 'IPRES', 'FNR', 'Tanel Health (Afiyah)', 'Privé (paiement direct)'],
                'pioneer': True,
                'actes': {
                    'Suture plaie simple': {'prix': 18000, 'delai': 'Immédiat'},
                    'Suture plaie complexe': {'prix': 35000, 'delai': 'Immédiat'},
                    'Incision & drainage abcès cutané': {'prix': 25000, 'delai': 'Immédiat'},
                    'Nébulisation thérapeutique': {'prix': 8000, 'delai': 'Immédiat'},
                    'Cryothérapie cutanée': {'prix': 20000, 'delai': 'Sur RDV'},
                    'Exérèse lésion cutanée bénigne': {'prix': 35000, 'delai': 'Sur RDV'},
                    'Électrocoagulation': {'prix': 25000, 'delai': 'Sur RDV'},
                    'Peeling médical': {'prix': 45000, 'delai': 'Sur RDV'},
                    'Pose DIU (stérilet)': {'prix': 25000, 'delai': 'Sur RDV'},
                    'Retrait DIU': {'prix': 15000, 'delai': 'Sur RDV'},
                    'Pose implant contraceptif': {'prix': 20000, 'delai': 'Sur RDV'},
                    'Aspiration endo-utérine': {'prix': 55000, 'delai': 'Sur RDV'},
                    'Biopsie gynécologique': {'prix': 35000, 'delai': 'Sur RDV'},
                    'Sondage vésical': {'prix': 12000, 'delai': 'Immédiat'},
                    'Changement de sonde': {'prix': 10000, 'delai': 'Immédiat'},
                    'Pansement simple': {'prix': 8000, 'delai': 'Immédiat'},
                    'Pansement complexe': {'prix': 18000, 'delai': 'Immédiat'},
                    'Perfusion IV': {'prix': 8000, 'delai': 'Immédiat'},
                    'Injection IM / SC': {'prix': 5000, 'delai': 'Immédiat'},
                    'Soins de plaies chroniques': {'prix': 15000, 'delai': 'Immédiat'},
                    'Nursing médicalisé': {'prix': 20000, 'delai': 'Sur RDV'},
                    'Infiltration articulaire genou': {'prix': 35000, 'delai': 'Sur RDV'},
                    'Infiltration articulaire épaule': {'prix': 35000, 'delai': 'Sur RDV'},
                    'Viscosupplémentation': {'prix': 65000, 'delai': 'Sur RDV'},
                    'Injection PRP': {'prix': 80000, 'delai': 'Sur RDV'},
                    'Ponction articulaire évacuatrice': {'prix': 30000, 'delai': 'Sur RDV'},
                    'Nébulisation pédiatrique': {'prix': 10000, 'delai': 'Immédiat'},
                    'Perfusion pédiatrique': {'prix': 18000, 'delai': 'Immédiat'},
                    'Hémodialyse chronique': {'prix': 55000, 'delai': 'Sur planning'},
                    'Hémodialyse aiguë': {'prix': 80000, 'delai': 'Urgence'},
                    'Soins cathéter de dialyse': {'prix': 15000, 'delai': 'Sur RDV'},
                    'ECG standard 12 dérivations': {'prix': 12000, 'delai': '30min'},
                    'Écho-cœur (échocardiographie transthoracique)': {'prix': 52000, 'delai': '1h'},
                    'Consultation psychiatrique initiale': {'prix': 45000, 'delai': 'Sur RDV'},
                    'Consultation psychiatrique de suivi': {'prix': 35000, 'delai': 'Sur RDV'},
                }
            },
            {
                'id': 10,
                'name': 'Centre Kiné & Rééducation Mermoz',
                'desc': 'Centre de kinésithérapie et de rééducation fonctionnelle à Mermoz, encadré par des praticiens diplômés.',
                'type': 'Kinésithérapie & rééducation fonctionnelle',
                'zone': 'Mermoz',
                'horaires': 'Lun–Sam 08h–19h',
                'assurances': ['CMU', 'IPM', 'AXA Assurances Sénégal', 'Allianz / SanlamAllianz', 'IPRES', 'Privé (paiement direct)'],
                'pioneer': True,
                'actes': {
                    'Rééducation post-traumatique': {'prix': 15000, 'delai': 'Sur RDV'},
                    'Rééducation post-opératoire genou': {'prix': 18000, 'delai': 'Sur RDV'},
                    'Rééducation lombalgie / cervicalgie': {'prix': 12000, 'delai': 'Sur RDV'},
                    'Kiné respiratoire adulte': {'prix': 14000, 'delai': 'Sur RDV'},
                    'Kiné respiratoire pédiatrique': {'prix': 12000, 'delai': 'Sur RDV'},
                    'Rééducation post-AVC': {'prix': 22000, 'delai': 'Sur RDV'},
                    'Rééducation périnéale post-partum': {'prix': 15000, 'delai': 'Sur RDV'},
                    'Drainage lymphatique manuel': {'prix': 20000, 'delai': 'Sur RDV'},
                    'Kinésithérapie à domicile': {'prix': 25000, 'delai': 'Sur RDV'},
                }
            },
            {
                'id': 11,
                'name': 'Cabinet Psychologie & Psychiatrie',
                'type': 'Centre de santé mentale',
                'zone': 'Fann Résidence',
                'horaires': 'Lun–Sam 09h–18h · Téléconsultation disponible',
                'assurances': ['AXA Assurances Sénégal', 'Allianz / SanlamAllianz', 'Tanel Health (Afiyah)', 'Susu Africa', 'Privé (paiement direct)'],
                'pioneer': False,
                'actes': {
                    'Consultation de psychologie initiale': {'prix': 35000, 'delai': 'Sur RDV'},
                    'Séance de psychologie de suivi': {'prix': 25000, 'delai': 'Sur RDV'},
                    'Thérapie individuelle': {'prix': 25000, 'delai': 'Sur RDV'},
                    'Thérapie de couple': {'prix': 40000, 'delai': 'Sur RDV'},
                    'Thérapie familiale': {'prix': 45000, 'delai': 'Sur RDV'},
                    'Téléconsultation psychologique': {'prix': 20000, 'delai': 'Sur RDV'},
                    'Consultation psychiatrique initiale': {'prix': 45000, 'delai': 'Sur RDV'},
                    'Consultation psychiatrique de suivi': {'prix': 35000, 'delai': 'Sur RDV'},
                    'Évaluation psychiatrique diagnostique': {'prix': 65000, 'delai': 'Sur RDV'},
                    'Ajustement traitement psychotrope': {'prix': 35000, 'delai': 'Sur RDV'},
                    'Téléconsultation psychiatrique': {'prix': 30000, 'delai': 'Sur RDV'},
                }
            },
            {
                'id': 12,
                'name': 'Cabinet DentaCare Plateau',
                'desc': 'Cabinet dentaire au Plateau : soins conservateurs, prothèses et chirurgie dentaire, dans un cadre moderne.',
                'type': 'Cabinet dentaire — Soins complets & Esthétique',
                'zone': 'Plateau',
                'horaires': 'Lun–Sam 08h–18h · Urgences',
                'assurances': ['CMU', 'IPM', 'CNAM', 'AXA Assurances Sénégal', 'Allianz / SanlamAllianz', 'Privé (paiement direct)'],
                'pioneer': True,
                'actes': {
                    'Consultation dentaire standard': {'prix': 15000, 'delai': 'Sur RDV'},
                    'Consultation dentaire spécialisée': {'prix': 20000, 'delai': 'Sur RDV'},
                    'Consultation d\'urgence dentaire': {'prix': 22000, 'delai': 'Immédiat'},
                    'Bilan bucco-dentaire complet': {'prix': 25000, 'delai': 'Sur RDV'},
                    'Détartrage complet': {'prix': 20000, 'delai': 'Sur RDV'},
                    'Détartrage + polissage + fluoration': {'prix': 28000, 'delai': 'Sur RDV'},
                    'Traitement carie (composite)': {'prix': 35000, 'delai': 'Sur RDV'},
                    'Obturation amalgame': {'prix': 25000, 'delai': 'Sur RDV'},
                    'Traitement endodontique mono-radiculaire': {'prix': 55000, 'delai': 'Sur RDV'},
                    'Traitement endodontique bi-radiculaire': {'prix': 70000, 'delai': 'Sur RDV'},
                    'Traitement endodontique multi-radiculaire': {'prix': 90000, 'delai': 'Sur RDV'},
                    'Reprise endodontique': {'prix': 80000, 'delai': 'Sur RDV'},
                    'Extraction simple': {'prix': 25000, 'delai': 'Sur RDV'},
                    'Extraction chirurgicale': {'prix': 45000, 'delai': 'Sur RDV'},
                    'Extraction dent de sagesse incluse': {'prix': 65000, 'delai': 'Sur RDV'},
                    'Drainage abcès dentaire': {'prix': 20000, 'delai': 'Immédiat'},
                    'Couronne céramique / zirconium': {'prix': 180000, 'delai': '2 semaines'},
                    'Bridge 3 éléments': {'prix': 350000, 'delai': '3 semaines'},
                    'Prothèse amovible partielle': {'prix': 250000, 'delai': '3 semaines'},
                    'Prothèse complète': {'prix': 350000, 'delai': '3 semaines'},
                    'Consultation implantaire': {'prix': 25000, 'delai': 'Sur RDV'},
                    'Pose d\'implant dentaire': {'prix': 350000, 'delai': 'Sur RDV'},
                    'Greffe osseuse': {'prix': 200000, 'delai': 'Sur RDV'},
                    'Couronne sur implant': {'prix': 180000, 'delai': '2 semaines'},
                    'Appareil orthodontique fixe (arcade)': {'prix': 600000, 'delai': 'Sur devis'},
                    'Appareil amovible': {'prix': 180000, 'delai': '2 semaines'},
                    'Gouttières transparentes (aligneurs)': {'prix': 800000, 'delai': 'Sur devis'},
                    'Contention post-orthodontie': {'prix': 80000, 'delai': 'Sur RDV'},
                    'Blanchiment dentaire professionnel': {'prix': 80000, 'delai': 'Sur RDV'},
                    'Facette céramique (par dent)': {'prix': 150000, 'delai': '2 semaines'},
                    'Smile design (consultation + plan)': {'prix': 50000, 'delai': 'Sur RDV'},
                }
            },
            {
                'id': 13,
                'name': 'Laboratoire Almadies BioMed',
                'desc': 'Laboratoire d\'analyses médicales aux Almadies, avec prélèvement à domicile et résultats en ligne.',
                'type': 'Laboratoire d\'analyses médicales',
                'zone': 'Almadies',
                'horaires': 'Lun–Sam 07h–18h',
                'assurances': ['CMU', 'IPM', 'CNAM', 'Allianz / SanlamAllianz', 'Privé (paiement direct)'],
                'pioneer': True,
                'actes': {
                    'NFS / Hémogramme': {'prix': 7500, 'delai': '1h30'},
                    'VS': {'prix': 3000, 'delai': '1h'},
                    'Frottis sanguin': {'prix': 4500, 'delai': '24h'},
                    'Groupe ABO/Rhésus': {'prix': 4500, 'delai': '1h'},
                    'Fer sérique': {'prix': 5500, 'delai': '4h'},
                    'Ferritine': {'prix': 8500, 'delai': '24h'},
                    'TP / INR': {'prix': 7000, 'delai': '2h'},
                    'TCA': {'prix': 7000, 'delai': '2h'},
                    'Fibrinogène': {'prix': 8500, 'delai': '2h'},
                    'D-Dimères': {'prix': 17000, 'delai': '4h'},
                    'Glycémie à jeun': {'prix': 3000, 'delai': '1h'},
                    'HbA1c': {'prix': 8500, 'delai': '24h'},
                    'Urée sanguine': {'prix': 4000, 'delai': '2h'},
                    'Créatininémie': {'prix': 4000, 'delai': '2h'},
                    'Natrémie': {'prix': 3000, 'delai': '2h'},
                    'Kaliémie': {'prix': 3000, 'delai': '2h'},
                    'ASAT': {'prix': 4000, 'delai': '4h'},
                    'ALAT': {'prix': 4000, 'delai': '4h'},
                    'GGT': {'prix': 4000, 'delai': '4h'},
                    'CRP': {'prix': 5000, 'delai': '2h'},
                    'Cholestérol total': {'prix': 4000, 'delai': '24h'},
                    'HDL': {'prix': 4500, 'delai': '24h'},
                    'LDL': {'prix': 4500, 'delai': '24h'},
                    'Triglycérides': {'prix': 4500, 'delai': '24h'},
                    'VIH Ag/Ac': {'prix': 9500, 'delai': '2h'},
                    'HBsAg': {'prix': 7500, 'delai': '2h'},
                    'Anti-VHC': {'prix': 8500, 'delai': '24h'},
                    'Syphilis VDRL': {'prix': 4500, 'delai': '24h'},
                    'Syphilis TPHA': {'prix': 4500, 'delai': '24h'},
                    'Toxoplasmose IgG/IgM': {'prix': 11000, 'delai': '24h'},
                    'ECBU + antibiogramme': {'prix': 10000, 'delai': '48h'},
                    'Prélèvement vaginal / cervico-vaginal': {'prix': 13000, 'delai': '48h'},
                    'Goutte épaisse / TDR paludisme': {'prix': 5500, 'delai': '1h'},
                    'TSH': {'prix': 11000, 'delai': '24h'},
                    'FT4': {'prix': 9500, 'delai': '24h'},
                    'PSA total': {'prix': 11000, 'delai': '24h'},
                    'CEA': {'prix': 11000, 'delai': '48h'},
                    'AFP': {'prix': 11000, 'delai': '48h'},
                }
            },
            {
                'id': 14,
                'name': 'Labo Analyses Liberté VI',
                'type': 'Laboratoire d\'analyses médicales',
                'zone': 'Liberté VI',
                'horaires': 'Lun–Ven 07h–17h · Sam 07h30–13h',
                'assurances': ['CMU', 'CNAM', 'MSAE', 'FNR', 'Privé (paiement direct)', 'Mutuelles communautaires CMU'],
                'pioneer': False,
                'actes': {
                    'NFS / Hémogramme': {'prix': 8000, 'delai': '2h'},
                    'Réticulocytes': {'prix': 5500, 'delai': '4h'},
                    'VS': {'prix': 3200, 'delai': '2h'},
                    'Groupe ABO/Rhésus': {'prix': 4800, 'delai': '1h'},
                    'Fer sérique': {'prix': 5800, 'delai': '4h'},
                    'Ferritine': {'prix': 8800, 'delai': '24h'},
                    'Vitamine B12': {'prix': 13000, 'delai': '24h'},
                    'Folates (B9)': {'prix': 11000, 'delai': '24h'},
                    'TP / INR': {'prix': 7200, 'delai': '2h'},
                    'TCA': {'prix': 7200, 'delai': '2h'},
                    'Fibrinogène': {'prix': 8800, 'delai': '2h'},
                    'Glycémie à jeun': {'prix': 3200, 'delai': '1h'},
                    'HbA1c': {'prix': 8800, 'delai': '24h'},
                    'Urée sanguine': {'prix': 4200, 'delai': '2h'},
                    'Créatininémie': {'prix': 4200, 'delai': '2h'},
                    'CRP': {'prix': 5200, 'delai': '2h'},
                    'Cholestérol total': {'prix': 4200, 'delai': '24h'},
                    'HDL': {'prix': 4700, 'delai': '24h'},
                    'LDL': {'prix': 4700, 'delai': '24h'},
                    'Triglycérides': {'prix': 4700, 'delai': '24h'},
                    'Procalcitonine': {'prix': 21000, 'delai': '4h'},
                    'VIH Ag/Ac': {'prix': 9800, 'delai': '2h'},
                    'HBsAg': {'prix': 7800, 'delai': '2h'},
                    'Anti-HBs': {'prix': 7800, 'delai': '24h'},
                    'Anti-VHC': {'prix': 8800, 'delai': '24h'},
                    'Syphilis VDRL': {'prix': 4800, 'delai': '24h'},
                    'ECBU + antibiogramme': {'prix': 10500, 'delai': '48h'},
                    'Coproculture': {'prix': 11500, 'delai': '48h'},
                    'Goutte épaisse / TDR paludisme': {'prix': 5800, 'delai': '1h'},
                    'Examen parasitologique des selles': {'prix': 6500, 'delai': '48h'},
                    'TSH': {'prix': 11500, 'delai': '24h'},
                    'FT4': {'prix': 9800, 'delai': '24h'},
                }
            },
            {
                'id': 15,
                'name': 'Labo Fann Medical Center',
                'desc': 'Laboratoire hospitalier à Fann Résidence, disponible 24h/24 pour la biologie d\'urgence et de routine.',
                'type': 'Laboratoire d\'analyses médicales — Centre hospitalier',
                'zone': 'Fann Résidence',
                'horaires': '24h/24 · 7j/7 (urgences biologiques)',
                'assurances': ['CMU', 'IPM', 'CNAM', 'IPRES', 'FNR', 'MSAE', 'AXA Assurances Sénégal', 'Tanel Health (Afiyah)', 'Privé (paiement direct)'],
                'pioneer': True,
                'actes': {
                    'NFS / Hémogramme': {'prix': 9000, 'delai': '1h'},
                    'Réticulocytes': {'prix': 6500, 'delai': '2h'},
                    'VS': {'prix': 3800, 'delai': '1h'},
                    'Frottis sanguin': {'prix': 5500, 'delai': '4h'},
                    'Groupe ABO/Rhésus': {'prix': 5500, 'delai': '30min'},
                    'RAI': {'prix': 13000, 'delai': '1h'},
                    'Test de Coombs direct': {'prix': 9500, 'delai': '2h'},
                    'Électrophorèse de l\'hémoglobine': {'prix': 19000, 'delai': '24h'},
                    'Fer sérique': {'prix': 6500, 'delai': '2h'},
                    'Ferritine': {'prix': 9500, 'delai': '4h'},
                    'TP / INR': {'prix': 8000, 'delai': '1h'},
                    'TCA': {'prix': 8000, 'delai': '1h'},
                    'Fibrinogène': {'prix': 9500, 'delai': '1h'},
                    'D-Dimères': {'prix': 19000, 'delai': '2h'},
                    'Activité anti-Xa': {'prix': 23000, 'delai': '2h'},
                    'Glycémie à jeun': {'prix': 4000, 'delai': '30min'},
                    'HbA1c': {'prix': 9500, 'delai': '4h'},
                    'Urée sanguine': {'prix': 5000, 'delai': '1h'},
                    'Créatininémie': {'prix': 5000, 'delai': '1h'},
                    'Natrémie': {'prix': 4000, 'delai': '1h'},
                    'Kaliémie': {'prix': 4000, 'delai': '1h'},
                    'Calcémie': {'prix': 4500, 'delai': '1h'},
                    'ASAT': {'prix': 5000, 'delai': '2h'},
                    'ALAT': {'prix': 5000, 'delai': '2h'},
                    'GGT': {'prix': 5000, 'delai': '2h'},
                    'CRP': {'prix': 6000, 'delai': '1h'},
                    'Procalcitonine': {'prix': 23000, 'delai': '2h'},
                    'Cholestérol total': {'prix': 5000, 'delai': '4h'},
                    'HDL': {'prix': 5500, 'delai': '4h'},
                    'LDL': {'prix': 5500, 'delai': '4h'},
                    'Triglycérides': {'prix': 5500, 'delai': '4h'},
                    'VIH Ag/Ac': {'prix': 10500, 'delai': '1h'},
                    'Charge virale VIH': {'prix': 58000, 'delai': '48h'},
                    'HBsAg': {'prix': 8500, 'delai': '1h'},
                    'Anti-HBs': {'prix': 8500, 'delai': '4h'},
                    'Anti-HBc total': {'prix': 9500, 'delai': '4h'},
                    'ADN VHB (charge virale HBV)': {'prix': 52000, 'delai': '48h'},
                    'Anti-VHC': {'prix': 9500, 'delai': '4h'},
                    'ARN VHC (charge virale HCV)': {'prix': 52000, 'delai': '48h'},
                    'Syphilis VDRL': {'prix': 5500, 'delai': '4h'},
                    'Syphilis TPHA': {'prix': 5500, 'delai': '4h'},
                    'Dengue NS1/IgM/IgG': {'prix': 19000, 'delai': '4h'},
                    'ECBU + antibiogramme': {'prix': 12000, 'delai': '24h'},
                    'Hémocultures': {'prix': 22000, 'delai': '24h'},
                    'Prélèvement vaginal / cervico-vaginal': {'prix': 15000, 'delai': '24h'},
                    'Recherche BK / BAAR': {'prix': 13000, 'delai': '24h'},
                    'ECB plaies / pus': {'prix': 14000, 'delai': '24h'},
                    'TSH': {'prix': 13000, 'delai': '4h'},
                    'FT4': {'prix': 11000, 'delai': '4h'},
                    'Cortisol': {'prix': 19000, 'delai': '4h'},
                    'Prolactine': {'prix': 12000, 'delai': '4h'},
                    'FSH': {'prix': 9000, 'delai': '4h'},
                    'LH': {'prix': 9000, 'delai': '4h'},
                    'Estradiol': {'prix': 9000, 'delai': '4h'},
                    'PSA total': {'prix': 13000, 'delai': '4h'},
                    'PSA libre': {'prix': 10000, 'delai': '4h'},
                    'CEA': {'prix': 13000, 'delai': '24h'},
                    'AFP': {'prix': 13000, 'delai': '24h'},
                    'CA 125': {'prix': 16000, 'delai': '24h'},
                    'βHCG quantitatif': {'prix': 13000, 'delai': '4h'},
                    'Gaz du sang artériel': {'prix': 22000, 'delai': '30min'},
                    'PCR BK': {'prix': 38000, 'delai': '24h'},
                    'GeneXpert MTB/RIF': {'prix': 42000, 'delai': '24h'},
                    'Goutte épaisse / TDR paludisme': {'prix': 6500, 'delai': '30min'},
                }
            },
            {
                'id': 16,
                'name': 'Clinique Dantec Lab',
                'type': 'Laboratoire hospitalier privé',
                'zone': 'Dakar Plateau',
                'horaires': 'Lun–Sam 07h30–17h30',
                'assurances': ['CNAM', 'IPM', 'MSAE', 'FNR', 'Privé (paiement direct)'],
                'pioneer': False,
                'actes': {
                    'NFS / Hémogramme': {'prix': 8200, 'delai': '2h'},
                    'VS': {'prix': 3400, 'delai': '2h'},
                    'Groupe ABO/Rhésus': {'prix': 5000, 'delai': '1h'},
                    'Fer sérique': {'prix': 6000, 'delai': '4h'},
                    'Ferritine': {'prix': 9000, 'delai': '24h'},
                    'TP / INR': {'prix': 7600, 'delai': '2h'},
                    'TCA': {'prix': 7600, 'delai': '2h'},
                    'D-Dimères': {'prix': 18500, 'delai': '4h'},
                    'Glycémie à jeun': {'prix': 3600, 'delai': '1h'},
                    'HbA1c': {'prix': 9200, 'delai': '24h'},
                    'Créatininémie': {'prix': 4600, 'delai': '2h'},
                    'Urée sanguine': {'prix': 4600, 'delai': '2h'},
                    'CRP': {'prix': 5600, 'delai': '2h'},
                    'ASAT': {'prix': 4600, 'delai': '4h'},
                    'ALAT': {'prix': 4600, 'delai': '4h'},
                    'Cholestérol total': {'prix': 4600, 'delai': '24h'},
                    'Triglycérides': {'prix': 4800, 'delai': '24h'},
                    'VIH Ag/Ac': {'prix': 10000, 'delai': '2h'},
                    'HBsAg': {'prix': 8000, 'delai': '2h'},
                    'Anti-VHC': {'prix': 9000, 'delai': '24h'},
                    'Syphilis VDRL': {'prix': 5000, 'delai': '24h'},
                    'ECBU + antibiogramme': {'prix': 11500, 'delai': '48h'},
                    'Hémocultures': {'prix': 21000, 'delai': '48h'},
                    'Coproculture': {'prix': 12500, 'delai': '48h'},
                    'Goutte épaisse / TDR paludisme': {'prix': 6000, 'delai': '1h'},
                    'TSH': {'prix': 12500, 'delai': '24h'},
                    'FT4': {'prix': 10500, 'delai': '24h'},
                    'Examen anapath. biopsie': {'prix': 38000, 'delai': '5 jours'},
                    'Frottis cervico-vaginal (FCV)': {'prix': 19000, 'delai': '5 jours'},
                }
            },
        ]

        # Mapping des délais vers les choix du modèle
        DELAI_MAPPING = {
            'Immédiat': 'immediat',
            'Urgence': 'immediat',
            '30min': '30min',
            '1h': '1h',
            '1h30': '2h',
            '2h': '2h',
            '4h': '4h',
            '24h': '24h',
            '48h': '48h',
            '72h': '72h',
            '7 jours': '7j',
            '5 jours': '7j',
            '2 semaines': 'rdv',
            '3 semaines': 'rdv',
            'Sur RDV': 'rdv',
            'Sur devis': 'rdv',
            'Sur réservation': 'rdv',
            'Sur planning': 'rdv',
        }

        # S'assurer que les assurances existent
        for assurance_data in ASSURANCES_FROM_DOCS:
            assurance = Assurance.objects.filter(name=assurance_data['name']).first()
            if not assurance:
                try:
                    Assurance.objects.create(
                        name=assurance_data['name'],
                        segment=assurance_data['segment'],
                        description=assurance_data.get('description', ''),
                        is_active=True
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Erreur création assurance {assurance_data["name"]}: {e}')
                    )
        
        # Ajouter les assurances manuelles qui ne sont pas dans le catalogue
        manual_assurances = [
            {'name': 'CMU', 'segment': 'public', 'description': 'Couverture Maladie Universelle'},
            {'name': 'IPM', 'segment': 'public', 'description': 'Institut de Prévoyance Maladie'},
            {'name': 'CNAM', 'segment': 'public', 'description': 'Caisse Nationale Assurance Maladie'},
            {'name': 'Allianz / SanlamAllianz', 'segment': 'privee_iard', 'description': 'Assurance privée'},
            {'name': 'Privé (paiement direct)', 'segment': 'privee_iard', 'description': 'Paiement direct sans assurance'},
            {'name': 'SONAM SA / SONAM Mutuelle', 'segment': 'privee_iard', 'description': 'Société Nationale Assurance Maladie'},
            {'name': 'Salama Assurances', 'segment': 'privee_iard', 'description': 'Assurance Salama'},
            {'name': 'GGA Sénégal – Ma Santé Plus', 'segment': 'privee_iard', 'description': 'GGA Sénégal'},
            {'name': 'La Prévoyance Assurances (PA)', 'segment': 'privee_iard', 'description': 'La Prévoyance'},
            {'name': 'Assurance Sécurité Sénégalaise (ASS)', 'segment': 'privee_iard', 'description': 'ASS'},
            {'name': 'MAAS', 'segment': 'privee_iard', 'description': 'MAAS'},
            {'name': 'CNART', 'segment': 'privee_iard', 'description': 'CNART'},
            {'name': 'Susu Africa', 'segment': 'digitale', 'description': 'Susu Africa'},
            {'name': 'Sammanté', 'segment': 'digitale', 'description': 'Sammanté'},
            {'name': 'Munasaili', 'segment': 'digitale', 'description': 'Munasaili'},
            {'name': 'IPRES', 'segment': 'public', 'description': 'Institut de Prévoyance Retraite Sénégal'},
            {'name': 'FNR', 'segment': 'public', 'description': 'Fonds National Retraite'},
            {'name': 'MSAE', 'segment': 'public', 'description': 'Mutuelle Santé des Agents de l\'État'},
            {'name': 'Plan Sésame', 'segment': 'public', 'description': 'Plan Sésame'},
            {'name': 'Mutuelles communautaires CMU', 'segment': 'public', 'description': 'Mutuelles communautaires'},
        ]
        
        for assurance_data in manual_assurances:
            assurance = Assurance.objects.filter(name=assurance_data['name']).first()
            if not assurance:
                try:
                    Assurance.objects.create(
                        name=assurance_data['name'],
                        segment=assurance_data['segment'],
                        description=assurance_data.get('description', ''),
                        is_active=True
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Erreur création assurance {assurance_data["name"]}: {e}')
                    )

        # Récupérer ou créer le plan d'abonnement par défaut
        default_plan, _ = SubscriptionPlan.objects.get_or_create(
            name='Gratuit',
            defaults={
                'slug': 'gratuit',
                'monthly_price_fcfa': 0,
                'is_default': True,
                'is_public': True,
                'is_pioneer_offer': False,
                'order': 0
            }
        )

        # Créer les structures
        created_count = 0
        updated_count = 0

        for struct_data in STRUCTURES:
            # Créer ou récupérer le type d'organisme
            type_org, _ = TypeOrganisme.objects.get_or_create(
                name=struct_data['type'],
                defaults={'order': 0}
            )

            # Créer un utilisateur pour la structure
            username = struct_data['name'].lower().replace(' ', '_').replace('-', '_')
            user, user_created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@medcare.sn',
                    'first_name': struct_data['name'].split()[0] if ' ' in struct_data['name'] else struct_data['name'],
                    'user_type': 'prestataire',
                    'is_active': True
                }
            )
            if user.user_type != 'prestataire':
                user.user_type = 'prestataire'
                user.save(update_fields=['user_type'])
            user.set_password('medcare2024')
            user.save(update_fields=['password'])

            # Créer ou mettre à jour l'organisme
            org, created = OrganismeDeSante.objects.update_or_create(
                user=user,
                defaults={
                    'name': struct_data['name'],
                    'description': struct_data.get('desc', ''),
                    'type_organisme': type_org,
                    'address': struct_data['zone'],
                    'quartier': struct_data['zone'],
                    'city': 'Dakar',
                    'contact_phone': '+221770000000',
                    'whatsapp_number': '+221770000000',
                    'opening_hours': struct_data['horaires'],
                    'is_active': True,
                    'is_verified': True,
                    'subscription_plan': default_plan,
                }
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

            # Associer les assurances
            for assurance_name in struct_data['assurances']:
                try:
                    assurance = Assurance.objects.get(name=assurance_name)
                    PriseEnChargeAssurance.objects.get_or_create(
                        organisme=org,
                        assurance=assurance,
                        defaults={'is_active': True}
                    )
                except Assurance.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'Assurance non trouvée: {assurance_name}')
                    )

            # Créer les PrestataireActe
            for acte_name, acte_data in struct_data['actes'].items():
                acte = ActeMedical.objects.filter(name=acte_name).first()
                if acte:
                    delai = DELAI_MAPPING.get(acte_data['delai'], 'rdv')
                    
                    PrestataireActe.objects.update_or_create(
                        organisme=org,
                        acte=acte,
                        defaults={
                            'price': acte_data['prix'],
                            'delai': delai,
                            'is_available': True
                        }
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Acte non trouvé: {acte_name}')
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'Succès: {created_count} structures créées, {updated_count} mises à jour'
            )
        )
