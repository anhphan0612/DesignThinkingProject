from django.utils.decorators import method_decorator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import DetailView, TemplateView

from apps.accounts.models import User
from apps.listings.models import Room, RoomImage


@method_decorator(ensure_csrf_cookie, name="dispatch")
class HomeView(TemplateView):
    template_name = "frontend/home.html"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class RoomSearchView(TemplateView):
    template_name = "frontend/rooms_home.html"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LandlordHomeView(TemplateView):
    template_name = "frontend/landlord_home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["is_landlord"] = user.is_authenticated and user.role == User.Role.LANDLORD
        if context["is_landlord"] and hasattr(user, "landlord_profile"):
            rooms = Room.objects.filter(landlord=user.landlord_profile, deleted_at__isnull=True)
            context.update(
                {
                    "profile": user.landlord_profile,
                    "total_rooms": rooms.count(),
                    "active_rooms": rooms.filter(status=Room.Status.ACTIVE).count(),
                    "pending_rooms": rooms.filter(status=Room.Status.PENDING).count(),
                    "draft_rooms": rooms.filter(status=Room.Status.DRAFT).count(),
                    "recent_rooms": rooms.prefetch_related("images", "amenities")[:4],
                }
            )
        return context


@method_decorator(ensure_csrf_cookie, name="dispatch")
class RoommateHomeView(TemplateView):
    template_name = "frontend/roommate_home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["is_student"] = user.is_authenticated and user.role == User.Role.STUDENT
        return context


@method_decorator(ensure_csrf_cookie, name="dispatch")
class RoomDetailView(DetailView):
    model = Room
    template_name = "frontend/room_detail.html"
    context_object_name = "room"

    def get_queryset(self):
        return (
            Room.objects.filter(status=Room.Status.ACTIVE, deleted_at__isnull=True)
            .select_related("landlord__user", "ward__district")
            .prefetch_related("amenities", "images")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        room = self.object
        delta = 0.006
        context["map_bbox"] = {
            "left": room.location.x - delta,
            "bottom": room.location.y - delta,
            "right": room.location.x + delta,
            "top": room.location.y + delta,
        }
        context["approved_images"] = room.images.filter(
            status=RoomImage.ModerationStatus.APPROVED
        ).select_related("uploaded_by")
        return context


@login_required
def upload_room_image(request, pk):
    room = get_object_or_404(Room, pk=pk, status=Room.Status.ACTIVE, deleted_at__isnull=True)
    if request.method != "POST":
        return redirect("frontend-room-detail", pk=room.pk)
    image = request.FILES.get("image")
    if not image:
        messages.error(request, "Hãy chọn ảnh trước khi gửi.")
        return redirect("frontend-room-detail", pk=room.pk)

    user = request.user
    is_landlord_owner = hasattr(user, "landlord_profile") and room.landlord_id == user.landlord_profile.id
    if user.is_staff:
        source = RoomImage.Source.ADMIN
        status = RoomImage.ModerationStatus.APPROVED
    elif is_landlord_owner:
        source = RoomImage.Source.LANDLORD
        status = RoomImage.ModerationStatus.APPROVED
    else:
        source = RoomImage.Source.STUDENT
        status = RoomImage.ModerationStatus.PENDING

    RoomImage.objects.create(
        room=room,
        image=image,
        caption=request.POST.get("caption", ""),
        uploaded_by=user,
        source=source,
        status=status,
        is_cover=False,
    )
    if status == RoomImage.ModerationStatus.PENDING:
        messages.success(request, "Ảnh đã được gửi và đang chờ admin duyệt.")
    else:
        messages.success(request, "Ảnh đã được thêm vào phòng.")
    return redirect("frontend-room-detail", pk=room.pk)
