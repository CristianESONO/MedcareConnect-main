import os
import sys
import django

sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medcare_connect.settings')
django.setup()

from healthcare.models import ServiceMedical, ActeMedical

print("=== SERVICES MEDICAUX (PILIERS) DANS LA DB ===")
for s in ServiceMedical.objects.all().order_by('order', 'id'):
    act_count = ActeMedical.objects.filter(service_medical_category=s).count()
    lvl2 = ActeMedical.objects.filter(service_medical_category=s, level=2).count()
    lvl3 = ActeMedical.objects.filter(service_medical_category=s, level=3).count()
    print(f"ID={s.id} | Slug='{s.slug}' | Nom='{s.name}' | Total={act_count} (lvl2={lvl2}, lvl3={lvl3})")
