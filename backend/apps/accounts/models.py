from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import F, Q

from .managers import UserManager


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Sinh viên"
        LANDLORD = "landlord", "Chủ trọ"
        ADMIN = "admin", "Admin"

    username = None
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    def __str__(self):
        return self.email


class StudentProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="student_profile",
        limit_choices_to={"role": User.Role.STUDENT},
    )
    university = models.ForeignKey(
        "locations.University",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    student_code = models.CharField(max_length=50, blank=True)
    budget_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_distance_km = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(budget_min__isnull=True)
                | Q(budget_max__isnull=True)
                | Q(budget_min__lte=F("budget_max")),
                name="student_budget_range_valid",
            ),
            models.CheckConstraint(
                condition=Q(budget_min__isnull=True) | Q(budget_min__gte=0),
                name="student_budget_min_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(budget_max__isnull=True) | Q(budget_max__gte=0),
                name="student_budget_max_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(max_distance_km__gt=0),
                name="student_max_distance_positive",
            ),
        ]

    def __str__(self):
        return f"Student profile: {self.user.email}"


class LandlordProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "unverified", "Chưa xác thực"
        PENDING = "pending", "Chờ duyệt"
        APPROVED = "approved", "Đã xác thực"
        REJECTED = "rejected", "Bị từ chối"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="landlord_profile",
        limit_choices_to={"role": User.Role.LANDLORD},
    )
    business_name = models.CharField(max_length=255, blank=True)
    identity_number = models.CharField(max_length=50, blank=True)
    identity_document = models.FileField(upload_to="private/landlord_documents/", blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Landlord profile: {self.user.email}"
