from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("healthcare", "0021_remove_reseau_plan"),
    ]

    operations = [
        migrations.AddField(
            model_name="organismedesante",
            name="domicile_delai_intervention",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Délai indicatif pour les prestations à domicile (catalogue actes).",
                max_length=40,
                verbose_name="Délai d'intervention à domicile",
            ),
        ),
        migrations.AddField(
            model_name="organismedesante",
            name="domicile_plages_horaires",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Ex. : 7h–10h Lun–Sam",
                max_length=120,
                verbose_name="Plages horaires à domicile",
            ),
        ),
    ]
