from django.contrib import admin

from .models import Favorite, SearchLog, UserEvent


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "room", "created_at")
    search_fields = ("user__email", "room__title")


@admin.register(UserEvent)
class UserEventAdmin(admin.ModelAdmin):
    list_display = ("type", "user", "room", "session_key", "created_at")
    list_filter = ("type", "created_at")
    search_fields = ("user__email", "room__title", "session_key")


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ("user", "query_text", "result_count", "created_at")
    search_fields = ("user__email", "query_text", "session_key")

