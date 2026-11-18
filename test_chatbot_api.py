import os
import sys
import django

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medcare_connect.settings')
django.setup()

from django.test import Client

c = Client(SERVER_NAME='127.0.0.1')

print("1. Testing GET /sante/assistant-collecte/ ...", flush=True)
r_view = c.get('/sante/assistant-collecte/')
print(f"Status view: {r_view.status_code}", flush=True)

print("2. Testing GET /sante/api/chatbot/suggest/?q=nfs ...", flush=True)
r_sug = c.get('/sante/api/chatbot/suggest/?q=nfs')
print(f"Status suggest: {r_sug.status_code} | data: {r_sug.json()}", flush=True)

print("3. Testing POST /sante/api/chatbot/submit/ ...", flush=True)
payload = {
    'mode': 'patient',
    'q1_besoin': 'NFS et Bilan sanguin',
    'q1_service_slug': 'biologie-medicale',
    'q2_ville': 'Dakar',
    'q3_delai': 'demain',
    'q3_creneau': 'matin',
    'q4_nom': 'Aminata Sall',
    'q4_telephone': '+221 77 123 45 67',
    'q4_email': 'aminata@example.com'
}
r_sub = c.post('/sante/api/chatbot/submit/', data=payload, content_type='application/json')
print(f"Status submit: {r_sub.status_code} | response: {r_sub.json()}", flush=True)
