from django.urls import path

from . import views


urlpatterns = [
    path("landlord/", views.landlord_dashboard, name="landlord-dashboard"),
    path("landlord/rooms/new/", views.landlord_room_create, name="landlord-room-create"),
    path("landlord/rooms/<int:pk>/", views.landlord_room_detail, name="landlord-room-detail"),
    path("landlord/rooms/<int:pk>/edit/", views.landlord_room_edit, name="landlord-room-edit"),
    path("landlord/rooms/<int:pk>/submit/", views.landlord_room_submit, name="landlord-room-submit"),
    path("landlord/rooms/<int:pk>/mark-rented/", views.landlord_room_mark_rented, name="landlord-room-mark-rented"),
    path("landlord/rooms/<int:pk>/images/upload/", views.landlord_room_image_upload, name="landlord-room-image-upload"),
    path("moderation/", views.moderation_dashboard, name="moderation-dashboard"),
    path("moderation/rooms/<int:pk>/", views.moderation_room_detail, name="moderation-room-detail"),
    path("moderation/rooms/<int:pk>/approve/", views.moderation_room_approve, name="moderation-room-approve"),
    path("moderation/rooms/<int:pk>/reject/", views.moderation_room_reject, name="moderation-room-reject"),
    path("moderation/images/<int:pk>/approve/", views.moderation_image_approve, name="moderation-image-approve"),
    path("moderation/images/<int:pk>/reject/", views.moderation_image_reject, name="moderation-image-reject"),
]
