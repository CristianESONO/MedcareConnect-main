from django.contrib import admin

from .models import RdvReminderSchedule, RendezVous, RendezVousReminderLog


class RendezVousReminderLogInline(admin.TabularInline):
    model = RendezVousReminderLog
    extra = 0
    readonly_fields = ("schedule", "sent_at")
    can_delete = False


@admin.register(RendezVous)
class RendezVousAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "organisme",
        "patient",
        "start",
        "status",
        "total_patient",
        "created_at",
    )
    list_filter = ("status", "organisme")
    search_fields = (
        "reference",
        "organisme__name",
        "patient__username",
        "patient__email",
        "devis__reference",
        "devis_part__reference",
    )
    date_hierarchy = "start"
    autocomplete_fields = ("patient", "organisme", "devis", "devis_part")
    readonly_fields = ("reference", "created_at", "updated_at", "confirmed_at", "reminder_sent_at")
    inlines = [RendezVousReminderLogInline]


@admin.register(RdvReminderSchedule)
class RdvReminderScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "label",
        "offset_value",
        "offset_unit",
        "tolerance_minutes",
        "include_prerequisites",
        "is_active",
        "order",
    )
    list_filter = ("is_active", "offset_unit", "include_prerequisites")
    search_fields = ("label",)
    filter_horizontal = ("actes",)
    ordering = ("order", "-offset_value")


@admin.register(RendezVousReminderLog)
class RendezVousReminderLogAdmin(admin.ModelAdmin):
    list_display = ("rendez_vous", "schedule", "sent_at")
    list_filter = ("schedule",)
    search_fields = ("rendez_vous__reference",)
    readonly_fields = ("rendez_vous", "schedule", "sent_at")

    def has_add_permission(self, request):
        return False
