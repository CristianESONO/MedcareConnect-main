from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cart", "0005_devispart"),
    ]

    operations = [
        migrations.AddField(
            model_name="cart",
            name="insurance_user_override",
            field=models.BooleanField(
                default=False,
                help_text="Le patient a choisi manuellement l'assurance (ou « sans assurance ») sur le chariot.",
            ),
        ),
    ]
