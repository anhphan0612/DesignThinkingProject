from rest_framework import serializers

from apps.listings.models import Room
from apps.listings.serializers import RoomReadSerializer

from .models import ContentReport, Favorite, SearchLog, UserEvent


class FavoriteSerializer(serializers.ModelSerializer):
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.filter(status=Room.Status.ACTIVE))
    room_detail = RoomReadSerializer(source="room", read_only=True)

    class Meta:
        model = Favorite
        fields = ("id", "room", "room_detail", "created_at")
        read_only_fields = ("id", "created_at")

    def create(self, validated_data):
        favorite, _ = Favorite.objects.get_or_create(
            user=self.context["request"].user,
            room=validated_data["room"],
        )
        return favorite


class UserEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserEvent
        fields = ("id", "type", "room", "metadata", "created_at")
        read_only_fields = ("id", "created_at")


class SearchLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchLog
        fields = ("id", "query_text", "filters", "result_ids", "result_count", "created_at")
        read_only_fields = ("id", "created_at")


class ContentReportSerializer(serializers.ModelSerializer):
    target_label = serializers.SerializerMethodField()

    class Meta:
        model = ContentReport
        fields = (
            "id",
            "target_type",
            "room",
            "room_image",
            "roommate_post",
            "reason",
            "details",
            "status",
            "target_label",
            "created_at",
        )
        read_only_fields = ("id", "status", "target_label", "created_at")

    def validate(self, attrs):
        target_type = attrs.get("target_type")
        target_fields = {
            ContentReport.TargetType.ROOM: "room",
            ContentReport.TargetType.ROOM_IMAGE: "room_image",
            ContentReport.TargetType.ROOMMATE_POST: "roommate_post",
        }
        expected = target_fields.get(target_type)
        if not expected or not attrs.get(expected):
            raise serializers.ValidationError({expected or "target_type": "Target is required."})
        for field in target_fields.values():
            if field != expected and attrs.get(field):
                raise serializers.ValidationError(field + " must be empty for this target type.")
        return attrs

    def get_target_label(self, obj):
        if obj.room:
            return obj.room.title
        if obj.room_image:
            return obj.room_image.caption or obj.room_image.room.title
        if obj.roommate_post:
            return obj.roommate_post.title
        return ""

