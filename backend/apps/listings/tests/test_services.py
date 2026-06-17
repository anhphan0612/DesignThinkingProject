from unittest.mock import Mock

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.test import override_settings
from rest_framework.exceptions import ValidationError

from apps.accounts.models import LandlordProfile
from apps.listings.models import Room
from apps.listings.services import approve_room, mark_room_rented, submit_room_for_review
from apps.listings.validators import validate_room_image_upload


class RoomStateServiceTests(SimpleTestCase):
    def room(self, state):
        room = Mock(status=state)
        room.landlord.verification_status = LandlordProfile.VerificationStatus.APPROVED
        room.rejection_reason = "old reason"
        return room

    def test_submit_moves_draft_room_to_pending(self):
        room = self.room(Room.Status.DRAFT)

        submit_room_for_review(room=room)

        self.assertEqual(room.status, Room.Status.PENDING)
        room.save.assert_called_once()

    def test_approve_rejects_room_not_pending(self):
        with self.assertRaises(ValidationError):
            approve_room(room=self.room(Room.Status.DRAFT), admin_user=Mock())

    def test_submit_requires_verified_landlord(self):
        room = self.room(Room.Status.DRAFT)
        room.landlord.verification_status = LandlordProfile.VerificationStatus.PENDING

        with self.assertRaises(ValidationError):
            submit_room_for_review(room=room)

    def test_mark_rented_requires_active_room(self):
        with self.assertRaises(ValidationError):
            mark_room_rented(room=self.room(Room.Status.PENDING))


class RoomImageUploadValidatorTests(SimpleTestCase):
    @override_settings(RENTIFY_MAX_ROOM_IMAGE_SIZE_MB=1)
    def test_rejects_image_larger_than_limit(self):
        upload = SimpleUploadedFile(
            "room.jpg",
            b"x" * (1024 * 1024 + 1),
            content_type="image/jpeg",
        )

        with self.assertRaises(DjangoValidationError):
            validate_room_image_upload(upload)

    @override_settings(RENTIFY_ALLOWED_ROOM_IMAGE_TYPES=["image/jpeg"])
    def test_rejects_unsupported_content_type(self):
        upload = SimpleUploadedFile(
            "room.gif",
            b"gif-data",
            content_type="image/gif",
        )

        with self.assertRaises(DjangoValidationError):
            validate_room_image_upload(upload)

