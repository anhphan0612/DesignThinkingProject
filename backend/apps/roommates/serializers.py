from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.models import User
from apps.listings.serializers import RoomReadSerializer
from apps.locations.models import District, University, Ward
from apps.locations.serializers import DistrictSerializer

from .models import LifestyleTag, RoommatePost


class LifestyleTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = LifestyleTag
        fields = ("id", "name", "code")


class RoommatePostReadSerializer(serializers.ModelSerializer):
    posted_by_name = serializers.CharField(source="posted_by.full_name", read_only=True)
    university_name = serializers.CharField(source="university.name", read_only=True)
    ward_name = serializers.CharField(source="ward.name", read_only=True)
    district_name = serializers.CharField(source="ward.district.name", read_only=True)
    preferred_districts = DistrictSerializer(many=True, read_only=True)
    lifestyle_tags = LifestyleTagSerializer(many=True, read_only=True)
    room = RoomReadSerializer(read_only=True)
    type_label = serializers.CharField(source="get_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    gender_preference_label = serializers.CharField(source="get_gender_preference_display", read_only=True)
    match = serializers.SerializerMethodField()

    class Meta:
        model = RoommatePost
        fields = (
            "id",
            "posted_by_name",
            "type",
            "type_label",
            "status",
            "status_label",
            "title",
            "description",
            "university",
            "university_name",
            "preferred_districts",
            "ward",
            "ward_name",
            "district_name",
            "room",
            "address",
            "budget_min",
            "budget_max",
            "move_in_date",
            "gender_preference",
            "gender_preference_label",
            "max_roommates",
            "current_occupants",
            "available_slots",
            "lifestyle_tags",
            "contact_phone",
            "match",
            "created_at",
            "updated_at",
        )

    def get_match(self, obj):
        return getattr(obj, "match", None)


class RoommatePostWriteSerializer(serializers.ModelSerializer):
    university = serializers.PrimaryKeyRelatedField(
        queryset=University.objects.filter(is_active=True),
        allow_null=True,
        required=False,
    )
    ward = serializers.PrimaryKeyRelatedField(
        queryset=Ward.objects.select_related("district"),
        allow_null=True,
        required=False,
    )
    preferred_districts = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=District.objects.all(),
        required=False,
    )
    lifestyle_tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=LifestyleTag.objects.all(),
        required=False,
    )

    class Meta:
        model = RoommatePost
        fields = (
            "id",
            "type",
            "title",
            "description",
            "university",
            "preferred_districts",
            "ward",
            "room",
            "address",
            "budget_min",
            "budget_max",
            "move_in_date",
            "gender_preference",
            "max_roommates",
            "current_occupants",
            "available_slots",
            "lifestyle_tags",
            "contact_phone",
            "status",
        )
        read_only_fields = ("id", "status")

    def validate(self, attrs):
        user = self.context["request"].user
        if user.role != User.Role.STUDENT:
            raise serializers.ValidationError("Only student accounts can create roommate posts.")
        return attrs

    def create(self, validated_data):
        preferred_districts = validated_data.pop("preferred_districts", [])
        lifestyle_tags = validated_data.pop("lifestyle_tags", [])
        post = RoommatePost(
            posted_by=self.context["request"].user,
            status=RoommatePost.Status.ACTIVE,
            **validated_data,
        )
        try:
            post.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        post.save()
        post.preferred_districts.set(preferred_districts)
        post.lifestyle_tags.set(lifestyle_tags)
        return post

    def update(self, instance, validated_data):
        preferred_districts = validated_data.pop("preferred_districts", None)
        lifestyle_tags = validated_data.pop("lifestyle_tags", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        instance.save()
        if preferred_districts is not None:
            instance.preferred_districts.set(preferred_districts)
        if lifestyle_tags is not None:
            instance.lifestyle_tags.set(lifestyle_tags)
        return instance
