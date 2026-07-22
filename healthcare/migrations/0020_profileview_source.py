from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("healthcare", "0019_prestataireacte_rdv_prerequisites"),
    ]

    operations = [
        migrations.AddField(
            model_name="profileview",
            name="source",
            field=models.CharField(
                choices=[
                    ("annuaire", "Annuaire"),
                    ("whatsapp", "WhatsApp"),
                    ("nfc", "MedPlaque NFC"),
                    ("qr", "MedPlaque QR"),
                ],
                db_index=True,
                default="annuaire",
                max_length=16,
            ),
        ),
    ]
