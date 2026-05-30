from rest_framework import permissions, viewsets

from .models import District, University, Ward
from .serializers import DistrictSerializer, UniversitySerializer, WardSerializer


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
        return queryset


class UniversityViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = University.objects.filter(is_active=True)
    serializer_class = UniversitySerializer

