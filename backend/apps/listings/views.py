from decimal import Decimal, InvalidOperation

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import models
from django.utils import timezone
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.interactions.models import UserEvent
from apps.interactions.services import add_favorite, log_event, log_search, remove_favorite
from apps.locations.models import University

from .models import Amenity, Room, RoomImage
from .permissions import IsRoomOwnerOrAdmin
from .serializers import (
    AmenitySerializer,
    RejectRoomSerializer,
    RoomImageSerializer,
    RoomReadSerializer,
    RoomWriteSerializer,
)
from .services import (
    approve_room,
    mark_room_rented,
    reject_room,
    require_reapproval_after_edit,
    submit_room_for_review,
)


class AmenityViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = Amenity.objects.all()
    serializer_class = AmenitySerializer


class RoomViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            classes = [permissions.AllowAny]
        elif self.action in {"favorite", "unfavorite"}:
            classes = [permissions.IsAuthenticated]
        elif self.action in {"approve", "reject"}:
            classes = [permissions.IsAdminUser]
        elif self.action in {"update", "partial_update", "destroy", "submit", "mark_rented"}:
            classes = [permissions.IsAuthenticated, IsRoomOwnerOrAdmin]
        else:
            classes = [permissions.IsAuthenticated]
        return [permission() for permission in classes]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return RoomWriteSerializer
        if self.action == "reject":
            return RejectRoomSerializer
        return RoomReadSerializer

    def get_queryset(self):
        queryset = (
            Room.objects.filter(deleted_at__isnull=True)
            .select_related("landlord__user", "ward__district")
            .prefetch_related("amenities", "images")
        )
        if self.action == "mine" and self.request.user.is_authenticated:
            if not hasattr(self.request.user, "landlord_profile"):
                return queryset.none()
            return queryset.filter(landlord=self.request.user.landlord_profile)
        if self.action in {"update", "partial_update", "destroy", "submit", "mark_rented"}:
            if self.request.user.is_staff:
                return queryset
            if hasattr(self.request.user, "landlord_profile"):
                return queryset.filter(landlord=self.request.user.landlord_profile)
            return queryset.none()
        if self.action in {"approve", "reject"}:
            return queryset
        if self.action == "retrieve" and self.request.user.is_authenticated:
            if self.request.user.is_staff:
                return queryset
            if hasattr(self.request.user, "landlord_profile"):
                return queryset.filter(
                    models.Q(status=Room.Status.ACTIVE)
                    | models.Q(landlord=self.request.user.landlord_profile)
                )

        queryset = queryset.filter(status=Room.Status.ACTIVE)
        return self._apply_public_filters(queryset)

    def _apply_public_filters(self, queryset):
        params = self.request.query_params
        if params.get("ward"):
            queryset = queryset.filter(ward_id=params["ward"])
        if params.get("district"):
            queryset = queryset.filter(ward__district_id=params["district"])
        for parameter, lookup in (
            ("min_price", "price__gte"),
            ("max_price", "price__lte"),
            ("min_area", "area__gte"),
        ):
            if params.get(parameter):
                try:
                    value = Decimal(params[parameter])
                except InvalidOperation:
                    raise serializers.ValidationError({parameter: "Enter a valid number."})
                if value < 0:
                    raise serializers.ValidationError({parameter: "Enter a non-negative number."})
                queryset = queryset.filter(**{lookup: value})
        if params.get("gender_policy"):
            queryset = queryset.filter(gender_policy=params["gender_policy"])
        amenity_ids = params.getlist("amenity")
        if amenity_ids:
            for amenity_id in amenity_ids:
                queryset = queryset.filter(amenities__id=amenity_id)
            queryset = queryset.distinct()

        query = params.get("q")
        if query:
            vector = SearchVector("title", "description", "address", config="simple")
            search_query = SearchQuery(query, config="simple")
            queryset = (
                queryset.annotate(rank=SearchRank(vector, search_query))
                .filter(rank__gte=0.05)
                .order_by("-rank", "-created_at")
            )

        university_id = params.get("university")
        max_distance_km = params.get("max_distance_km")
        if university_id and max_distance_km:
            try:
                university = University.objects.get(id=university_id, is_active=True)
                distance_limit = float(max_distance_km)
            except (University.DoesNotExist, ValueError):
                raise serializers.ValidationError({"university": "Enter valid distance search values."})
            if distance_limit <= 0:
                raise serializers.ValidationError({"max_distance_km": "Enter a positive distance."})
            queryset = (
                queryset.filter(location__distance_lte=(university.location, D(km=distance_limit)))
                .annotate(distance=Distance("location", university.location))
                .order_by("distance", "price")
            )
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        objects = page if page is not None else queryset
        serializer = self.get_serializer(objects, many=True)
        result_ids = [item["id"] for item in serializer.data]
        log_search(
            request=request,
            query_text=request.query_params.get("q", ""),
            filters={key: request.query_params.getlist(key) for key in request.query_params.keys()},
            result_ids=result_ids,
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        room = self.get_object()
        log_event(request=request, type=UserEvent.Type.VIEW_ROOM, room=room)
        serializer = self.get_serializer(room)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.status = Room.Status.INACTIVE
        instance.save(update_fields=("deleted_at", "status", "updated_at"))

    @action(detail=False, methods=["get"])
    def mine(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = RoomReadSerializer(page or queryset, many=True, context={"request": request})
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def submit(self, request, pk=None):
        room = self.get_object()
        self.check_object_permissions(request, room)
        room = submit_room_for_review(room=room)
        return Response(RoomReadSerializer(room, context={"request": request}).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        room = approve_room(room=self.get_object(), admin_user=request.user)
        return Response(RoomReadSerializer(room, context={"request": request}).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        serializer = RejectRoomSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = reject_room(room=self.get_object(), reason=serializer.validated_data["reason"])
        return Response(RoomReadSerializer(room, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def mark_rented(self, request, pk=None):
        room = self.get_object()
        room = mark_room_rented(room=room)
        return Response(RoomReadSerializer(room, context={"request": request}).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        room = self.get_object()
        favorite, created = add_favorite(user=request.user, room=room, request=request)
        return Response(
            {"favorite_id": favorite.id, "created": created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"], permission_classes=[permissions.IsAuthenticated])
    def unfavorite(self, request, pk=None):
        room = self.get_object()
        removed = remove_favorite(user=request.user, room=room, request=request)
        return Response({"removed": removed})

    @action(detail=True, methods=["post"], permission_classes=[permissions.AllowAny])
    def contact(self, request, pk=None):
        room = self.get_object()
        log_event(request=request, type=UserEvent.Type.CLICK_CONTACT, room=room)
        return Response(
            {
                "landlord_name": room.landlord.user.full_name,
                "phone": room.landlord.user.phone,
                "message": "Thong tin lien he duoc ghi nhan cho prototype.",
            }
        )

    def get_object(self):
        return super().get_object()


class RoomImageViewSet(viewsets.ModelViewSet):
    serializer_class = RoomImageSerializer

    def get_permissions(self):
        if self.action in {"approve", "reject"}:
            classes = [permissions.IsAdminUser]
        else:
            classes = [permissions.IsAuthenticated]
        return [permission() for permission in classes]

    def get_queryset(self):
        queryset = RoomImage.objects.select_related("room__landlord__user", "uploaded_by")
        if self.request.user.is_staff:
            return queryset
        if hasattr(self.request.user, "landlord_profile"):
            return queryset.filter(
                models.Q(room__landlord=self.request.user.landlord_profile)
                | models.Q(uploaded_by=self.request.user)
            )
        if self.request.user.is_authenticated:
            return queryset.filter(uploaded_by=self.request.user)
        return queryset.none()

    def perform_create(self, serializer):
        room = serializer.validated_data["room"]
        user = self.request.user
        is_landlord_owner = hasattr(user, "landlord_profile") and room.landlord_id == user.landlord_profile.id
        if user.is_staff:
            image = serializer.save(
                uploaded_by=user,
                source=RoomImage.Source.ADMIN,
                status=RoomImage.ModerationStatus.APPROVED,
            )
        elif is_landlord_owner:
            image = serializer.save(
                uploaded_by=user,
                source=RoomImage.Source.LANDLORD,
                status=RoomImage.ModerationStatus.APPROVED,
            )
            require_reapproval_after_edit(room=image.room)
        else:
            serializer.save(
                uploaded_by=user,
                source=RoomImage.Source.STUDENT,
                status=RoomImage.ModerationStatus.PENDING,
                is_cover=False,
            )

    def perform_update(self, serializer):
        image = serializer.save()
        if image.status == RoomImage.ModerationStatus.APPROVED and image.source == RoomImage.Source.LANDLORD:
            require_reapproval_after_edit(room=image.room)

    def perform_destroy(self, instance):
        room = instance.room
        instance.delete()
        require_reapproval_after_edit(room=room)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        image = self.get_object()
        image.status = RoomImage.ModerationStatus.APPROVED
        image.reviewed_by = request.user
        image.reviewed_at = timezone.now()
        image.moderation_note = ""
        image.save(update_fields=("status", "reviewed_by", "reviewed_at", "moderation_note"))
        return Response(RoomImageSerializer(image, context={"request": request}).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        image = self.get_object()
        image.status = RoomImage.ModerationStatus.REJECTED
        image.reviewed_by = request.user
        image.reviewed_at = timezone.now()
        image.moderation_note = request.data.get("moderation_note", "")
        image.save(update_fields=("status", "reviewed_by", "reviewed_at", "moderation_note"))
        return Response(RoomImageSerializer(image, context={"request": request}).data)
