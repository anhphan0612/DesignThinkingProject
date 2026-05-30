from django.contrib.gis.geos import Point
from rest_framework import serializers

from apps.accounts.models import LandlordProfile, User
from apps.locations.models import Ward

from .models import Amenity, Room, RoomImage
from .services import require_reapproval_after_edit


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ("id", "name", "code")


class RoomImageSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.full_name", read_only=True)
    source_label = serializers.CharField(source="get_source_display", read_only=True)

    class Meta:
        model = RoomImage
        fields = (
            "id",
            "room",
            "image",
            "caption",
            "is_cover",
            "sort_order",
            "source",
            "source_label",
            "status",
            "uploaded_by_name",
            "created_at",
        )
        read_only_fields = ("id", "source", "source_label", "status", "uploaded_by_name", "created_at")

    def validate_room(self, room):
        user = self.context["request"].user
        if user.is_staff:
            return room
        if hasattr(user, "landlord_profile") and room.landlord_id == user.landlord_profile.id:
            return room
        if room.status == Room.Status.ACTIVE:
            return room
        raise serializers.ValidationError("You cannot add an image to this room.")
        return room

    def validate(self, attrs):
        room = attrs.get("room", getattr(self.instance, "room", None))
        is_cover = attrs.get("is_cover", getattr(self.instance, "is_cover", False))
        user = self.context["request"].user
        if is_cover and not (
            user.is_staff
            or (room and hasattr(user, "landlord_profile") and room.landlord_id == user.landlord_profile.id)
        ):
            raise serializers.ValidationError("Only the landlord or admin can set a cover image.")
        if room and is_cover:
            covers = RoomImage.objects.filter(
                room=room,
                is_cover=True,
                status=RoomImage.ModerationStatus.APPROVED,
            )
            if self.instance:
                covers = covers.exclude(pk=self.instance.pk)
            if covers.exists():
                raise serializers.ValidationError("This room already has a cover image.")
        return attrs


class RoomReadSerializer(serializers.ModelSerializer):
    landlord_name = serializers.CharField(source="landlord.user.full_name", read_only=True)
    ward_name = serializers.CharField(source="ward.name", read_only=True)
    district_name = serializers.CharField(source="ward.district.name", read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)
    images = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = (
            "id",
            "title",
            "description",
            "landlord_name",
            "ward",
            "ward_name",
            "district_name",
            "address",
            "latitude",
            "longitude",
            "price",
            "deposit",
            "area",
            "max_occupants",
            "gender_policy",
            "electricity_price",
            "water_price",
            "amenities",
            "images",
            "status",
            "rejection_reason",
            "distance_km",
            "created_at",
        )

    def get_latitude(self, obj):
        return obj.location.y

    def get_longitude(self, obj):
        return obj.location.x

    def get_distance_km(self, obj):
        distance = getattr(obj, "distance", None)
        return round(distance.km, 2) if distance else None

    def get_images(self, obj):
        images = obj.images.filter(status=RoomImage.ModerationStatus.APPROVED).select_related("uploaded_by")
        return RoomImageSerializer(images, many=True, context=self.context).data


class RoomWriteSerializer(serializers.ModelSerializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, write_only=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, write_only=True)
    amenities = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Amenity.objects.all(),
        required=False,
    )

    class Meta:
        model = Room
        fields = (
            "id",
            "ward",
            "title",
            "description",
            "address",
            "latitude",
            "longitude",
            "price",
            "deposit",
            "area",
            "max_occupants",
            "gender_policy",
            "electricity_price",
            "water_price",
            "amenities",
            "status",
        )
        read_only_fields = ("id", "status")

    def validate(self, attrs):
        user = self.context["request"].user
        has_latitude = "latitude" in attrs
        has_longitude = "longitude" in attrs
        if has_latitude != has_longitude:
            raise serializers.ValidationError("Latitude and longitude must be provided together.")
        if self.instance is None:
            if user.role != User.Role.LANDLORD or not hasattr(user, "landlord_profile"):
                raise serializers.ValidationError("Only landlords can create rooms.")
            if user.landlord_profile.verification_status != LandlordProfile.VerificationStatus.APPROVED:
                raise serializers.ValidationError("The landlord account must be verified first.")
        return attrs

    def create(self, validated_data):
        amenities = validated_data.pop("amenities", [])
        latitude = validated_data.pop("latitude")
        longitude = validated_data.pop("longitude")
        room = Room.objects.create(
            landlord=self.context["request"].user.landlord_profile,
            location=Point(float(longitude), float(latitude), srid=4326),
            **validated_data,
        )
        room.amenities.set(amenities)
        return room

    def update(self, instance, validated_data):
        was_active = instance.status == Room.Status.ACTIVE
        amenities = validated_data.pop("amenities", None)
        latitude = validated_data.pop("latitude", None)
        longitude = validated_data.pop("longitude", None)
        if latitude is not None and longitude is not None:
            validated_data["location"] = Point(float(longitude), float(latitude), srid=4326)
        instance = super().update(instance, validated_data)
        if amenities is not None:
            instance.amenities.set(amenities)
        if was_active:
            require_reapproval_after_edit(room=instance)
        return instance


class RejectRoomSerializer(serializers.Serializer):
    reason = serializers.CharField()
