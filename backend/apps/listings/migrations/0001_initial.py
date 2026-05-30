import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
        ("locations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Amenity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("code", models.SlugField(max_length=50, unique=True)),
            ],
            options={"verbose_name_plural": "amenities", "ordering": ("name",)},
        ),
        migrations.CreateModel(
            name="Room",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("address", models.TextField()),
                ("location", django.contrib.gis.db.models.fields.PointField(geography=True, srid=4326)),
                ("price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("deposit", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("area", models.DecimalField(decimal_places=2, max_digits=7)),
                ("max_occupants", models.PositiveSmallIntegerField(default=1)),
                (
                    "gender_policy",
                    models.CharField(
                        choices=[("any", "Any"), ("male", "Male"), ("female", "Female")],
                        default="any",
                        max_length=10,
                    ),
                ),
                ("electricity_price", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("water_price", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("pending", "Pending approval"),
                            ("active", "Active"),
                            ("rejected", "Rejected"),
                            ("inactive", "Inactive"),
                            ("rented", "Rented"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("rejection_reason", models.TextField(blank=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("amenities", models.ManyToManyField(blank=True, related_name="rooms", to="listings.amenity")),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="approved_rooms",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "landlord",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rooms",
                        to="accounts.landlordprofile",
                    ),
                ),
                (
                    "ward",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rooms",
                        to="locations.ward",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
                "indexes": [models.Index(fields=["status", "price"], name="room_status_price_idx")],
            },
        ),
        migrations.AddConstraint(
            model_name="room",
            constraint=models.CheckConstraint(condition=models.Q(("price__gt", 0)), name="room_price_positive"),
        ),
        migrations.AddConstraint(
            model_name="room",
            constraint=models.CheckConstraint(condition=models.Q(("area__gt", 0)), name="room_area_positive"),
        ),
        migrations.AddConstraint(
            model_name="room",
            constraint=models.CheckConstraint(condition=models.Q(("max_occupants__gt", 0)), name="room_occupants_positive"),
        ),
        migrations.AddConstraint(
            model_name="room",
            constraint=models.CheckConstraint(
                condition=models.Q(("deposit__isnull", True), ("deposit__gte", 0), _connector="OR"),
                name="room_deposit_non_negative",
            ),
        ),
        migrations.AddConstraint(
            model_name="room",
            constraint=models.CheckConstraint(
                condition=models.Q(("electricity_price__isnull", True), ("electricity_price__gte", 0), _connector="OR"),
                name="room_electricity_non_negative",
            ),
        ),
        migrations.AddConstraint(
            model_name="room",
            constraint=models.CheckConstraint(
                condition=models.Q(("water_price__isnull", True), ("water_price__gte", 0), _connector="OR"),
                name="room_water_non_negative",
            ),
        ),
        migrations.CreateModel(
            name="RoomImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="rooms/")),
                ("is_cover", models.BooleanField(default=False)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "room",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="images", to="listings.room"),
                ),
            ],
            options={"ordering": ("sort_order", "id")},
        ),
        migrations.AddConstraint(
            model_name="roomimage",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_cover", True)),
                fields=("room",),
                name="unique_room_cover_image",
            ),
        ),
    ]

