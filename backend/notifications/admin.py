from django.contrib import admin

from .models import (
    NotificationChannel,
    NotificationEvent,
    NotificationLog,
    NotificationRule,
    NotificationSettings,
    NotificationTemplate,
    UserNotificationPreference,
)


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Email / SMTP", {
            "fields": (
                "email_enabled",
                ("smtp_host", "smtp_port"),
                ("smtp_user", "smtp_password"),
                ("smtp_use_tls", "smtp_use_ssl"),
                ("smtp_from_email", "smtp_from_name"),
                "smtp_reply_to",
            ),
        }),
        ("WhatsApp Cloud API", {
            "fields": (
                "whatsapp_enabled",
                "wa_phone_number_id",
                "wa_business_account_id",
                "wa_access_token",
                "wa_api_version",
            ),
        }),
        ("Général", {
            "fields": ("in_app_enabled", "log_retention_days", "google_reviews_url"),
        }),
        ("Textes patient — liens WhatsApp (wa.me)", {
            "classes": ("collapse",),
            "fields": (
                "patient_wa_me_message_general",
                "patient_wa_me_message_acte",
                "patient_wa_me_message_devis_formal",
            ),
        }),
    )

    def has_add_permission(self, request):
        return not NotificationSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class NotificationTemplateInline(admin.StackedInline):
    model = NotificationTemplate
    extra = 0
    fields = ("channel", "subject", "body", "is_enabled")
    autocomplete_fields = ("channel",)


class NotificationRuleInline(admin.TabularInline):
    model = NotificationRule
    extra = 0
    fields = ("channel", "target_roles", "notify_event_actor", "extra_emails", "is_active")
    autocomplete_fields = ("channel",)


@admin.register(NotificationEvent)
class NotificationEventAdmin(admin.ModelAdmin):
    list_display = ("label", "code", "audience", "is_enabled", "order")
    list_filter = ("audience", "is_enabled")
    search_fields = ("code", "label", "description")
    inlines = [NotificationTemplateInline, NotificationRuleInline]


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ("label", "code", "is_enabled", "requires_external_config", "order")
    list_filter = ("is_enabled", "requires_external_config")
    search_fields = ("code", "label")


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("event", "channel", "is_enabled", "updated_at")
    list_filter = ("channel", "is_enabled")
    search_fields = ("event__code", "event__label", "subject", "body")
    autocomplete_fields = ("event", "channel")


@admin.register(NotificationRule)
class NotificationRuleAdmin(admin.ModelAdmin):
    list_display = ("event", "channel", "is_active", "notify_event_actor", "updated_at")
    list_filter = ("channel", "is_active", "notify_event_actor")
    search_fields = ("event__code", "event__label", "extra_emails", "note")
    autocomplete_fields = ("event", "channel", "target_users")
    filter_horizontal = ("target_users",)


@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "channel", "enabled", "updated_at")
    list_filter = ("channel", "event", "enabled")
    autocomplete_fields = ("user", "event", "channel")
    search_fields = ("user__username", "user__email")


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "event", "channel", "status", "recipient_user", "recipient_address")
    list_filter = ("status", "channel", "event")
    date_hierarchy = "created_at"
    search_fields = ("recipient_address", "recipient_user__username", "subject", "body", "error")
    readonly_fields = (
        "event",
        "channel",
        "recipient_user",
        "recipient_address",
        "subject",
        "body",
        "status",
        "error",
        "context_snapshot",
        "created_at",
        "sent_at",
    )

    def has_add_permission(self, request):
        return False
