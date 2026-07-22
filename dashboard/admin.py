from django.contrib import admin

from .models import ComplianceChecklistSettings


@admin.register(ComplianceChecklistSettings)
class ComplianceChecklistSettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "updated_at")

    def has_add_permission(self, request):
        return not ComplianceChecklistSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
