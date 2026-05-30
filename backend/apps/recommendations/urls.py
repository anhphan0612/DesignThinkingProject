from django.urls import path

from .views import RecommendationListAPIView


urlpatterns = [
    path("", RecommendationListAPIView.as_view(), name="recommendations"),
]

