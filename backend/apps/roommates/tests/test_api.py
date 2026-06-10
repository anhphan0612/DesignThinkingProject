from decimal import Decimal
from uuid import uuid4

from django.contrib.gis.geos import Point
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import LandlordProfile, StudentProfile, User
from apps.locations.models import District, University, Ward
from apps.roommates.models import LifestyleTag, RoommatePost


class RoommatePostApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        suffix = uuid4().hex[:6]
        self.district = District.objects.create(name="Hai Ba Trung", code=f"H{suffix}")
        self.ward = Ward.objects.create(district=self.district, name="Bach Khoa", code=f"HBK{suffix}")
        self.university = University.objects.create(
            name="Dai hoc Bach khoa Ha Noi",
            short_name=f"HUST-{suffix}",
            location=Point(105.8435, 21.0059, srid=4326),
            is_active=True,
        )
        self.tag = LifestyleTag.objects.create(name="Yen tinh", code=f"quiet-{suffix}")
        self.student = User.objects.create_user(
            email=f"student-{suffix}@example.com",
            password="password-123",
            full_name="Student",
            role=User.Role.STUDENT,
        )
        self.profile = StudentProfile.objects.create(
            user=self.student,
            university=self.university,
            budget_min=Decimal("1500000"),
            budget_max=Decimal("3500000"),
        )
        self.profile.preferred_districts.add(self.district)
        self.profile.lifestyle_tags.add(self.tag)

        self.other_student = User.objects.create_user(
            email=f"other-{suffix}@example.com",
            password="password-123",
            full_name="Other Student",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=self.other_student)

    def create_post(self, **overrides):
        defaults = {
            "posted_by": self.other_student,
            "type": RoommatePost.Type.LOOKING_TOGETHER,
            "status": RoommatePost.Status.ACTIVE,
            "title": "Tim ban o ghep gan truong",
            "university": self.university,
            "ward": self.ward,
            "budget_min": Decimal("1800000"),
            "budget_max": Decimal("3000000"),
            "available_slots": 1,
            "max_roommates": 2,
        }
        defaults.update(overrides)
        post = RoommatePost.objects.create(**defaults)
        post.preferred_districts.add(self.district)
        post.lifestyle_tags.add(self.tag)
        return post

    def test_public_list_only_returns_active_posts(self):
        active_post = self.create_post()
        self.create_post(title="Draft post", status=RoommatePost.Status.DRAFT)

        response = self.client.get("/api/roommate-posts/")

        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data["results"]]
        self.assertEqual(ids, [active_post.id])

    def test_student_can_create_roommate_post(self):
        self.client.force_authenticate(self.student)

        response = self.client.post(
            "/api/roommate-posts/",
            {
                "type": RoommatePost.Type.HAS_ROOM,
                "title": "Can tim 1 ban o ghep",
                "address": "Ngo 30 Ta Quang Buu",
                "university": self.university.id,
                "ward": self.ward.id,
                "budget_min": "1500000",
                "budget_max": "2500000",
                "available_slots": 1,
                "max_roommates": 2,
                "current_occupants": 1,
                "lifestyle_tags": [self.tag.id],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        post = RoommatePost.objects.get(id=response.data["id"])
        self.assertEqual(post.posted_by, self.student)
        self.assertEqual(post.status, RoommatePost.Status.ACTIVE)

    def test_landlord_cannot_create_roommate_post(self):
        landlord = User.objects.create_user(
            email=f"landlord-{uuid4().hex[:6]}@example.com",
            password="password-123",
            full_name="Landlord",
            role=User.Role.LANDLORD,
        )
        LandlordProfile.objects.create(user=landlord)
        self.client.force_authenticate(landlord)

        response = self.client.post(
            "/api/roommate-posts/",
            {
                "type": RoommatePost.Type.LOOKING_TOGETHER,
                "title": "Invalid landlord post",
                "budget_min": "1500000",
                "budget_max": "2500000",
                "available_slots": 1,
                "max_roommates": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_matches_returns_ranked_posts_for_student(self):
        post = self.create_post()
        self.client.force_authenticate(self.student)

        response = self.client.get("/api/roommate-posts/matches/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["id"], post.id)
        self.assertGreater(response.data[0]["match"]["score"], 0)
        self.assertIn("Ngân sách khớp", response.data[0]["match"]["reasons"])
