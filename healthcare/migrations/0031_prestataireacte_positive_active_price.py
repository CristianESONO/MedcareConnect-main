from django.db import migrations, models


def deactivate_zero_price_offers(apps, schema_editor):
    PrestataireActe = apps.get_model("healthcare", "PrestataireActe")
    PrestataireActe.objects.filter(
        is_available=True,
        price__lte=0,
    ).update(is_available=False)


class Migration(migrations.Migration):
    dependencies = [
        ("healthcare", "0030_alter_domicile_plages_horaires"),
    ]

    operations = [
        migrations.RunPython(
            deactivate_zero_price_offers,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="prestataireacte",
            constraint=models.CheckConstraint(
                condition=models.Q(is_available=False) | models.Q(price__gt=0),
                name="presta_acte_active_price_positive",
            ),
        ),
    ]
