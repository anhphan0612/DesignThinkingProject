from rest_framework import serializers

from apps.listings.serializers import RoomReadSerializer


class RecommendationSerializer(serializers.Serializer):
    room = RoomReadSerializer()
    score = serializers.FloatField()
    rank = serializers.IntegerField()
    score_detail = serializers.JSONField()

