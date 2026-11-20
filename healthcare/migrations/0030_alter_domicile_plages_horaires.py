from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("healthcare", "0029_actemedical_nomenclature_coef_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organismedesante",
            name="domicile_plages_horaires",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Ex. : 7h–10h Lun–Sam",
                max_length=500,
                verbose_name="Plages horaires à domicile",
            ),
        ),
    ]
