from django.contrib.gis.db import models
from django.db.models import Q


class Amenity(models.Model):
    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=50, unique=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "amenities"

    def __str__(self):
        return self.name


class Room(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Bản nháp"
        PENDING = "pending", "Chờ duyệt"
        ACTIVE = "active", "Đang hiển thị"
        REJECTED = "rejected", "Bị từ chối"
        INACTIVE = "inactive", "Đã ẩn"
        RENTED = "rented", "Đã cho thuê"

    class GenderPolicy(models.TextChoices):
        ANY = "any", "Tất cả"
        MALE = "male", "Nam"
        FEMALE = "female", "Nữ"

    landlord = models.ForeignKey(
        "accounts.LandlordProfile",
        on_delete=models.PROTECT,
        related_name="rooms",
    )
    ward = models.ForeignKey("locations.Ward", on_delete=models.PROTECT, related_name="rooms")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    address = models.TextField()
    location = models.PointField(srid=4326, geography=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    deposit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    area = models.DecimalField(max_digits=7, decimal_places=2)
    max_occupants = models.PositiveSmallIntegerField(default=1)
    gender_policy = models.CharField(
        max_length=10,
        choices=GenderPolicy.choices,
        default=GenderPolicy.ANY,
    )
    electricity_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    water_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amenities = models.ManyToManyField(Amenity, blank=True, related_name="rooms")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    rejection_reason = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_rooms",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(condition=Q(price__gt=0), name="room_price_positive"),
            models.CheckConstraint(condition=Q(area__gt=0), name="room_area_positive"),
            models.CheckConstraint(condition=Q(max_occupants__gt=0), name="room_occupants_positive"),
            models.CheckConstraint(
                condition=Q(deposit__isnull=True) | Q(deposit__gte=0),
                name="room_deposit_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(electricity_price__isnull=True) | Q(electricity_price__gte=0),
                name="room_electricity_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(water_price__isnull=True) | Q(water_price__gte=0),
                name="room_water_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=("status", "price"), name="room_status_price_idx"),
        ]

    def __str__(self):
        return self.title


class RoomImage(models.Model):
    class Source(models.TextChoices):
        LANDLORD = "landlord", "Chủ trọ"
        STUDENT = "student", "Sinh viên"
        ADMIN = "admin", "Admin"

    class ModerationStatus(models.TextChoices):
        PENDING = "pending", "Chờ duyệt"
        APPROVED = "approved", "Đã duyệt"
        REJECTED = "rejected", "Bị từ chối"

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="rooms/")
    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_room_images",
    )
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.LANDLORD)
    status = models.CharField(
        max_length=20,
        choices=ModerationStatus.choices,
        default=ModerationStatus.APPROVED,
    )
    caption = models.CharField(max_length=255, blank=True)
    is_cover = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_room_images",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    moderation_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sort_order", "id")
        indexes = [
            models.Index(fields=("room", "status", "source"), name="room_image_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("room",),
                condition=Q(is_cover=True) & Q(status="approved"),
                name="unique_room_cover_image",
            )
        ]

    def __str__(self):
        return f"Image for {self.room_id}"
