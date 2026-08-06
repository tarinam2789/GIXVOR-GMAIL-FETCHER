from django.contrib import admin

from .models import CachedEmail, SearchQuery


class CachedEmailInline(admin.TabularInline):
    model = CachedEmail
    extra = 0
    fields = ("subject", "from_address", "received_at", "has_attachments")
    readonly_fields = fields
    can_delete = False


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ("sender_email", "gmail_address", "mailbox", "result_count", "succeeded", "created_at")
    list_filter = ("succeeded", "mailbox")
    search_fields = ("sender_email", "gmail_address")
    inlines = [CachedEmailInline]


@admin.register(CachedEmail)
class CachedEmailAdmin(admin.ModelAdmin):
    list_display = ("subject", "from_address", "query", "received_at", "has_attachments")
    search_fields = ("subject", "from_address", "body_text")
    list_filter = ("has_attachments",)
