from django.contrib.gis.geos import Point
from django.conf import settings
from rest_framework import serializers

from apps.accounts.models import User
from apps.interactions.models import Favorite
from apps.locations.geocoding import GeocodingError, geocode_room_address
from apps.locations.models import Ward

from .models import Amenity, Room, RoomImage
from .services import require_reapproval_after_edit
from .validators import validate_room_image_upload


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

    def validate_image(self, image):
        validate_room_image_upload(image)
        return image

    def validate_room(self, room):
        user = self.context["request"].user
        if user.is_staff:
            return room
        if hasattr(user, "landlord_profile") and room.landlord_id == user.landlord_profile.id:
            return room
        if room.status == Room.Status.ACTIVE:
            return room
        raise serializers.ValidationError("You cannot add an image to this room.")

    def validate(self, attrs):
        room = attrs.get("room", getattr(self.instance, "room", None))
        is_cover = attrs.get("is_cover", getattr(self.instance, "is_cover", False))
        user = self.context["request"].user
        if self.instance is None and room and room.images.count() >= settings.RENTIFY_ROOM_IMAGE_LIMIT:
            raise serializers.ValidationError("This room has reached the image limit.")
        if is_cover and not (
            user.is_staff
            or (room and hasattr(user, "landlord_profile") and room.landlord_id == user.landlord_profile.id)
        ):
            raise serializers.ValidationError("Only the landlord or admin can set a cover image.")
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
    is_favorited = serializers.SerializerMethodField()

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
            "location_status",
            "location_label",
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
            "is_favorited",
            "created_at",
        )

    def get_latitude(self, obj):
        return obj.location.y

    def get_longitude(self, obj):
        return obj.location.x

    def get_distance_km(self, obj):
        distance = getattr(obj, "distance", None)
        return round(distance.km, 2) if distance else None

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return Favorite.objects.filter(user=request.user, room=obj).exists()

    def get_images(self, obj):
        images = obj.images.filter(status=RoomImage.ModerationStatus.APPROVED).select_related("uploaded_by")
        return RoomImageSerializer(images, many=True, context=self.context).data


class RoomWriteSerializer(serializers.ModelSerializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, write_only=True, required=False)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, write_only=True, required=False)
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
        return attrs

    def create(self, validated_data):
        amenities = validated_data.pop("amenities", [])
        latitude = validated_data.pop("latitude", None)
        longitude = validated_data.pop("longitude", None)
        location_data = self._resolve_location(validated_data, latitude=latitude, longitude=longitude)
        room = Room.objects.create(
            landlord=self.context["request"].user.landlord_profile,
            **location_data,
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
            validated_data.update(self._resolve_location(validated_data, latitude=latitude, longitude=longitude))
        elif "address" in validated_data or "ward" in validated_data:
            address = validated_data.get("address", instance.address)
            ward = validated_data.get("ward", instance.ward)
            validated_data.update(self._resolve_location({"address": address, "ward": ward}))
        instance = super().update(instance, validated_data)
        if amenities is not None:
            instance.amenities.set(amenities)
        if was_active:
            require_reapproval_after_edit(room=instance)
        return instance

    def _resolve_location(self, attrs, *, latitude=None, longitude=None):
        if latitude is not None and longitude is not None:
            return {
                "location": Point(float(longitude), float(latitude), srid=4326),
                "location_status": Room.LocationStatus.GEOCODED,
                "location_query": attrs.get("address", ""),
                "location_label": "Tọa độ được nhập thủ công",
            }

        address = attrs.get("address")
        ward = attrs.get("ward")
        try:
            candidates = geocode_room_address(address=address, ward=ward, limit=1)
        except GeocodingError:
            candidates = []

        if candidates:
            candidate = candidates[0]
            return {
                "location": Point(float(candidate.longitude), float(candidate.latitude), srid=4326),
                "location_status": Room.LocationStatus.GEOCODED,
                "location_query": candidate.query,
                "location_label": candidate.label,
            }

        return {
            "location": Point(106.700806, 10.776889, srid=4326),
            "location_status": Room.LocationStatus.FAILED,
            "location_query": address or "",
            "location_label": "",
        }


class RejectRoomSerializer(serializers.Serializer):
    reason = serializers.CharField()
