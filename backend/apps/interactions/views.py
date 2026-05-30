from rest_framework import mixins, permissions, status, viewsets
from rest_framework.response import Response

from .models import Favorite, SearchLog, UserEvent
from .serializers import FavoriteSerializer, SearchLogSerializer, UserEventSerializer
from .services import get_session_key


class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Favorite.objects.filter(user=self.request.user)
            .select_related("room__landlord__user", "room__ward__district")
            .prefetch_related("room__amenities", "room__images")
        )

    def perform_create(self, serializer):
        serializer.save()


class UserEventViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = UserEventSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = UserEvent.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_key=get_session_key(request),
            **serializer.validated_data,
        )
        return Response(UserEventSerializer(event).data, status=status.HTTP_201_CREATED)


class SearchLogViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = SearchLogSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        search_log = SearchLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_key=get_session_key(request),
            **serializer.validated_data,
        )
        return Response(SearchLogSerializer(search_log).data, status=status.HTTP_201_CREATED)
