import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0004_rdv_reminder_schedules"),
        ("healthcare", "0018_actemedical_rdv_prerequisites"),
    ]

    operations = [
        migrations.AddField(
            model_name="rdvreminderschedule",
            name="organisme",
            field=models.ForeignKey(
                blank=True,
                help_text="Vide = règle plateforme (admin). Renseigné = règle propre à la structure.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="rdv_reminder_schedules",
                to="healthcare.organismedesante",
            ),
        ),
    ]
