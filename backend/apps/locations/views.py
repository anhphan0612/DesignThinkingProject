from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .geocoding import GeocodingError, geocode_room_address
from .models import District, Landmark, University, Ward
from .serializers import DistrictSerializer, LandmarkSerializer, UniversitySerializer, WardSerializer


class DistrictViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = District.objects.all()
    serializer_class = DistrictSerializer


class WardViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = WardSerializer

    def get_queryset(self):
        queryset = Ward.objects.select_related("district")
        district_id = self.request.query_params.get("district")
        if district_id:
            queryset = queryset.filter(district_id=district_id)
        return queryset.order_by("district__name", "name", "id")

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def geocode(self, request):
        address = request.query_params.get("address", "").strip()
        ward_id = request.query_params.get("ward")
        if not address:
            return Response({"detail": "address is required."}, status=status.HTTP_400_BAD_REQUEST)

        ward = None
        if ward_id:
            try:
                ward = Ward.objects.select_related("district").get(pk=ward_id)
            except Ward.DoesNotExist:
                return Response({"detail": "ward is invalid."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            candidates = geocode_room_address(address=address, ward=ward, limit=5)
        except GeocodingError as exc:
            return Response({"detail": str(exc), "results": []}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(
            {
                "results": [
                    {
                        "latitude": str(candidate.latitude),
                        "longitude": str(candidate.longitude),
                        "label": candidate.label,
                        "provider": candidate.provider,
                        "query": candidate.query,
                    }
                    for candidate in candidates
                ]
            }
        )


class UniversityViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = University.objects.filter(is_active=True)
    serializer_class = UniversitySerializer


class LandmarkViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = LandmarkSerializer

    def get_queryset(self):
        queryset = Landmark.objects.filter(is_active=True).select_related("ward__district")
        landmark_type = self.request.query_params.get("type")
        district_id = self.request.query_params.get("district")
        ward_id = self.request.query_params.get("ward")
        if landmark_type:
            queryset = queryset.filter(type=landmark_type)
        if district_id:
            queryset = queryset.filter(ward__district_id=district_id)
        if ward_id:
            queryset = queryset.filter(ward_id=ward_id)
        return queryset.order_by("type", "name", "id")

