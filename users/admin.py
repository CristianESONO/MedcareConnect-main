from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PatientProfile


class PatientProfileInline(admin.StackedInline):
    model = PatientProfile
    can_delete = False
    verbose_name = "Profil Patient"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "user_type", "phone_number", "is_active", "date_joined")
    list_filter = ("user_type", "is_active", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name", "phone_number")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("MedCare", {"fields": ("user_type", "phone_number", "avatar", "slug")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("MedCare", {"fields": ("user_type", "phone_number")}),
    )
    prepopulated_fields = {"slug": ("username",)}

    def get_inlines(self, request, obj=None):
        if obj and obj.is_patient:
            return [PatientProfileInline]
        return []


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "city", "gender", "insurance", "date_of_birth")
    list_filter = ("city", "gender", "insurance")
    search_fields = ("user__username", "user__email", "city", "quartier")
    raw_id_fields = ("user", "insurance")
