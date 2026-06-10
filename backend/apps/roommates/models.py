from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class LifestyleTag(models.Model):
    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=60, unique=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class RoommatePost(models.Model):
    class Type(models.TextChoices):
        HAS_ROOM = "has_room", "Đã có phòng"
        LOOKING_TOGETHER = "looking_together", "Tìm bạn cùng thuê"

    class Status(models.TextChoices):
        DRAFT = "draft", "Bản nháp"
        ACTIVE = "active", "Đang hiển thị"
        CLOSED = "closed", "Đã đóng"
        REJECTED = "rejected", "Bị từ chối"

    class GenderPreference(models.TextChoices):
        ANY = "any", "Không yêu cầu"
        MALE = "male", "Nam"
        FEMALE = "female", "Nữ"
        SAME = "same", "Cùng giới"

    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="roommate_posts",
    )
    type = models.CharField(max_length=30, choices=Type.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    university = models.ForeignKey(
        "locations.University",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="roommate_posts",
    )
    preferred_districts = models.ManyToManyField(
        "locations.District",
        blank=True,
        related_name="roommate_posts",
    )
    ward = models.ForeignKey(
        "locations.Ward",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="roommate_posts",
    )
    room = models.ForeignKey(
        "listings.Room",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="roommate_posts",
        help_text="Optional room when the poster already has a room and needs roommates.",
    )
    address = models.TextField(blank=True)

    budget_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    move_in_date = models.DateField(null=True, blank=True)
    gender_preference = models.CharField(
        max_length=10,
        choices=GenderPreference.choices,
        default=GenderPreference.ANY,
    )
    max_roommates = models.PositiveSmallIntegerField(default=1)
    current_occupants = models.PositiveSmallIntegerField(default=0)
    available_slots = models.PositiveSmallIntegerField(default=1)
    lifestyle_tags = models.ManyToManyField(
        LifestyleTag,
        blank=True,
        related_name="roommate_posts",
    )

    contact_phone = models.CharField(max_length=20, blank=True)
    rejection_reason = models.TextField(blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=Q(budget_min__isnull=True)
                | Q(budget_max__isnull=True)
                | Q(budget_min__lte=F("budget_max")),
                name="roommate_budget_range_valid",
            ),
            models.CheckConstraint(
                condition=Q(budget_min__isnull=True) | Q(budget_min__gte=0),
                name="roommate_budget_min_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(budget_max__isnull=True) | Q(budget_max__gte=0),
                name="roommate_budget_max_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(max_roommates__gt=0),
                name="roommate_max_roommates_positive",
            ),
            models.CheckConstraint(
                condition=Q(available_slots__gt=0),
                name="roommate_available_slots_positive",
            ),
        ]
        indexes = [
            models.Index(fields=("status", "type", "-created_at"), name="roommate_status_type_idx"),
            models.Index(fields=("university", "status"), name="roommate_university_idx"),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        errors = {}
        if self.posted_by_id and getattr(self.posted_by, "role", None) != "student":
            errors["posted_by"] = "Only student accounts can create roommate posts."
        if self.type == self.Type.HAS_ROOM and not self.room_id and not self.address.strip():
            errors["address"] = "Provide a room or an address when the post already has a room."
        if self.current_occupants > self.max_roommates:
            errors["current_occupants"] = "Current occupants cannot exceed maximum roommates."
        if errors:
            raise ValidationError(errors)

    def close(self):
        self.status = self.Status.CLOSED
        self.closed_at = timezone.now()
        self.save(update_fields=("status", "closed_at", "updated_at"))
        return self
