from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="notificationsettings",
            name="patient_wa_me_message_acte",
            field=models.TextField(
                default=(
                    "Bonjour, je vous contacte via MedCare Connect. "
                    "Je souhaite réserver un rendez-vous pour l'examen « {{ acte.name }} » "
                    "(établissement « {{ org.name }} »)."
                ),
                help_text=(
                    "Lien WhatsApp à côté de chaque acte. Variables : {{ acte.name }}, {{ org.name }}."
                ),
                verbose_name="Message WhatsApp (par examen)",
            ),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="patient_wa_me_message_general",
            field=models.TextField(
                default=(
                    "Bonjour, je vous contacte via MedCare Connect. "
                    "Je souhaite réserver un rendez-vous pour un examen."
                ),
                help_text=(
                    "Bouton principal sur la fiche prestataire. Syntaxe Django : "
                    "{{ org.name }} (nom de l'établissement)."
                ),
                verbose_name="Message WhatsApp (contact général)",
            ),
        ),
    ]
