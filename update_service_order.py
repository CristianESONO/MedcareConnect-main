"""
update_service_order.py — Met à jour l'ordre des services médicaux pour correspondre à l'ordre du demo.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medcare.settings')
django.setup()

from healthcare.models import ServiceMedical

# Ordre correspondant au demo ACTES_TREE
SERVICE_ORDER = {
    "Biologie médicale": 1,
    "Imagerie médicale": 2,
    "Explorations fonctionnelles": 3,
    "Ambulance médicalisée": 4,
    "Soins spécialisés": 5,
    "Soins dentaires": 6,
}

updated = 0
for name, order in SERVICE_ORDER.items():
    try:
        svc = ServiceMedical.objects.get(name=name)
        if svc.order != order:
            svc.order = order
            svc.save()
            print(f"✓ {name}: order={order}")
            updated += 1
        else:
            print(f"  {name}: déjà à order={order}")
    except ServiceMedical.DoesNotExist:
        print(f"✗ {name}: non trouvé dans la base")

print(f"\nTotal mis à jour: {updated}")
