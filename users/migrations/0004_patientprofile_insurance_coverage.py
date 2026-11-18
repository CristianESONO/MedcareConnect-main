from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_image_upload_unique_maxlen"),
    ]

    operations = [
        migrations.AddField(
            model_name="patientprofile",
            name="insurance_coverage_pct",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Taux global de prise en charge (0–100 %) saisi par le patient pour les estimations.",
                max_digits=5,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="insurance_coverage_by_category",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Taux par catégorie d'acte (niveau 2) : {« Hématologie »: 70, …}.",
            ),
        ),
    ]
