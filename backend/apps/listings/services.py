from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Room, RoomImage


def submit_room_for_review(*, room):
    if room.status not in {Room.Status.DRAFT, Room.Status.REJECTED}:
        raise ValidationError("Only draft or rejected rooms can be submitted.")
    if room.location_status != Room.LocationStatus.GEOCODED:
        raise ValidationError("The room address must be mapped before submitting.")
    if room.price <= 0 or room.area <= 0 or room.max_occupants <= 0:
        raise ValidationError("Room price, area and maximum occupants must be valid before submitting.")
    if not room.images.filter(status=RoomImage.ModerationStatus.APPROVED).exists():
        raise ValidationError("At least one approved room image is required before submitting.")
    room.status = Room.Status.PENDING
    room.rejection_reason = ""
    room.save(update_fields=("status", "rejection_reason", "updated_at"))
    return room


def approve_room(*, room, admin_user):
    if room.status != Room.Status.PENDING:
        raise ValidationError("Only pending rooms can be approved.")
    room.status = Room.Status.ACTIVE
    room.approved_by = admin_user
    room.approved_at = timezone.now()
    room.rejection_reason = ""
    room.save(
        update_fields=("status", "approved_by", "approved_at", "rejection_reason", "updated_at")
    )
    return room


def reject_room(*, room, reason):
    if room.status != Room.Status.PENDING:
        raise ValidationError("Only pending rooms can be rejected.")
    if not reason.strip():
        raise ValidationError({"reason": "A rejection reason is required."})
    room.status = Room.Status.REJECTED
    room.rejection_reason = reason.strip()
    room.save(update_fields=("status", "rejection_reason", "updated_at"))
    return room


def mark_room_rented(*, room):
    if room.status != Room.Status.ACTIVE:
        raise ValidationError("Only active rooms can be marked as rented.")
    room.status = Room.Status.RENTED
    room.save(update_fields=("status", "updated_at"))
    return room


def mark_room_available(*, room):
    if room.status != Room.Status.RENTED:
        raise ValidationError("Only rented rooms can be reopened.")
    room.status = Room.Status.ACTIVE
    room.save(update_fields=("status", "updated_at"))
    return room


def require_reapproval_after_edit(*, room):
    if room.status == Room.Status.ACTIVE:
        room.status = Room.Status.PENDING
        room.approved_by = None
        room.approved_at = None
        room.save(update_fields=("status", "approved_by", "approved_at", "updated_at"))
    return room
