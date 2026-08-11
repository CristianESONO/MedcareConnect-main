import django, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'medcare_connect.settings'
django.setup()
from healthcare.models import OrganismeDeSante, PrestataireActe

# Show all ambulance service orgs
print("=== Ambulance service orgs ===")
for o in OrganismeDeSante.objects.filter(is_active=True, is_ambulance_service=True):
    print(f"  id={o.id}  name={o.name}")

# Show Hopital Principal de Dakar
print("\n=== Hopital Principal de Dakar ===")
for o in OrganismeDeSante.objects.filter(name__icontains="principal", is_active=True):
    print(f"  id={o.id}  name={o.name}  is_ambulance_service={o.is_ambulance_service}")

# Show actes for any ambulance org
print("\n=== Actes for ambulance orgs ===")
for pa in PrestataireActe.objects.filter(organisme__is_ambulance_service=True, is_available=True).select_related("acte","organisme"):
    print(f"  org={pa.organisme.name}  acte={pa.acte.name}")
