import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.contrib.postgres.operations import CreateExtension
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        CreateExtension("postgis"),
        migrations.CreateModel(
            name="District",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("code", models.CharField(max_length=10, unique=True)),
            ],
            options={"ordering": ("name",)},
        ),
        migrations.CreateModel(
            name="University",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("short_name", models.CharField(blank=True, max_length=100)),
                ("address", models.TextField(blank=True)),
                ("location", django.contrib.gis.db.models.fields.PointField(geography=True, srid=4326)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"verbose_name_plural": "universities", "ordering": ("name",)},
        ),
        migrations.CreateModel(
            name="Ward",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("code", models.CharField(max_length=20, unique=True)),
                (
                    "district",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="wards",
                        to="locations.district",
                    ),
                ),
            ],
            options={"ordering": ("district__name", "name")},
        ),
        migrations.AddConstraint(
            model_name="ward",
            constraint=models.UniqueConstraint(fields=("district", "name"), name="unique_ward_name_in_district"),
        ),
        migrations.CreateModel(
            name="Landmark",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("hospital", "Hospital"),
                            ("market", "Market"),
                            ("bus_stop", "Bus stop"),
                            ("park", "Park"),
                            ("other", "Other"),
                        ],
                        max_length=30,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("location", django.contrib.gis.db.models.fields.PointField(geography=True, srid=4326)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "ward",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="landmarks",
                        to="locations.ward",
                    ),
                ),
            ],
        ),
    ]
