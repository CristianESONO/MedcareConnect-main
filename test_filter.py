import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medcare_connect.settings")
import django
django.setup()

from healthcare.models import ServiceMedical
from medcare_connect.views import is_excluded_pillar_service, _home_vitrine_context

print("=== ALL SERVICES ===")
for s in ServiceMedical.objects.filter(is_active=True).order_by("order")[:15]:
    excluded = is_excluded_pillar_service(s)
    print(f"Name: {s.name[:40]:40} | Slug: {s.slug:30} | Excluded: {excluded}")

print("\n=== CONTEXT PILLARS ===")
ctx = _home_vitrine_context()
print(f"Total pillars returned: {len(ctx['pillars'])}")
for p in ctx["pillars"]:
    print(f"  - {p['service'].name}")
