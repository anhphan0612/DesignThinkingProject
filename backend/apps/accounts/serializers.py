from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from apps.locations.models import District, University
from apps.roommates.models import LifestyleTag

from .models import LandlordProfile, StudentProfile, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "full_name", "phone", "role", "avatar")
        read_only_fields = ("id", "role")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("id", "email", "password", "full_name", "phone", "role")
        read_only_fields = ("id",)

    def validate_role(self, value):
        if value == User.Role.ADMIN:
            raise serializers.ValidationError("Admin accounts cannot be registered publicly.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        if user.role == User.Role.STUDENT:
            StudentProfile.objects.create(user=user)
        elif user.role == User.Role.LANDLORD:
            LandlordProfile.objects.create(user=user)
        return user


class StudentProfileSerializer(serializers.ModelSerializer):
    university = serializers.PrimaryKeyRelatedField(
        queryset=University.objects.filter(is_active=True),
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
    university_name = serializers.CharField(source="university.name", read_only=True)
    preferred_district_names = serializers.SerializerMethodField()
    lifestyle_tag_names = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = (
            "university",
            "university_name",
            "student_code",
            "budget_min",
            "budget_max",
            "max_distance_km",
            "gender",
            "move_in_date",
            "preferred_districts",
            "preferred_district_names",
            "lifestyle_tags",
            "lifestyle_tag_names",
        )

    def get_preferred_district_names(self, obj):
        return [district.name for district in obj.preferred_districts.all()]

    def get_lifestyle_tag_names(self, obj):
        return [tag.name for tag in obj.lifestyle_tags.all()]


class LandlordProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandlordProfile
        fields = ("business_name", "verification_status", "verified_at")
        read_only_fields = ("verification_status", "verified_at")


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            email=attrs["email"],
            password=attrs["password"],
        )
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")
        token, _ = Token.objects.get_or_create(user=user)
        attrs["token"] = token
        attrs["user"] = user
        return attrs
