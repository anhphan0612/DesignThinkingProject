from django.core.management.base import BaseCommand

from apps.listings.models import Amenity


AMENITIES = (
    ("Wifi", "wifi"),
    ("Điều hòa", "air-conditioner"),
    ("Máy giặt", "washing-machine"),
    ("Chỗ để xe", "parking"),
    ("Nhà tắm riêng", "private-bathroom"),
    ("Bếp", "kitchen"),
    ("Gác lửng", "mezzanine"),
    ("Bảo vệ", "security"),
)


class Command(BaseCommand):
    help = "Seed room amenities used by listings and recommendations."

    def handle(self, *args, **options):
        created = 0
        for name, code in AMENITIES:
            _, was_created = Amenity.objects.update_or_create(code=code, defaults={"name": name})
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Seeded amenities; {created} created."))
