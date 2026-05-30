from django.contrib.gis.db import models


class District(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Ward(models.Model):
    district = models.ForeignKey(District, on_delete=models.PROTECT, related_name="wards")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ("district__name", "name")
        constraints = [
            models.UniqueConstraint(fields=("district", "name"), name="unique_ward_name_in_district")
        ]

    def __str__(self):
        return f"{self.name}, {self.district.name}"


class University(models.Model):
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    location = models.PointField(srid=4326, geography=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "universities"

    def __str__(self):
        return self.name


class Landmark(models.Model):
    class Type(models.TextChoices):
        HOSPITAL = "hospital", "Hospital"
        MARKET = "market", "Market"
        BUS_STOP = "bus_stop", "Bus stop"
        PARK = "park", "Park"
        OTHER = "other", "Other"

    ward = models.ForeignKey(Ward, on_delete=models.PROTECT, related_name="landmarks")
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=30, choices=Type.choices)
    location = models.PointField(srid=4326, geography=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

