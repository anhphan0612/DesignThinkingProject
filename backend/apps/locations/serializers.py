from rest_framework import serializers

from .models import District, Landmark, University, Ward


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ("id", "name", "code")


class WardSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source="district.name", read_only=True)

    class Meta:
        model = Ward
        fields = ("id", "district", "district_name", "name", "code")


class UniversitySerializer(serializers.ModelSerializer):
    longitude = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()

    class Meta:
        model = University
        fields = ("id", "name", "short_name", "address", "longitude", "latitude")

    def get_longitude(self, obj):
        return obj.location.x

    def get_latitude(self, obj):
        return obj.location.y


class LandmarkSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_type_display", read_only=True)
    district_name = serializers.CharField(source="ward.district.name", read_only=True)
    ward_name = serializers.CharField(source="ward.name", read_only=True)
    longitude = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Landmark
        fields = (
            "id",
            "name",
            "type",
            "type_label",
            "ward",
            "ward_name",
            "district_name",
            "longitude",
            "latitude",
            "distance_km",
        )

    def get_longitude(self, obj):
        return obj.location.x

    def get_latitude(self, obj):
        return obj.location.y

    def get_distance_km(self, obj):
        distance = getattr(obj, "distance", None)
        return round(distance.km, 2) if distance else None

