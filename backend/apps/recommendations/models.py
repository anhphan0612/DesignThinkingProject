from django.conf import settings
from django.db import models


class RecommendationLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recommendation_logs")
    room = models.ForeignKey("listings.Room", on_delete=models.CASCADE, related_name="recommendation_logs")
    score = models.DecimalField(max_digits=8, decimal_places=6)
    rank = models.PositiveIntegerField()
    score_detail = models.JSONField(default=dict, blank=True)
    was_clicked = models.BooleanField(default=False)
    was_contacted = models.BooleanField(default=False)
    was_favorited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("rank", "-created_at")
        indexes = [
            models.Index(fields=("user", "-created_at"), name="rec_user_created_idx"),
            models.Index(fields=("room",), name="rec_room_idx"),
            models.Index(fields=("score",), name="rec_score_idx"),
        ]

