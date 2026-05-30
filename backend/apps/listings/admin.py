from django.contrib.gis import admin

from .models import Amenity, Room, RoomImage


admin.site.register(Amenity)
admin.site.register(Room, admin.GISModelAdmin)
@admin.register(RoomImage)
class RoomImageAdmin(admin.ModelAdmin):
    list_display = ("room", "source", "status", "is_cover", "uploaded_by", "created_at")
    list_filter = ("source", "status", "is_cover", "created_at")
    search_fields = ("room__title", "uploaded_by__email", "caption")
