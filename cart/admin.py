from django.contrib import admin
from .models import Cart, CartItem, Devis, DevisPart


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    raw_id_fields = ("prestataire_acte",)
    readonly_fields = ("added_at",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("patient", "name", "status", "item_count", "selected_insurance", "updated_at")
    list_filter = ("status",)
    search_fields = ("patient__username", "name")
    raw_id_fields = ("patient", "selected_insurance")
    readonly_fields = ("created_at", "updated_at")
    inlines = [CartItemInline]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "prestataire_acte", "quantity", "added_at")
    raw_id_fields = ("cart", "prestataire_acte")


class DevisPartInline(admin.TabularInline):
    model = DevisPart
    extra = 0
    readonly_fields = ("reference", "organisme", "total_brut", "total_patient", "status", "created_at")
    can_delete = False


@admin.register(Devis)
class DevisAdmin(admin.ModelAdmin):
    list_display = ("reference", "patient", "insurance", "total_brut", "total_patient", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("reference", "patient__username")
    raw_id_fields = ("patient", "cart", "insurance")
    readonly_fields = ("reference", "created_at")
    inlines = [DevisPartInline]


@admin.register(DevisPart)
class DevisPartAdmin(admin.ModelAdmin):
    list_display = ("reference", "devis", "organisme", "total_brut", "total_patient", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("reference", "devis__reference", "organisme__name")
    raw_id_fields = ("devis", "organisme")
    readonly_fields = ("reference", "created_at")
