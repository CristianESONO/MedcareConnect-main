"""
Parcours e-commerce simplifié : conversion panier → devis + notification devis.created.
"""

import pytest
from django.urls import reverse

from cart.models import CartItem, Devis, DevisPart
from notifications.models import NotificationEvent, NotificationLog


@pytest.mark.django_db
def test_generer_devis_depuis_panier_cree_devis_et_log(
    client, patient_user, cart_avec_ligne,
):
    ev = NotificationEvent.objects.get(code="devis.created")
    n0 = NotificationLog.objects.filter(event=ev).count()

    client.force_login(patient_user)
    item = CartItem.objects.get(cart=cart_avec_ligne)
    url = reverse("cart:generate_devis") + f"?item={item.pk}"
    r = client.get(url, follow=False)
    assert r.status_code == 302

    devis = Devis.objects.get(patient=patient_user)
    assert devis.status == "sent"
    assert DevisPart.objects.filter(devis=devis).count() == 1
    assert NotificationLog.objects.filter(event=ev).count() == n0 + 1

    cart_avec_ligne.refresh_from_db()
    assert cart_avec_ligne.status == "converted"
