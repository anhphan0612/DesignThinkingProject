from decimal import Decimal, InvalidOperation

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import models
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import User

from .models import LifestyleTag, RoommatePost
from .permissions import IsRoommatePostOwnerOrAdmin
from .serializers import LifestyleTagSerializer, RoommatePostReadSerializer, RoommatePostWriteSerializer
from .services import score_roommate_post


class LifestyleTagViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = LifestyleTag.objects.all()
    serializer_class = LifestyleTagSerializer


class RoommatePostViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            classes = [permissions.AllowAny]
        elif self.action in {"update", "partial_update", "destroy", "close"}:
            classes = [permissions.IsAuthenticated, IsRoommatePostOwnerOrAdmin]
        else:
            classes = [permissions.IsAuthenticated]
        return [permission() for permission in classes]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return RoommatePostWriteSerializer
        return RoommatePostReadSerializer

    def get_queryset(self):
        queryset = (
            RoommatePost.objects.select_related(
                "posted_by",
                "university",
                "ward__district",
                "room__landlord__user",
                "room__ward__district",
            )
            .prefetch_related(
                "preferred_districts",
                "lifestyle_tags",
                "room__amenities",
                "room__images",
            )
        )
        if self.action == "mine" and self.request.user.is_authenticated:
            return queryset.filter(posted_by=self.request.user)
        if self.action in {"update", "partial_update", "destroy", "close"}:
            if self.request.user.is_staff:
                return queryset
            return queryset.filter(posted_by=self.request.user)
        if self.action == "matches":
            return queryset.filter(status=RoommatePost.Status.ACTIVE).exclude(posted_by=self.request.user)
        if self.action == "retrieve":
            if self.request.user.is_authenticated and (
                self.request.user.is_staff or queryset.filter(pk=self.kwargs.get("pk"), posted_by=self.request.user).exists()
            ):
                return queryset
        return self._apply_public_filters(queryset.filter(status=RoommatePost.Status.ACTIVE))

    def _apply_public_filters(self, queryset):
        params = self.request.query_params
        if params.get("type"):
            queryset = queryset.filter(type=params["type"])
        if params.get("university"):
            queryset = queryset.filter(university_id=params["university"])
        if params.get("district"):
            queryset = queryset.filter(
                models.Q(preferred_districts__id=params["district"])
                | models.Q(ward__district_id=params["district"])
            ).distinct()
        for parameter, lookup in (
            ("min_budget", "budget_max__gte"),
            ("max_budget", "budget_min__lte"),
        ):
            if params.get(parameter):
                try:
                    value = Decimal(params[parameter])
                except InvalidOperation:
                    raise serializers.ValidationError({parameter: "Enter a valid number."})
                if value < 0:
                    raise serializers.ValidationError({parameter: "Enter a non-negative number."})
                queryset = queryset.filter(**{lookup: value})
        if params.get("gender_preference"):
            queryset = queryset.filter(gender_preference=params["gender_preference"])
        tag_ids = params.getlist("lifestyle_tag")
        if tag_ids:
            for tag_id in tag_ids:
                queryset = queryset.filter(lifestyle_tags__id=tag_id)
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
        return queryset

    def perform_destroy(self, instance):
        instance.close()

    @action(detail=False, methods=["get"])
    def mine(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = RoommatePostReadSerializer(page or queryset, many=True, context={"request": request})
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def matches(self, request):
        if request.user.role != User.Role.STUDENT or not hasattr(request.user, "student_profile"):
            raise serializers.ValidationError("Only student accounts can get roommate matches.")
        profile = request.user.student_profile
        queryset = self.get_queryset()
        ranked = []
        for post in queryset[:100]:
            match = score_roommate_post(profile, post)
            post.match = match
            ranked.append((match["score"], post))
        posts = [post for _, post in sorted(ranked, key=lambda item: item[0], reverse=True) if post.match["score"] > 0]
        serializer = RoommatePostReadSerializer(posts[:20], many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        post = self.get_object()
        post.close()
        return Response(RoommatePostReadSerializer(post, context={"request": request}).data)
