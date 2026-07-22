from django.contrib import admin
from .models import Conversation, Message, Notification


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("timestamp",)
    fields = ("sender", "receiver", "content", "message_type", "is_read", "timestamp")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("patient", "prestataire", "subject", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("patient__username", "prestataire__username", "subject")
    raw_id_fields = ("patient", "prestataire", "related_cart")
    readonly_fields = ("created_at", "updated_at")
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "message_type", "is_read", "timestamp")
    list_filter = ("message_type", "is_read")
    search_fields = ("sender__username", "receiver__username", "content")
    raw_id_fields = ("sender", "receiver", "conversation")
    readonly_fields = ("timestamp", "read_at")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "notification_type", "title", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")
    search_fields = ("user__username", "title", "content")
    raw_id_fields = ("user",)
    readonly_fields = ("created_at",)
