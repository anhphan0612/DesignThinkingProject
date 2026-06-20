from django.conf import settings
from django.db import models


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    room = models.ForeignKey("listings.Room", on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("user", "room"), name="unique_user_room_favorite")
        ]

    def __str__(self):
        return f"{self.user_id} -> {self.room_id}"


class UserEvent(models.Model):
    class Type(models.TextChoices):
        VIEW_ROOM = "view_room", "View room"
        CLICK_CONTACT = "click_contact", "Click contact"
        FAVORITE_ADD = "favorite_add", "Favorite add"
        FAVORITE_REMOVE = "favorite_remove", "Favorite remove"
        SEARCH = "search", "Search"
        RECOMMENDATION_VIEW = "recommendation_view", "Recommendation view"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    session_key = models.CharField(max_length=80, blank=True)
    type = models.CharField(max_length=40, choices=Type.choices)
    room = models.ForeignKey(
        "listings.Room",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("user", "-created_at"), name="event_user_created_idx"),
            models.Index(fields=("room", "type"), name="event_room_type_idx"),
            models.Index(fields=("session_key",), name="event_session_idx"),
        ]


class SearchLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="search_logs",
    )
    session_key = models.CharField(max_length=80, blank=True)
    query_text = models.TextField(blank=True)
    filters = models.JSONField(default=dict, blank=True)
    result_ids = models.JSONField(default=list, blank=True)
    result_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("user", "-created_at"), name="search_user_created_idx"),
            models.Index(fields=("session_key",), name="search_session_idx"),
        ]


class ContentReport(models.Model):
    class TargetType(models.TextChoices):
        ROOM = "room", "Phòng"
        ROOM_IMAGE = "room_image", "Ảnh phòng"
        ROOMMATE_POST = "roommate_post", "Bài ghép trọ"

    class Status(models.TextChoices):
        OPEN = "open", "Đang mở"
        RESOLVED = "resolved", "Đã xử lý"
        DISMISSED = "dismissed", "Bỏ qua"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="content_reports",
    )
    session_key = models.CharField(max_length=80, blank=True)
    target_type = models.CharField(max_length=30, choices=TargetType.choices)
    room = models.ForeignKey(
        "listings.Room",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports",
    )
    room_image = models.ForeignKey(
        "listings.RoomImage",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports",
    )
    roommate_post = models.ForeignKey(
        "roommates.RoommatePost",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports",
    )
    reason = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_content_reports",
    )
    handled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("target_type", "status"), name="report_target_status_idx"),
            models.Index(fields=("reporter", "-created_at"), name="report_reporter_created_idx"),
        ]

    def __str__(self):
        return f"{self.target_type}: {self.reason}"

    @property
    def target_label(self):
        if self.room_id:
            return self.room.title
        if self.room_image_id:
            return self.room_image.caption or self.room_image.room.title
        if self.roommate_post_id:
            return self.roommate_post.title
        return ""

