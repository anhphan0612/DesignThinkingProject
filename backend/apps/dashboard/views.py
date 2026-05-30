from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import LandlordProfile
from apps.listings.models import Room, RoomImage
from apps.listings.services import approve_room, mark_room_rented, reject_room, submit_room_for_review

from .forms import LandlordRoomImageForm, RejectImageForm, RejectRoomForm, RoomForm
from .permissions import landlord_required, staff_required


@landlord_required
def landlord_dashboard(request):
    profile = request.user.landlord_profile
    rooms = (
        Room.objects.filter(landlord=profile, deleted_at__isnull=True)
        .prefetch_related("images", "amenities")
        .order_by("-created_at")
    )
    return render(request, "dashboard/landlord_dashboard.html", {"rooms": rooms, "profile": profile})


@landlord_required
def landlord_room_create(request):
    form = RoomForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        room = form.save(commit=False)
        room.landlord = request.user.landlord_profile
        room.status = Room.Status.DRAFT
        room.save()
        form.save_m2m()
        messages.success(request, "Da tao phong nhap. Hay them anh va gui duyet.")
        return redirect("landlord-room-detail", pk=room.pk)
    return render(request, "dashboard/landlord_room_form.html", {"form": form, "title": "Tao phong moi"})


@landlord_required
def landlord_room_detail(request, pk):
    room = get_object_or_404(Room, pk=pk, landlord=request.user.landlord_profile, deleted_at__isnull=True)
    image_form = LandlordRoomImageForm()
    return render(request, "dashboard/landlord_room_detail.html", {"room": room, "image_form": image_form})


@landlord_required
def landlord_room_edit(request, pk):
    room = get_object_or_404(Room, pk=pk, landlord=request.user.landlord_profile, deleted_at__isnull=True)
    form = RoomForm(request.POST or None, instance=room)
    if request.method == "POST" and form.is_valid():
        was_active = room.status == Room.Status.ACTIVE
        room = form.save()
        if was_active:
            room.status = Room.Status.PENDING
            room.approved_by = None
            room.approved_at = None
            room.save(update_fields=("status", "approved_by", "approved_at", "updated_at"))
        messages.success(request, "Da cap nhat phong.")
        return redirect("landlord-room-detail", pk=room.pk)
    return render(request, "dashboard/landlord_room_form.html", {"form": form, "room": room, "title": "Sua phong"})


@landlord_required
def landlord_room_submit(request, pk):
    room = get_object_or_404(Room, pk=pk, landlord=request.user.landlord_profile, deleted_at__isnull=True)
    try:
        submit_room_for_review(room=room)
        messages.success(request, "Da gui phong cho admin duyet.")
    except Exception as exc:
        messages.error(request, str(exc))
    return redirect("landlord-room-detail", pk=room.pk)


@landlord_required
def landlord_room_mark_rented(request, pk):
    room = get_object_or_404(Room, pk=pk, landlord=request.user.landlord_profile, deleted_at__isnull=True)
    try:
        mark_room_rented(room=room)
        messages.success(request, "Da danh dau phong la da cho thue.")
    except Exception as exc:
        messages.error(request, str(exc))
    return redirect("landlord-room-detail", pk=room.pk)


@landlord_required
def landlord_room_image_upload(request, pk):
    room = get_object_or_404(Room, pk=pk, landlord=request.user.landlord_profile, deleted_at__isnull=True)
    form = LandlordRoomImageForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        image = form.save(commit=False)
        image.room = room
        image.uploaded_by = request.user
        image.source = RoomImage.Source.LANDLORD
        image.status = RoomImage.ModerationStatus.APPROVED
        image.save()
        messages.success(request, "Da them anh phong.")
    else:
        messages.error(request, "Khong them duoc anh phong.")
    return redirect("landlord-room-detail", pk=room.pk)


@staff_required
def moderation_dashboard(request):
    pending_rooms = Room.objects.filter(status=Room.Status.PENDING, deleted_at__isnull=True).select_related("landlord__user", "ward__district")
    pending_images = RoomImage.objects.filter(status=RoomImage.ModerationStatus.PENDING).select_related("room", "uploaded_by")
    pending_landlords = LandlordProfile.objects.filter(verification_status=LandlordProfile.VerificationStatus.PENDING).select_related("user")
    return render(
        request,
        "dashboard/moderation_dashboard.html",
        {
            "pending_rooms": pending_rooms,
            "pending_images": pending_images,
            "pending_landlords": pending_landlords,
        },
    )


@staff_required
def moderation_room_detail(request, pk):
    room = get_object_or_404(Room.objects.select_related("landlord__user", "ward__district").prefetch_related("amenities", "images"), pk=pk)
    return render(request, "dashboard/moderation_room_detail.html", {"room": room})


@staff_required
def moderation_room_approve(request, pk):
    room = get_object_or_404(Room, pk=pk)
    approve_room(room=room, admin_user=request.user)
    messages.success(request, "Da duyet phong.")
    return redirect("moderation-dashboard")


@staff_required
def moderation_room_reject(request, pk):
    room = get_object_or_404(Room, pk=pk)
    form = RejectRoomForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        reject_room(room=room, reason=form.cleaned_data["reason"])
        messages.success(request, "Da tu choi phong.")
        return redirect("moderation-dashboard")
    return render(request, "dashboard/reject_form.html", {"form": form, "title": "Tu choi phong"})


@staff_required
def moderation_image_approve(request, pk):
    image = get_object_or_404(RoomImage, pk=pk)
    image.status = RoomImage.ModerationStatus.APPROVED
    image.reviewed_by = request.user
    image.reviewed_at = timezone.now()
    image.moderation_note = ""
    image.save(update_fields=("status", "reviewed_by", "reviewed_at", "moderation_note"))
    messages.success(request, "Da duyet anh.")
    return redirect("moderation-dashboard")


@staff_required
def moderation_image_reject(request, pk):
    image = get_object_or_404(RoomImage, pk=pk)
    form = RejectImageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        image.status = RoomImage.ModerationStatus.REJECTED
        image.reviewed_by = request.user
        image.reviewed_at = timezone.now()
        image.moderation_note = form.cleaned_data["moderation_note"]
        image.save(update_fields=("status", "reviewed_by", "reviewed_at", "moderation_note"))
        messages.success(request, "Da tu choi anh.")
        return redirect("moderation-dashboard")
    return render(request, "dashboard/reject_form.html", {"form": form, "title": "Tu choi anh"})
