from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.frontend.views import HomeView, LandlordHomeView, RoomDetailView, RoommateHomeView, upload_room_image
from apps.interactions.views import FavoriteViewSet, SearchLogViewSet, UserEventViewSet
from apps.listings.views import AmenityViewSet, RoomImageViewSet, RoomViewSet
from apps.locations.views import DistrictViewSet, UniversityViewSet, WardViewSet
from apps.roommates.views import LifestyleTagViewSet, RoommatePostViewSet


router = DefaultRouter()
router.register("districts", DistrictViewSet, basename="district")
router.register("wards", WardViewSet, basename="ward")
router.register("universities", UniversityViewSet, basename="university")
router.register("amenities", AmenityViewSet, basename="amenity")
router.register("rooms", RoomViewSet, basename="room")
router.register("room-images", RoomImageViewSet, basename="room-image")
router.register("lifestyle-tags", LifestyleTagViewSet, basename="lifestyle-tag")
router.register("roommate-posts", RoommatePostViewSet, basename="roommate-post")
router.register("favorites", FavoriteViewSet, basename="favorite")
router.register("events", UserEventViewSet, basename="event")
router.register("search-logs", SearchLogViewSet, basename="search-log")

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("landlord/", LandlordHomeView.as_view(), name="landlord-home"),
    path("roommates/", RoommateHomeView.as_view(), name="roommate-home"),
    path("rooms/<int:pk>/", RoomDetailView.as_view(), name="frontend-room-detail"),
    path("rooms/<int:pk>/images/upload/", upload_room_image, name="room-image-upload"),
    path("admin/", admin.site.urls),
    path("auth/", include("apps.accounts.web_urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("accounts/", include("allauth.urls")),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/recommendations/", include("apps.recommendations.urls")),
    path("api/", include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
