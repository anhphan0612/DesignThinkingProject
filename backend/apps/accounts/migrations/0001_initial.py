import apps.accounts.managers
import django.contrib.auth.models
import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("locations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active.",
                        verbose_name="active",
                    ),
                ),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                ("email", models.EmailField(max_length=254, unique=True)),
                (
                    "role",
                    models.CharField(
                        choices=[("student", "Student"), ("landlord", "Landlord"), ("admin", "Admin")],
                        default="student",
                        max_length=20,
                    ),
                ),
                ("full_name", models.CharField(max_length=255)),
                ("phone", models.CharField(blank=True, max_length=20)),
                ("avatar", models.ImageField(blank=True, upload_to="avatars/")),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={"abstract": False},
            managers=[("objects", apps.accounts.managers.UserManager())],
        ),
        migrations.CreateModel(
            name="LandlordProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("business_name", models.CharField(blank=True, max_length=255)),
                ("identity_number", models.CharField(blank=True, max_length=50)),
                ("identity_document", models.FileField(blank=True, upload_to="private/landlord_documents/")),
                (
                    "verification_status",
                    models.CharField(
                        choices=[
                            ("unverified", "Unverified"),
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                        ],
                        default="unverified",
                        max_length=20,
                    ),
                ),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        limit_choices_to={"role": "landlord"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="landlord_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="StudentProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("student_code", models.CharField(blank=True, max_length=50)),
                ("budget_min", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("budget_max", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("max_distance_km", models.DecimalField(decimal_places=2, default=Decimal("5"), max_digits=5)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "university",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="students",
                        to="locations.university",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        limit_choices_to={"role": "student"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="student_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="studentprofile",
            constraint=models.CheckConstraint(
                condition=models.Q(("budget_min__isnull", True), ("budget_max__isnull", True), ("budget_min__lte", models.F("budget_max")), _connector="OR"),
                name="student_budget_range_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="studentprofile",
            constraint=models.CheckConstraint(
                condition=models.Q(("budget_min__isnull", True), ("budget_min__gte", 0), _connector="OR"),
                name="student_budget_min_non_negative",
            ),
        ),
        migrations.AddConstraint(
            model_name="studentprofile",
            constraint=models.CheckConstraint(
                condition=models.Q(("budget_max__isnull", True), ("budget_max__gte", 0), _connector="OR"),
                name="student_budget_max_non_negative",
            ),
        ),
        migrations.AddConstraint(
            model_name="studentprofile",
            constraint=models.CheckConstraint(condition=models.Q(("max_distance_km__gt", 0)), name="student_max_distance_positive"),
        ),
    ]
