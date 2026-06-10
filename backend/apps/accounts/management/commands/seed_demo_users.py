from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import LandlordProfile, StudentProfile, User
from apps.locations.models import University


DEFAULT_PASSWORD = "demo-password"

STUDENTS = (
    {
        "email": "student.hust.demo@example.com",
        "full_name": "Nguyen Van An",
        "phone": "0911000001",
        "student_code": "HUST-DEMO-001",
        "university": "HUST",
        "budget_min": "2500000",
        "budget_max": "3800000",
        "max_distance_km": "3.00",
    },
    {
        "email": "student.neu.demo@example.com",
        "full_name": "Tran Thi Binh",
        "phone": "0911000002",
        "student_code": "NEU-DEMO-002",
        "university": "NEU",
        "budget_min": "2200000",
        "budget_max": "3500000",
        "max_distance_km": "2.50",
    },
    {
        "email": "student.huce.demo@example.com",
        "full_name": "Le Minh Chau",
        "phone": "0911000003",
        "student_code": "HUCE-DEMO-003",
        "university": "HUCE",
        "budget_min": "3000000",
        "budget_max": "4500000",
        "max_distance_km": "4.00",
    },
    {
        "email": "student.vnu.demo@example.com",
        "full_name": "Pham Quang Dung",
        "phone": "0911000004",
        "student_code": "VNU-DEMO-004",
        "university": "VNU",
        "budget_min": "2000000",
        "budget_max": "3200000",
        "max_distance_km": "5.00",
    },
    {
        "email": "student.ajc.demo@example.com",
        "full_name": "Hoang Thu Ha",
        "phone": "0911000005",
        "student_code": "AJC-DEMO-005",
        "university": "AJC",
        "budget_min": "2600000",
        "budget_max": "4200000",
        "max_distance_km": "3.50",
    },
)

LANDLORDS = (
    {
        "email": "landlord.demo@example.com",
        "full_name": "Chu tro demo",
        "phone": "0900000000",
        "business_name": "Nha tro demo",
        "identity_number": "LANDLORD-DEMO-001",
    },
    {
        "email": "landlord.hanoi.demo@example.com",
        "full_name": "Do Manh Hung",
        "phone": "0900000002",
        "business_name": "Phong tro Minh Hung",
        "identity_number": "LANDLORD-DEMO-002",
    },
)

ADMINS = (
    {
        "email": "admin.demo@example.com",
        "full_name": "Admin demo",
        "phone": "0900000009",
    },
)


class Command(BaseCommand):
    help = "Seed demo users for local and test databases."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help=f"Password assigned to every demo user. Default: {DEFAULT_PASSWORD}",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["password"]
        universities = {
            university.short_name: university
            for university in University.objects.filter(short_name__in={item["university"] for item in STUDENTS})
        }

        student_count = 0
        for item in STUDENTS:
            user = self._upsert_user(
                email=item["email"],
                password=password,
                full_name=item["full_name"],
                phone=item["phone"],
                role=User.Role.STUDENT,
            )
            StudentProfile.objects.update_or_create(
                user=user,
                defaults={
                    "university": universities.get(item["university"]),
                    "student_code": item["student_code"],
                    "budget_min": Decimal(item["budget_min"]),
                    "budget_max": Decimal(item["budget_max"]),
                    "max_distance_km": Decimal(item["max_distance_km"]),
                },
            )
            student_count += 1

        landlord_count = 0
        for item in LANDLORDS:
            user = self._upsert_user(
                email=item["email"],
                password=password,
                full_name=item["full_name"],
                phone=item["phone"],
                role=User.Role.LANDLORD,
            )
            LandlordProfile.objects.update_or_create(
                user=user,
                defaults={
                    "business_name": item["business_name"],
                    "identity_number": item["identity_number"],
                    "verification_status": LandlordProfile.VerificationStatus.APPROVED,
                },
            )
            landlord_count += 1

        admin_count = 0
        for item in ADMINS:
            self._upsert_user(
                email=item["email"],
                password=password,
                full_name=item["full_name"],
                phone=item["phone"],
                role=User.Role.ADMIN,
                is_staff=True,
                is_superuser=True,
            )
            admin_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded demo users: "
                f"{student_count} students, "
                f"{landlord_count} landlords, "
                f"{admin_count} admins. "
                f"Password: {password}"
            )
        )

    def _upsert_user(self, email, password, **defaults):
        defaults.setdefault("is_active", True)
        if defaults["role"] != User.Role.ADMIN:
            defaults.setdefault("is_staff", False)
            defaults.setdefault("is_superuser", False)

        user, _ = User.objects.update_or_create(email=email, defaults=defaults)
        user.set_password(password)
        user.save(update_fields=("password",))
        return user
