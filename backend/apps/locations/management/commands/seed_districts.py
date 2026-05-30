from django.core.management.base import BaseCommand

from apps.locations.models import District


DISTRICTS = (
    ("Hoàn Kiếm", "HK"),
    ("Ba Đình", "BD"),
    ("Đống Đa", "DD"),
    ("Hai Bà Trưng", "HBT"),
    ("Hoàng Mai", "HM"),
    ("Thanh Xuân", "TX"),
    ("Cầu Giấy", "CG"),
    ("Nam Từ Liêm", "NTL"),
    ("Bắc Từ Liêm", "BTL"),
    ("Tây Hồ", "TH"),
    ("Long Biên", "LB"),
    ("Hà Đông", "HD"),
)


class Command(BaseCommand):
    help = "Seed Hanoi districts used by room listings."

    def handle(self, *args, **options):
        created = 0
        for name, code in DISTRICTS:
            _, was_created = District.objects.update_or_create(code=code, defaults={"name": name})
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Seeded districts; {created} created."))
