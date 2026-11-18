from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("healthcare", "0018_actemedical_rdv_prerequisites"),
    ]

    operations = [
        migrations.AddField(
            model_name="prestataireacte",
            name="rdv_prerequisites",
            field=models.TextField(
                blank=True,
                verbose_name="Consignes / prérequis RDV (structure)",
                help_text="Message personnalisé pour vos patients (rappels automatiques). Laisse vide pour utiliser la suggestion MedCare.",
            ),
        ),
        migrations.AddField(
            model_name="prestataireacte",
            name="rdv_prerequisites_active",
            field=models.BooleanField(
                default=True,
                verbose_name="Diffuser les consignes au patient",
                help_text="Inclure ce message dans les rappels RDV si une règle l'active.",
            ),
        ),
    ]
