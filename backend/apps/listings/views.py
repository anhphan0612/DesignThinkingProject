from decimal import Decimal, InvalidOperation

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.db import models
from django.utils import timezone
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.interactions.models import UserEvent
from apps.interactions.services import add_favorite, log_event, log_search, remove_favorite, start_contact_thread
from apps.locations.models import University
from apps.recommendations.keywords import apply_room_keyword_search

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
    mark_room_available,
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
        elif self.action in {"update", "partial_update", "destroy", "submit", "mark_rented", "mark_available"}:
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

        search_intelligence = None
        query = params.get("q")
        if query:
            result = apply_room_keyword_search(queryset, query)
            queryset = result.queryset
            search_intelligence = result.intent.as_dict()
        self.search_intelligence = search_intelligence

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
                queryset.filter(
                    location_status=Room.LocationStatus.GEOCODED,
                    location__distance_lte=(university.location, D(km=distance_limit)),
                )
                .annotate(distance=Distance("location", university.location))
            )

        sort = params.get("sort") or ("distance" if university_id and max_distance_km else "newest")
        if sort == "price_asc":
            queryset = queryset.order_by("price", "-created_at")
        elif sort == "price_desc":
            queryset = queryset.order_by("-price", "-created_at")
        elif sort == "area_desc":
            queryset = queryset.order_by("-area", "price")
        elif sort == "distance" and university_id and max_distance_km:
            queryset = queryset.order_by("distance", "price")
        elif not params.get("q"):
            queryset = queryset.order_by("-created_at")
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
        if getattr(self, "search_intelligence", None):
            response_meta = {"search_intelligence": self.search_intelligence}
        else:
            response_meta = {}
        if page is not None:
            response = self.get_paginated_response(serializer.data)
            response.data.update(response_meta)
            return response
        if response_meta:
            return Response({"results": serializer.data, **response_meta})
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

    @action(detail=True, methods=["post"])
    def mark_available(self, request, pk=None):
        room = self.get_object()
        room = mark_room_available(room=room)
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

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def contact(self, request, pk=None):
        room = self.get_object()
        log_event(request=request, type=UserEvent.Type.CLICK_CONTACT, room=room)
        message = request.data.get("message", "").strip()
        contact_request, thread = start_contact_thread(
            requester=request.user,
            recipient=room.landlord.user,
            room=room,
            message=message,
        )
        return Response(
            {
                "contact_request_id": contact_request.id,
                "thread_id": thread.id,
                "landlord_name": room.landlord.user.full_name,
                "message": "Đã mở cuộc trò chuyện. Hãy nhập tin nhắn trong box chat.",
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
        if serializer.validated_data.get("is_cover"):
            room.images.filter(is_cover=True).update(is_cover=False)

        if user.is_staff:
            source = RoomImage.Source.ADMIN
            image_status = RoomImage.ModerationStatus.APPROVED
        elif is_landlord_owner:
            source = RoomImage.Source.LANDLORD
            image_status = RoomImage.ModerationStatus.APPROVED
        else:
            source = RoomImage.Source.STUDENT
            image_status = RoomImage.ModerationStatus.PENDING

        if image_status == RoomImage.ModerationStatus.PENDING:
            image = serializer.save(
                uploaded_by=user,
                source=source,
                status=image_status,
                is_cover=False,
            )
        else:
            image = serializer.save(
                uploaded_by=user,
                source=source,
                status=image_status,
            )

        if is_landlord_owner:
            require_reapproval_after_edit(room=image.room)

        approved_cover_exists = room.images.filter(
            status=RoomImage.ModerationStatus.APPROVED,
            is_cover=True,
        ).exists()
        if not approved_cover_exists:
            first_image = room.images.filter(status=RoomImage.ModerationStatus.APPROVED).order_by("sort_order", "id").first()
            if first_image:
                first_image.is_cover = True
                first_image.save(update_fields=("is_cover",))

    def perform_update(self, serializer):
        image = serializer.save()
        if image.is_cover:
            image.room.images.exclude(pk=image.pk).update(is_cover=False)
        if image.status == RoomImage.ModerationStatus.APPROVED and image.source == RoomImage.Source.LANDLORD:
            require_reapproval_after_edit(room=image.room)

    def perform_destroy(self, instance):
        room = instance.room
        visible_images = room.images.filter(status=RoomImage.ModerationStatus.APPROVED).count()
        if room.status in {Room.Status.ACTIVE, Room.Status.PENDING} and visible_images <= 1:
            raise serializers.ValidationError("Rooms that are active or pending must keep at least one approved image.")
        was_cover = instance.is_cover
        instance.delete()
        if was_cover:
            first_image = room.images.filter(status=RoomImage.ModerationStatus.APPROVED).order_by("sort_order", "id").first()
            if first_image:
                first_image.is_cover = True
                first_image.save(update_fields=("is_cover",))
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
