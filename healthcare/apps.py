from django.apps import AppConfig


class HealthcareConfig(AppConfig):
    name = "healthcare"

    def ready(self):
        # Enregistrement des filtres template (catalogue, fiches…)
        try:
            import healthcare.templatetags.healthcare_display  # noqa: F401
        except ImportError:
            pass
