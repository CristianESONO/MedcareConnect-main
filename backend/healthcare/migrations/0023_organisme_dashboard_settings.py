from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("healthcare", "0022_organisme_domicile_params"),
    ]

    operations = [
        migrations.AddField(
            model_name="organismedesante",
            name="dashboard_team",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Invitations / accès dashboard (nom, email, rôle, statut).",
            ),
        ),
        migrations.AddField(
            model_name="organismedesante",
            name="settings_currency",
            field=models.CharField(
                choices=[
                    ("XOF", "FCFA (XOF)"),
                    ("EUR", "EUR (€)"),
                    ("USD", "USD ($)"),
                ],
                default="XOF",
                max_length=5,
                verbose_name="Devise d'affichage",
            ),
        ),
        migrations.AddField(
            model_name="organismedesante",
            name="settings_dashboard_period",
            field=models.CharField(
                choices=[
                    ("7j", "7 jours"),
                    ("30j", "30 jours"),
                    ("total", "Depuis M0 (total)"),
                ],
                default="30j",
                max_length=10,
                verbose_name="Période par défaut du dashboard",
            ),
        ),
        migrations.AddField(
            model_name="organismedesante",
            name="settings_locale",
            field=models.CharField(
                choices=[
                    ("fr", "Français"),
                    ("wo", "Wolof"),
                    ("en", "English"),
                ],
                default="fr",
                max_length=5,
                verbose_name="Langue du dashboard",
            ),
        ),
        migrations.AddField(
            model_name="organismedesante",
            name="show_prices_on_public_profile",
            field=models.BooleanField(
                default=True,
                verbose_name="Afficher les tarifs sur le profil public",
            ),
        ),
    ]
