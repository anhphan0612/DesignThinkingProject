from django.contrib import admin

from .models import LifestyleTag, RoommatePost


@admin.register(LifestyleTag)
class LifestyleTagAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")
    prepopulated_fields = {"code": ("name",)}


@admin.register(RoommatePost)
class RoommatePostAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "posted_by",
        "type",
        "status",
        "university",
        "budget_min",
        "budget_max",
        "move_in_date",
        "created_at",
    )
    list_filter = ("type", "status", "gender_preference", "university", "created_at")
    search_fields = ("title", "description", "posted_by__email", "posted_by__full_name")
    raw_id_fields = ("posted_by", "university", "room", "ward")
    filter_horizontal = ("preferred_districts", "lifestyle_tags")
    readonly_fields = ("created_at", "updated_at", "closed_at")
