from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("healthcare", "0017_plans_biz_eco_003"),
    ]

    operations = [
        migrations.AddField(
            model_name="actemedical",
            name="rdv_prerequisites",
            field=models.TextField(
                blank=True,
                help_text="Instructions patient avant le rendez-vous (à jeun, ordonnance, arrêt médicaments…). Inclus dans les rappels automatiques si configurés.",
                verbose_name="Prérequis / consignes RDV",
            ),
        ),
    ]
