import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medcare_connect.settings")
import django
django.setup()

from healthcare.models import OrganismeDeSante

verified = OrganismeDeSante.objects.filter(is_verified=True)
print(f"Structures VÉRIFIÉES : {verified.count()}")
for org in verified:
    print(f"  ✓ {org.name} ({org.type_organisme})")

all_orgs = OrganismeDeSante.objects.all()
print(f"\nTotal structures en BD : {all_orgs.count()}")

if all_orgs.count() > 0:
    print("\nTous les statuts :")
    for org in all_orgs[:15]:
        status = "✓ Vérifié" if org.is_verified else "✗ Non vérifié"
        print(f"  {status} — {org.name} ({org.type_organisme})")
