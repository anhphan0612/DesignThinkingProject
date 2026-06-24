from django.conf import settings
from django.contrib import messages
from django.contrib.gis.geos import Point
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.interactions.models import ContentReport
from apps.listings.models import Room, RoomImage
from apps.listings.services import (
    approve_room,
    mark_room_available,
    mark_room_rented,
    reject_room,
    require_reapproval_after_edit,
    submit_room_for_review,
)
from apps.locations.geocoding import GeocodingError, geocode_room_address, local_geocode_room_address
from apps.locations.models import Landmark

from .forms import LandlordRoomImageForm, LandlordRoomImageMetaForm, RejectImageForm, RejectRoomForm, RoomForm
from .permissions import landlord_required, staff_required


def _room_review_checklist(room):
    approved_images = room.images.filter(status=RoomImage.ModerationStatus.APPROVED)
    return [
        {
            "label": "Có ít nhất 1 ảnh phòng",
            "done": approved_images.exists(),
            "action_url": None,
            "action_label": "",
        },
        {
            "label": "Địa chỉ đã ghim được trên bản đồ",
            "done": room.location_status == Room.LocationStatus.GEOCODED,
            "action_url": "landlord-room-edit",
            "action_label": "Sửa vị trí",
        },
        {
            "label": "Đã nhập giá, diện tích và sức chứa",
            "done": bool(room.price and room.area and room.max_occupants),
            "action_url": "landlord-room-edit",
            "action_label": "Sửa thông tin",
        },
    ]


def _room_can_submit(room):
    return all(item["done"] for item in _room_review_checklist(room))


def _touch_room_after_image_change(room):
    require_reapproval_after_edit(room=room)


def _ensure_cover_image(room):
    approved_images = room.images.filter(status=RoomImage.ModerationStatus.APPROVED)
    if approved_images.filter(is_cover=True).exists():
        return
    first_image = approved_images.order_by("sort_order", "id").first()
    if first_image:
        first_image.is_cover = True
        first_image.save(update_fields=("is_cover",))


def _apply_room_geocoding(room):
    try:
        candidates = geocode_room_address(address=room.address, ward=room.ward, limit=1)
    except GeocodingError:
        candidates = []

    if candidates:
        candidate = candidates[0]
        room.location = Point(float(candidate.longitude), float(candidate.latitude), srid=4326)
        room.location_status = Room.LocationStatus.GEOCODED
        room.location_query = candidate.query
        room.location_label = candidate.label
        return True

    fallback = _fallback_room_geocoding(room)
    if fallback:
        point, label = fallback
        room.location = point
        room.location_status = Room.LocationStatus.GEOCODED
        room.location_query = f"{room.address}, {room.ward}" if room.ward_id else room.address
        room.location_label = label
        return True

    room.location_status = Room.LocationStatus.FAILED
    room.location_query = f"{room.address}, {room.ward}" if room.ward_id else room.address
    room.location_label = ""
    return False


def _fallback_room_geocoding(room):
    if not room.ward_id:
        return None

    local_candidates = local_geocode_room_address(address=room.address, ward=room.ward)
    if local_candidates:
        candidate = local_candidates[0]
        return Point(float(candidate.longitude), float(candidate.latitude), srid=4326), candidate.label

    landmarks = Landmark.objects.filter(is_active=True, ward=room.ward)
    landmark = landmarks.order_by("type", "name").first()
    if not landmark:
        landmark = (
            Landmark.objects.filter(is_active=True, ward__district=room.ward.district)
            .select_related("ward__district")
            .order_by("type", "name")
            .first()
        )
    if not landmark:
        return None

    label = f"Ước lượng theo {room.ward.name}, {room.ward.district.name} gần {landmark.name}"
    return Point(landmark.location.x, landmark.location.y, srid=4326), label


@landlord_required
def landlord_dashboard(request):
    profile = request.user.landlord_profile
    rooms = (
        Room.objects.filter(landlord=profile, deleted_at__isnull=True)
        .prefetch_related("images", "amenities")
        .order_by("-created_at")
    )
    room_cards = [
        {
            "room": room,
            "checklist": _room_review_checklist(room),
            "can_submit": _room_can_submit(room),
        }
        for room in rooms
    ]
    return render(request, "dashboard/landlord_dashboard.html", {"room_cards": room_cards, "profile": profile})


@landlord_required
def landlord_room_create(request):
    form = RoomForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        room = form.save(commit=False)
        room.landlord = request.user.landlord_profile
        room.status = Room.Status.DRAFT
        geocoded = _apply_room_geocoding(room)
        room.save()
        form.save_m2m()
        if geocoded:
            messages.success(request, "Đã tạo phòng nháp và ghim vị trí trên bản đồ.")
        else:
            messages.warning(request, "Đã tạo phòng nháp, nhưng chưa tìm được vị trí trên bản đồ. Hãy kiểm tra lại địa chỉ trước khi gửi duyệt.")
        return redirect("landlord-room-detail", pk=room.pk)
    return render(request, "dashboard/landlord_room_form.html", {"form": form, "title": "Tạo phòng mới"})


@landlord_required
def landlord_room_detail(request, pk):
    room = get_object_or_404(Room, pk=pk, landlord=request.user.landlord_profile, deleted_at__isnull=True)
    image_form = LandlordRoomImageForm()
    room_images = list(room.images.all())
    for image in room_images:
        image.meta_form = LandlordRoomImageMetaForm(instance=image, prefix=f"image-{image.id}")
    checklist = _room_review_checklist(room)
    return render(
        request,
        "dashboard/landlord_room_detail.html",
        {
            "room": room,
            "image_form": image_form,
            "room_images": room_images,
            "image_count": len(room_images),
            "image_limit": settings.RENTIFY_ROOM_IMAGE_LIMIT,
            "checklist": checklist,
            "can_submit": all(item["done"] for item in checklist),
        },
    )


@landlord_required
def landlord_room_preview(request, pk):
    room = get_object_or_404(
        Room.objects.select_related("landlord__user", "ward__district").prefetch_related("amenities", "images"),
        pk=pk,
        landlord=request.user.landlord_profile,
        deleted_at__isnull=True,
    )
    delta = 0.006
    return render(
        request,
        "frontend/room_detail.html",
        {
            "room": room,
            "map_bbox": {
                "left": room.location.x - delta,
                "bottom": room.location.y - delta,
                "right": room.location.x + delta,
                "top": room.location.y + delta,
            },
            "approved_images": room.images.filter(status=RoomImage.ModerationStatus.APPROVED).select_related("uploaded_by"),
            "is_favorited": False,
            "is_landlord_preview": True,
        },
    )


@landlord_required
def landlord_room_edit(request, pk):
    room = get_object_or_404(Room, pk=pk, landlord=request.user.landlord_profile, deleted_at__isnull=True)
    form = RoomForm(request.POST or None, instance=room)
    if request.method == "POST" and form.is_valid():
        was_active = room.status == Room.Status.ACTIVE
        room = form.save()
        geocoded = _apply_room_geocoding(room)
        if was_active:
            room.status = Room.Status.PENDING
            room.approved_by = None
            room.approved_at = None
        room.save(
            update_fields=(
                "location",
                "location_status",
                "location_query",
                "location_label",
                "status",
                "approved_by",
                "approved_at",
                "updated_at",
            )
        )
        if geocoded:
            messages.success(request, "Đã cập nhật phòng và ghim vị trí trên bản đồ.")
        else:
            messages.warning(request, "Đã cập nhật phòng, nhưng chưa tìm được vị trí trên bản đồ. Hãy kiểm tra lại địa chỉ.")
        return redirect("landlord-room-detail", pk=room.pk)
    return render(request, "dashboard/landlord_room_form.html", {"form": form, "room": room, "title": "Sửa phòng"})


@landlord_required
@require_POST
def landlord_room_submit(request, pk):
    room = get_object_or_404(Room, pk=pk, landlord=request.user.landlord_profile, deleted_at__isnull=True)
    if not _room_can_submit(room):
        messages.error(request, "Phòng chưa đủ điều kiện gửi duyệt. Hãy hoàn tất các mục trong checklist.")
        return redirect("landlord-room-detail", pk=room.pk)
    try:
        submit_room_for_review(room=room)
        messages.success(request, "Đã gửi phòng cho admin duyệt.")
    except Exception as exc:
        messages.error(request, str(exc))
    return redirect("landlord-room-detail", pk=room.pk)


@landlord_required
@require_POST
def landlord_room_mark_rented(request, pk):
    room = get_object_or_404(Room, pk=pk, landlord=request.user.landlord_profile, deleted_at__isnull=True)
    try:
        mark_room_rented(room=room)
        messages.success(request, "Đã đánh dấu phòng là đã cho thuê.")
    except Exception as exc:
        messages.error(request, str(exc))
    return redirect("landlord-room-detail", pk=room.pk)


@landlord_required
@require_POST
def landlord_room_mark_available(request, pk):
    room = get_object_or_404(Room, pk=pk, landlord=request.user.landlord_profile, deleted_at__isnull=True)
    try:
        mark_room_available(room=room)
        messages.success(request, "Đã mở lại phòng để hiển thị cho người tìm trọ.")
    except Exception as exc:
        messages.error(request, str(exc))
    return redirect("landlord-room-detail", pk=room.pk)


@landlord_required
@require_POST
def landlord_room_image_upload(request, pk):
    room = get_object_or_404(Room, pk=pk, landlord=request.user.landlord_profile, deleted_at__isnull=True)
    form = LandlordRoomImageForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        if room.images.count() >= settings.RENTIFY_ROOM_IMAGE_LIMIT:
            messages.error(request, f"Phòng chỉ được có tối đa {settings.RENTIFY_ROOM_IMAGE_LIMIT} ảnh.")
            return redirect("landlord-room-detail", pk=room.pk)
        if form.cleaned_data.get("is_cover"):
            room.images.filter(is_cover=True).update(is_cover=False)
        image = form.save(commit=False)
        image.room = room
        image.uploaded_by = request.user
        image.source = RoomImage.Source.LANDLORD
        image.status = RoomImage.ModerationStatus.APPROVED
        try:
            image.save()
        except IntegrityError:
            messages.error(request, "Không đặt được ảnh bìa. Hãy thử lại.")
            return redirect("landlord-room-detail", pk=room.pk)
        _ensure_cover_image(room)
        _touch_room_after_image_change(room)
        messages.success(request, "Đã thêm ảnh phòng.")
    else:
        messages.error(request, "Không thêm được ảnh phòng. Hãy kiểm tra định dạng và dung lượng ảnh.")
    return redirect("landlord-room-detail", pk=room.pk)


@landlord_required
@require_POST
def landlord_room_image_update(request, pk, image_pk):
    room = get_object_or_404(Room, pk=pk, landlord=request.user.landlord_profile, deleted_at__isnull=True)
    image = get_object_or_404(RoomImage, pk=image_pk, room=room)
    form = LandlordRoomImageMetaForm(request.POST, instance=image, prefix=f"image-{image.id}")
    if form.is_valid():
        form.save()
        _touch_room_after_image_change(room)
        messages.success(request, "Đã cập nhật thông tin ảnh.")
    else:
        messages.error(request, "Không cập nhật được ảnh. Hãy kiểm tra chú thích và thứ tự.")
    return redirect("landlord-room-detail", pk=room.pk)


@landlord_required
@require_POST
def landlord_room_image_set_cover(request, pk, image_pk):
    room = get_object_or_404(Room, pk=pk, landlord=request.user.landlord_profile, deleted_at__isnull=True)
    image = get_object_or_404(RoomImage, pk=image_pk, room=room)
    room.images.exclude(pk=image.pk).update(is_cover=False)
    image.is_cover = True
    image.status = RoomImage.ModerationStatus.APPROVED
    try:
        image.save(update_fields=("is_cover", "status"))
    except IntegrityError:
        messages.error(request, "Không đặt được ảnh bìa. Hãy thử lại.")
        return redirect("landlord-room-detail", pk=room.pk)
    _touch_room_after_image_change(room)
    messages.success(request, "Đã đặt ảnh bìa.")
    return redirect("landlord-room-detail", pk=room.pk)


@landlord_required
@require_POST
def landlord_room_image_delete(request, pk, image_pk):
    room = get_object_or_404(Room, pk=pk, landlord=request.user.landlord_profile, deleted_at__isnull=True)
    image = get_object_or_404(RoomImage, pk=image_pk, room=room)
    visible_images = room.images.filter(status=RoomImage.ModerationStatus.APPROVED).count()
    if room.status in {Room.Status.ACTIVE, Room.Status.PENDING} and visible_images <= 1:
        messages.error(request, "Không thể xóa ảnh cuối cùng khi phòng đang hiển thị hoặc chờ duyệt.")
        return redirect("landlord-room-detail", pk=room.pk)
    was_cover = image.is_cover
    image.delete()
    if was_cover:
        _ensure_cover_image(room)
    _touch_room_after_image_change(room)
    messages.success(request, "Đã xóa ảnh phòng.")
    return redirect("landlord-room-detail", pk=room.pk)


@staff_required
def moderation_dashboard(request):
    pending_rooms = Room.objects.filter(status=Room.Status.PENDING, deleted_at__isnull=True).select_related("landlord__user", "ward__district")
    pending_images = RoomImage.objects.filter(status=RoomImage.ModerationStatus.PENDING).select_related("room", "uploaded_by")
    open_reports = (
        ContentReport.objects.filter(status=ContentReport.Status.OPEN)
        .select_related("reporter", "room", "room_image__room", "roommate_post")
        .order_by("-created_at")
    )
    return render(
        request,
        "dashboard/moderation_dashboard.html",
        {
            "pending_rooms": pending_rooms,
            "pending_images": pending_images,
            "open_reports": open_reports,
        },
    )


@staff_required
def moderation_room_detail(request, pk):
    room = get_object_or_404(Room.objects.select_related("landlord__user", "ward__district").prefetch_related("amenities", "images"), pk=pk)
    return render(request, "dashboard/moderation_room_detail.html", {"room": room})


@staff_required
def moderation_room_preview(request, pk):
    room = get_object_or_404(
        Room.objects.select_related("landlord__user", "ward__district").prefetch_related("amenities", "images"),
        pk=pk,
        deleted_at__isnull=True,
    )
    delta = 0.006
    return render(
        request,
        "frontend/room_detail.html",
        {
            "room": room,
            "map_bbox": {
                "left": room.location.x - delta,
                "bottom": room.location.y - delta,
                "right": room.location.x + delta,
                "top": room.location.y + delta,
            },
            "approved_images": room.images.filter(status=RoomImage.ModerationStatus.APPROVED).select_related("uploaded_by"),
            "is_favorited": False,
            "is_landlord_preview": True,
        },
    )


@staff_required
@require_POST
def moderation_room_approve(request, pk):
    room = get_object_or_404(Room, pk=pk)
    approve_room(room=room, admin_user=request.user)
    messages.success(request, "Đã duyệt phòng.")
    return redirect("moderation-dashboard")


@staff_required
def moderation_room_reject(request, pk):
    room = get_object_or_404(Room, pk=pk)
    form = RejectRoomForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        reject_room(room=room, reason=form.cleaned_data["reason"])
        messages.success(request, "Đã từ chối phòng.")
        return redirect("moderation-dashboard")
    return render(request, "dashboard/reject_form.html", {"form": form, "title": "Từ chối phòng"})


@staff_required
@require_POST
def moderation_image_approve(request, pk):
    image = get_object_or_404(RoomImage, pk=pk)
    image.status = RoomImage.ModerationStatus.APPROVED
    image.reviewed_by = request.user
    image.reviewed_at = timezone.now()
    image.moderation_note = ""
    image.save(update_fields=("status", "reviewed_by", "reviewed_at", "moderation_note"))
    _ensure_cover_image(image.room)
    messages.success(request, "Đã duyệt ảnh.")
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
        image.is_cover = False
        image.save(update_fields=("status", "reviewed_by", "reviewed_at", "moderation_note", "is_cover"))
        _ensure_cover_image(image.room)
        messages.success(request, "Đã từ chối ảnh.")
        return redirect("moderation-dashboard")
    return render(request, "dashboard/reject_form.html", {"form": form, "title": "Từ chối ảnh"})


def _handle_report(request, pk, status_value, message):
    report = get_object_or_404(ContentReport, pk=pk)
    report.status = status_value
    report.handled_by = request.user
    report.handled_at = timezone.now()
    report.save(update_fields=("status", "handled_by", "handled_at"))
    messages.success(request, message)
    return redirect("moderation-dashboard")


@staff_required
@require_POST
def moderation_report_resolve(request, pk):
    return _handle_report(request, pk, ContentReport.Status.RESOLVED, "Đã đánh dấu báo cáo là đã xử lý.")


@staff_required
@require_POST
def moderation_report_dismiss(request, pk):
    return _handle_report(request, pk, ContentReport.Status.DISMISSED, "Đã bỏ qua báo cáo.")
