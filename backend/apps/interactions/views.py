from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import ContentReport, Favorite, SearchLog, UserEvent
from .serializers import ContentReportSerializer, FavoriteSerializer, SearchLogSerializer, UserEventSerializer
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


class ContentReportViewSet(viewsets.ModelViewSet):
    serializer_class = ContentReportSerializer

    def get_permissions(self):
        if self.action in {"list", "retrieve", "resolve", "dismiss"}:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        return (
            ContentReport.objects.select_related(
                "reporter",
                "handled_by",
                "room",
                "room_image__room",
                "roommate_post",
            )
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(
            reporter=self.request.user if self.request.user.is_authenticated else None,
            session_key=get_session_key(self.request),
        )

    def _handle(self, status_value):
        report = self.get_object()
        report.status = status_value
        report.handled_by = self.request.user
        report.handled_at = timezone.now()
        report.save(update_fields=("status", "handled_by", "handled_at"))
        return Response(ContentReportSerializer(report, context={"request": self.request}).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        return self._handle(ContentReport.Status.RESOLVED)

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        return self._handle(ContentReport.Status.DISMISSED)
