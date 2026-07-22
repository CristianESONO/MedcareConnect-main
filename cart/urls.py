from django.urls import path
from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_view, name="cart_view"),
    path("guest/", views.cart_view, name="guest_cart"),
    path("api/guest-preview/", views.guest_cart_preview, name="guest_cart_preview"),
    path("api/snapshot/", views.cart_snapshot, name="cart_snapshot"),
    path("api/merge-guest/", views.cart_merge_guest, name="cart_merge_guest"),
    path("add/<int:pk>/", views.cart_add, name="cart_add"),
    path("add-bundle/", views.cart_add_bundle, name="cart_add_bundle"),
    path("fiche-devis/", views.cart_fiche_request_devis, name="cart_fiche_request_devis"),
    path("remove-pa/<int:pa_id>/", views.cart_remove_pa, name="cart_remove_pa"),
    path("guest/remove/<int:pa_id>/", views.guest_cart_remove, name="guest_cart_remove"),
    path("guest/update/<int:pa_id>/", views.guest_cart_update_quantity, name="guest_cart_update_quantity"),
    path("guest/insurance/", views.guest_cart_select_insurance, name="guest_cart_select_insurance"),
    path("guest/clear/", views.guest_cart_clear, name="guest_cart_clear"),
    path("remove/<int:pk>/", views.cart_remove, name="cart_remove"),
    path("update/<int:pk>/", views.cart_update_quantity, name="cart_update_quantity"),
    path("insurance/", views.cart_select_insurance, name="cart_select_insurance"),
    path("clear/", views.cart_clear, name="cart_clear"),
    path("devis/generate/", views.generate_devis, name="generate_devis"),
    path("devis/", views.devis_list, name="devis_list"),
    path("devis/<str:ref>/", views.devis_detail, name="devis_detail"),
    path("history/", views.cart_history, name="cart_history"),
]
