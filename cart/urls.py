from django.urls import path
from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_view, name="cart_view"),
    path("invite/", views.cart_view, name="guest_cart"),
    path("api/apercu-invite/", views.guest_cart_preview, name="guest_cart_preview"),
    path("api/snapshot/", views.cart_snapshot, name="cart_snapshot"),
    path("api/fusion-invite/", views.cart_merge_guest, name="cart_merge_guest"),
    path("ajouter/<int:pk>/", views.cart_add, name="cart_add"),
    path("ajouter-formule/", views.cart_add_bundle, name="cart_add_bundle"),
    path("fiche-devis/", views.cart_fiche_request_devis, name="cart_fiche_request_devis"),
    path("ambulance-trajet-devis/", views.ambulance_trajet_devis, name="ambulance_trajet_devis"),
    path("supprimer-pa/<int:pa_id>/", views.cart_remove_pa, name="cart_remove_pa"),
    path("invite/supprimer/<int:pa_id>/", views.guest_cart_remove, name="guest_cart_remove"),
    path("invite/modifier/<int:pa_id>/", views.guest_cart_update_quantity, name="guest_cart_update_quantity"),
    path("invite/assurance/", views.guest_cart_select_insurance, name="guest_cart_select_insurance"),
    path("invite/vider/", views.guest_cart_clear, name="guest_cart_clear"),
    path("supprimer/<int:pk>/", views.cart_remove, name="cart_remove"),
    path("modifier/<int:pk>/", views.cart_update_quantity, name="cart_update_quantity"),
    path("assurance/", views.cart_select_insurance, name="cart_select_insurance"),
    path("vider/", views.cart_clear, name="cart_clear"),
    path("devis/generer/", views.generate_devis, name="generate_devis"),
    path("devis/", views.devis_list, name="devis_list"),
    path("devis/<str:ref>/", views.devis_detail, name="devis_detail"),
    path("historique/", views.cart_history, name="cart_history"),
]
