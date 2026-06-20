from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("interactions", "0001_initial"),
        ("listings", "0004_room_location_geocoding"),
        ("roommates", "0002_roommatepost_status_labels"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ContentReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_key", models.CharField(blank=True, max_length=80)),
                (
                    "target_type",
                    models.CharField(
                        choices=[
                            ("room", "Phòng"),
                            ("room_image", "Ảnh phòng"),
                            ("roommate_post", "Bài ghép trọ"),
                        ],
                        max_length=30,
                    ),
                ),
                ("reason", models.CharField(max_length=255)),
                ("details", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "Đang mở"),
                            ("resolved", "Đã xử lý"),
                            ("dismissed", "Bỏ qua"),
                        ],
                        default="open",
                        max_length=20,
                    ),
                ),
                ("handled_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "handled_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="handled_content_reports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reporter",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="content_reports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "room",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reports",
                        to="listings.room",
                    ),
                ),
                (
                    "room_image",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reports",
                        to="listings.roomimage",
                    ),
                ),
                (
                    "roommate_post",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reports",
                        to="roommates.roommatepost",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="contentreport",
            index=models.Index(fields=["target_type", "status"], name="report_target_status_idx"),
        ),
        migrations.AddIndex(
            model_name="contentreport",
            index=models.Index(fields=["reporter", "-created_at"], name="report_reporter_created_idx"),
        ),
    ]
