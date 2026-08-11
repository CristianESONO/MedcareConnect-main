from django.core.management.base import BaseCommand
from healthcare.models import ServiceMedical


class Command(BaseCommand):
    help = "Met à jour l'ordre des services médicaux pour correspondre à l'ordre du demo"

    def handle(self, *args, **options):
        # Ordre correspondant au demo ACTES_TREE (avec et sans emoji)
        SERVICE_ORDER = {
            "Biologie médicale": 1,
            "🧬 Biologie médicale": 1,
            "Imagerie médicale": 2,
            "🖥 Imagerie médicale": 2,
            "Explorations fonctionnelles": 3,
            "⚡ Explorations fonctionnelles": 3,
            "Ambulance médicalisée": 4,
            "🚑 Ambulance médicalisée": 4,
            "Soins spécialisés": 5,
            "🩺 Soins spécialisés": 5,
            "Soins dentaires": 6,
            "🦷 Soins dentaires": 6,
        }

        updated = 0
        for name, order in SERVICE_ORDER.items():
            try:
                svc = ServiceMedical.objects.get(name=name)
                if svc.order != order:
                    svc.order = order
                    svc.save()
                    self.stdout.write(self.style.SUCCESS(f"✓ {name}: order={order}"))
                    updated += 1
                else:
                    self.stdout.write(f"  {name}: déjà à order={order}")
            except ServiceMedical.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"✗ {name}: non trouvé dans la base"))

        self.stdout.write(f"\nTotal mis à jour: {updated}")
