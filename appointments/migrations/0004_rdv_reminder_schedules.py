from django.db import migrations, models


DEFAULT_SCHEDULES = [
    (10, "3 jours avant", 3, "days", 60),
    (20, "Veille du RDV (J-1)", 1, "days", 30),
    (30, "30 minutes avant", 30, "minutes", 15),
]


def seed_default_schedules(apps, schema_editor):
    Schedule = apps.get_model("appointments", "RdvReminderSchedule")
    for order, label, value, unit, tolerance in DEFAULT_SCHEDULES:
        Schedule.objects.get_or_create(
            label=label,
            defaults={
                "offset_value": value,
                "offset_unit": unit,
                "tolerance_minutes": tolerance,
                "include_prerequisites": True,
                "is_active": True,
                "order": order,
            },
        )


def unseed_default_schedules(apps, schema_editor):
    Schedule = apps.get_model("appointments", "RdvReminderSchedule")
    Schedule.objects.filter(label__in=[s[1] for s in DEFAULT_SCHEDULES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("healthcare", "0018_actemedical_rdv_prerequisites"),
        ("appointments", "0003_rendezvous_source_rendezvous_walk_in_motif_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="RdvReminderSchedule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(help_text="Libellé affiché en admin (ex. « Veille du RDV », « 30 min avant »).", max_length=80)),
                ("offset_value", models.PositiveIntegerField(default=1, help_text="Valeur numérique (ex. 1 jour, 3 jours, 30 minutes).")),
                ("offset_unit", models.CharField(choices=[("minutes", "Minutes avant"), ("hours", "Heures avant"), ("days", "Jours avant")], default="days", max_length=10)),
                ("tolerance_minutes", models.PositiveSmallIntegerField(default=30, help_text="Fenêtre cron ± minutes autour de l'heure cible d'envoi.")),
                ("include_prerequisites", models.BooleanField(default=True, help_text="Ajoute les consignes configurées sur chaque acte du RDV.", verbose_name="Inclure les prérequis des actes")),
                ("is_active", models.BooleanField(default=True)),
                ("order", models.PositiveIntegerField(default=0)),
                ("actes", models.ManyToManyField(blank=True, help_text="Vide = tous les RDV confirmés. Sinon, uniquement si le RDV contient au moins un de ces actes.", related_name="rdv_reminder_schedules", to="healthcare.actemedical", verbose_name="Actes concernés")),
            ],
            options={
                "verbose_name": "Règle de rappel RDV",
                "verbose_name_plural": "Règles de rappel RDV",
                "ordering": ["order", "-offset_value"],
            },
        ),
        migrations.CreateModel(
            name="RendezVousReminderLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sent_at", models.DateTimeField(auto_now_add=True)),
                ("rendez_vous", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="reminder_logs", to="appointments.rendezvous")),
                ("schedule", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="sent_logs", to="appointments.rdvreminderschedule")),
            ],
            options={
                "verbose_name": "Rappel RDV envoyé",
                "verbose_name_plural": "Rappels RDV envoyés",
            },
        ),
        migrations.AddConstraint(
            model_name="rendezvousreminderlog",
            constraint=models.UniqueConstraint(fields=("rendez_vous", "schedule"), name="uniq_rdv_reminder_per_schedule"),
        ),
        migrations.RunPython(seed_default_schedules, unseed_default_schedules),
    ]
