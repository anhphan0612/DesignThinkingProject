from rest_framework import serializers

from apps.listings.models import Room
from apps.listings.serializers import RoomReadSerializer

from .models import Favorite, SearchLog, UserEvent


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

