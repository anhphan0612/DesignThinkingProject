from unittest.mock import Mock

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from apps.listings.models import Room
from apps.listings.services import approve_room, mark_room_rented, submit_room_for_review


class RoomStateServiceTests(SimpleTestCase):
    def room(self, state):
        room = Mock(status=state)
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

    def test_mark_rented_requires_active_room(self):
        with self.assertRaises(ValidationError):
            mark_room_rented(room=self.room(Room.Status.PENDING))

