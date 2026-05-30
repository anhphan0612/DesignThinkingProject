from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Room


def submit_room_for_review(*, room):
    if room.status not in {Room.Status.DRAFT, Room.Status.REJECTED}:
        raise ValidationError("Only draft or rejected rooms can be submitted.")
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


def require_reapproval_after_edit(*, room):
    if room.status == Room.Status.ACTIVE:
        room.status = Room.Status.PENDING
        room.approved_by = None
        room.approved_at = None
        room.save(update_fields=("status", "approved_by", "approved_at", "updated_at"))
    return room
