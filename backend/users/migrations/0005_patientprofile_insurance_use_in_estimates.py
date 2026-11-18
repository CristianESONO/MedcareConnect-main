from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_patientprofile_insurance_coverage"),
    ]

    operations = [
        migrations.AddField(
            model_name="patientprofile",
            name="insurance_use_in_estimates",
            field=models.BooleanField(
                default=True,
                help_text="Si décoché, les tarifs bruts sont affichés (panier/devis) sans prise en charge estimée.",
            ),
        ),
    ]
