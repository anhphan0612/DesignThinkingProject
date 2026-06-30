from rest_framework import serializers

from apps.listings.models import Room
from apps.listings.serializers import RoomReadSerializer

from .models import ChatMessage, ChatThread, ContactRequest, ContentReport, Favorite, SearchLog, UserEvent


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


class ContactRequestSerializer(serializers.ModelSerializer):
    requester_name = serializers.CharField(source="requester.full_name", read_only=True)
    recipient_name = serializers.CharField(source="recipient.full_name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    thread_id = serializers.IntegerField(source="chat_thread.id", read_only=True)

    class Meta:
        model = ContactRequest
        fields = (
            "id",
            "requester",
            "requester_name",
            "recipient",
            "recipient_name",
            "room",
            "roommate_post",
            "message",
            "status",
            "status_label",
            "thread_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "requester",
            "requester_name",
            "recipient",
            "recipient_name",
            "status",
            "status_label",
            "thread_id",
            "created_at",
            "updated_at",
        )


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.full_name", read_only=True)

    class Meta:
        model = ChatMessage
        fields = ("id", "thread", "sender", "sender_name", "body", "created_at")
        read_only_fields = ("id", "thread", "sender", "sender_name", "created_at")


class ChatThreadSerializer(serializers.ModelSerializer):
    requester_name = serializers.CharField(source="requester.full_name", read_only=True)
    recipient_name = serializers.CharField(source="recipient.full_name", read_only=True)
    messages = ChatMessageSerializer(many=True, read_only=True)
    current_user_id = serializers.SerializerMethodField()
    target_title = serializers.SerializerMethodField()
    latest_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatThread
        fields = (
            "id",
            "current_user_id",
            "target_title",
            "latest_message",
            "requester",
            "requester_name",
            "recipient",
            "recipient_name",
            "room",
            "roommate_post",
            "contact_request",
            "messages",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "current_user_id",
            "requester",
            "requester_name",
            "recipient",
            "recipient_name",
            "contact_request",
            "messages",
            "created_at",
            "updated_at",
        )

    def get_current_user_id(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return request.user.id
        return None

    def get_target_title(self, obj):
        if obj.room_id:
            return obj.room.title
        if obj.roommate_post_id:
            return obj.roommate_post.title
        return ""

    def get_latest_message(self, obj):
        message = obj.messages.order_by("-created_at").first()
        if not message:
            return ""
        return message.body


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
