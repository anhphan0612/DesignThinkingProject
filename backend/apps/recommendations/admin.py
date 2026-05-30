from django.contrib import admin

from .models import RecommendationLog


@admin.register(RecommendationLog)
class RecommendationLogAdmin(admin.ModelAdmin):
    list_display = ("user", "room", "score", "rank", "was_clicked", "was_contacted", "was_favorited", "created_at")
    list_filter = ("was_clicked", "was_contacted", "was_favorited", "created_at")
    search_fields = ("user__email", "room__title")

