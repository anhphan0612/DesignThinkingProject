from decimal import Decimal

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.interactions.models import UserEvent
from apps.interactions.services import log_event

from .models import RecommendationLog
from .serializers import RecommendationSerializer
from .services import recommended_rooms_for_student


class RecommendationListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ranked = recommended_rooms_for_student(request.user)
        payload = []
        for index, (room, score, detail) in enumerate(ranked, start=1):
            payload.append(
                {
                    "room": room,
                    "score": score,
                    "rank": index,
                    "score_detail": detail,
                }
            )
            RecommendationLog.objects.create(
                user=request.user,
                room=room,
                score=Decimal(str(score)),
                rank=index,
                score_detail=detail,
            )
        if payload:
            log_event(
                request=request,
                type=UserEvent.Type.RECOMMENDATION_VIEW,
                metadata={"room_ids": [item["room"].id for item in payload]},
            )
        serializer = RecommendationSerializer(payload, many=True, context={"request": request})
        return Response(serializer.data)

