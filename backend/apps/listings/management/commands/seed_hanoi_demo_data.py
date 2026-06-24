from decimal import Decimal
from pathlib import Path
import shutil

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import LandlordProfile, StudentProfile, User
from apps.listings.models import Amenity, Room, RoomImage
from apps.locations.models import District, Landmark, University, Ward
from apps.roommates.models import LifestyleTag


DISTRICTS = (
    ("Cầu Giấy", "HN-CG"),
    ("Đống Đa", "HN-DD"),
    ("Hai Bà Trưng", "HN-HBT"),
    ("Thanh Xuân", "HN-TX"),
    ("Hà Đông", "HN-HD"),
    ("Nam Từ Liêm", "HN-NTL"),
)

WARDS = (
    ("HN-CG", "Dịch Vọng Hậu", "HN-CG-DVH"),
    ("HN-CG", "Quan Hoa", "HN-CG-QH"),
    ("HN-DD", "Trung Liệt", "HN-DD-TL"),
    ("HN-DD", "Láng Thượng", "HN-DD-LT"),
    ("HN-HBT", "Bách Khoa", "HN-HBT-BK"),
    ("HN-HBT", "Đồng Tâm", "HN-HBT-DT"),
    ("HN-TX", "Nhân Chính", "HN-TX-NC"),
    ("HN-TX", "Khương Trung", "HN-TX-KT"),
    ("HN-HD", "Mộ Lao", "HN-HD-ML"),
    ("HN-NTL", "Mỹ Đình 2", "HN-NTL-MD2"),
)

UNIVERSITIES = (
    ("Đại học Bách khoa Hà Nội", "HUST", "1 Đại Cồ Việt, Hai Bà Trưng", 105.8435, 21.0059, "HN-HBT-BK"),
    ("Đại học Kinh tế Quốc dân", "NEU", "207 Giải Phóng, Hai Bà Trưng", 105.8420, 21.0007, "HN-HBT-DT"),
    ("Đại học Xây dựng Hà Nội", "HUCE", "55 Giải Phóng, Hai Bà Trưng", 105.8428, 21.0037, "HN-HBT-BK"),
    ("Đại học Quốc gia Hà Nội", "VNU", "144 Xuân Thủy, Cầu Giấy", 105.7829, 21.0379, "HN-CG-DVH"),
    ("Học viện Báo chí và Tuyên truyền", "AJC", "36 Xuân Thủy, Cầu Giấy", 105.7850, 21.0375, "HN-CG-DVH"),
    ("Đại học Thương mại", "TMU", "79 Hồ Tùng Mậu, Cầu Giấy", 105.7759, 21.0368, "HN-CG-DVH"),
    ("Đại học Hà Nội", "HANU", "Km 9 Nguyễn Trãi, Thanh Xuân", 105.7966, 20.9885, "HN-TX-KT"),
    ("Học viện Công nghệ Bưu chính Viễn thông", "PTIT", "Km 10 Nguyễn Trãi, Hà Đông", 105.7875, 20.9807, "HN-HD-ML"),
)

LANDMARKS = (
    ("Công viên Cầu Giấy", Landmark.Type.PARK, "HN-CG-DVH", 105.7900, 21.0307),
    ("Công viên Thống Nhất", Landmark.Type.PARK, "HN-HBT-DT", 105.8439, 21.0116),
    ("Công viên Nhân Chính", Landmark.Type.PARK, "HN-TX-NC", 105.8036, 21.0041),
    ("Bệnh viện Bạch Mai", Landmark.Type.HOSPITAL, "HN-HBT-DT", 105.8393, 21.0009),
    ("Bệnh viện Đại học Y Hà Nội", Landmark.Type.HOSPITAL, "HN-DD-TL", 105.8302, 21.0022),
    ("Bệnh viện 198", Landmark.Type.HOSPITAL, "HN-CG-DVH", 105.7778, 21.0442),
    ("Vincom Center Bà Triệu", Landmark.Type.SHOPPING_MALL, "HN-HBT-DT", 105.8494, 21.0116),
    ("Lotte Center Hà Nội", Landmark.Type.SHOPPING_MALL, "HN-DD-LT", 105.8125, 21.0321),
    ("The Garden Shopping Center", Landmark.Type.SHOPPING_MALL, "HN-NTL-MD2", 105.7781, 21.0168),
    ("Aeon Mall Hà Đông", Landmark.Type.SHOPPING_MALL, "HN-HD-ML", 105.7509, 20.9918),
    ("Trạm bus Xuân Thủy - Đại học Quốc gia", Landmark.Type.BUS_STOP, "HN-CG-DVH", 105.7832, 21.0376),
    ("Trạm bus Cầu Giấy", Landmark.Type.BUS_STOP, "HN-CG-QH", 105.8008, 21.0312),
    ("Trạm bus Giải Phóng - Bạch Mai", Landmark.Type.BUS_STOP, "HN-HBT-DT", 105.8420, 21.0020),
    ("Trạm bus Nguyễn Trãi - Đại học Hà Nội", Landmark.Type.BUS_STOP, "HN-TX-KT", 105.7970, 20.9892),
)

AMENITIES = (
    ("Wifi", "wifi"),
    ("Điều hòa", "air-conditioner"),
    ("Máy giặt", "washing-machine"),
    ("Chỗ để xe", "parking"),
    ("Nhà tắm riêng", "private-bathroom"),
    ("Bếp", "kitchen"),
    ("An ninh", "security"),
    ("Cửa sổ thoáng", "window"),
)

LIFESTYLE_TAGS = (
    ("Yên tĩnh", "quiet"),
    ("Sạch sẽ", "clean"),
    ("Ngủ sớm", "early-sleeper"),
    ("Nấu ăn", "cooking"),
    ("Không hút thuốc", "non-smoking"),
    ("Thân thiện thú cưng", "pet-friendly"),
)

ROOMS = (
    ("Phòng gần Bách Khoa, đủ nội thất", "HN-HBT-BK", "Ngõ 30 Tạ Quang Bửu", 105.8461, 21.0072, "3200000", "22", 2, ("wifi", "air-conditioner", "parking", "private-bathroom")),
    ("Phòng khép kín gần NEU", "HN-HBT-DT", "Ngõ 121 Lê Thanh Nghị", 105.8448, 21.0023, "2800000", "18", 1, ("wifi", "parking", "private-bathroom")),
    ("Căn hộ mini gần VNU Xuân Thủy", "HN-CG-DVH", "Ngõ 68 Cầu Giấy", 105.7904, 21.0328, "4200000", "28", 2, ("wifi", "air-conditioner", "washing-machine", "kitchen")),
    ("Phòng giá tốt khu Quan Hoa", "HN-CG-QH", "Ngõ 79 Cầu Giấy", 105.8018, 21.0310, "2600000", "17", 1, ("wifi", "parking")),
    ("Phòng rộng Nhân Chính phù hợp ở ghép", "HN-TX-NC", "Ngõ 1 Quan Nhân", 105.8031, 21.0052, "3600000", "26", 3, ("wifi", "air-conditioner", "washing-machine", "parking")),
    ("Studio gần Đại học Hà Nội", "HN-TX-KT", "Ngõ 190 Nguyễn Trãi", 105.7978, 20.9891, "3900000", "24", 2, ("wifi", "air-conditioner", "private-bathroom", "kitchen")),
    ("Phòng sinh viên gần PTIT Hà Đông", "HN-HD-ML", "Ngõ 10 Trần Phú Hà Đông", 105.7869, 20.9819, "2400000", "16", 1, ("wifi", "parking")),
    ("Căn hộ mini Mỹ Đình gần The Garden", "HN-NTL-MD2", "Đường Mễ Trì, Mỹ Đình", 105.7794, 21.0180, "4500000", "30", 2, ("wifi", "air-conditioner", "washing-machine", "security")),
    ("Phòng yên tĩnh gần Láng Thượng", "HN-DD-LT", "Ngõ 1194 Đường Láng", 105.8122, 21.0268, "3300000", "21", 2, ("wifi", "window", "parking")),
    ("Phòng gần bệnh viện Bạch Mai", "HN-HBT-DT", "Ngõ 4 Phương Mai", 105.8387, 21.0019, "3000000", "19", 1, ("wifi", "private-bathroom", "security")),
)


def ensure_demo_images():
    media_rooms = Path("media") / "rooms"
    media_rooms.mkdir(parents=True, exist_ok=True)
    source_dir = Path.home() / "Downloads" / "BGround"
    if not source_dir.exists():
        return
    images = sorted(source_dir.glob("*.jpg"))[: len(ROOMS)]
    for index, image in enumerate(images, start=1):
        target = media_rooms / f"demo-hanoi-{index}.jpg"
        if not target.exists():
            shutil.copyfile(image, target)


class Command(BaseCommand):
    help = "Seed Hanoi universities, focused landmarks, rooms, and student profiles for map/recommendation QA."

    @transaction.atomic
    def handle(self, *args, **options):
        ensure_demo_images()
        district_map = {}
        for name, code in DISTRICTS:
            district, _ = District.objects.update_or_create(code=code, defaults={"name": name})
            district_map[code] = district

        ward_map = {}
        for district_code, name, code in WARDS:
            ward, _ = Ward.objects.update_or_create(
                code=code,
                defaults={"district": district_map[district_code], "name": name},
            )
            ward_map[code] = ward

        for name, short_name, address, lng, lat, ward_code in UNIVERSITIES:
            University.objects.update_or_create(
                short_name=short_name,
                defaults={
                    "name": name,
                    "address": address,
                    "location": Point(lng, lat, srid=4326),
                    "is_active": True,
                },
            )
            Landmark.objects.update_or_create(
                name=name,
                defaults={
                    "type": Landmark.Type.UNIVERSITY,
                    "ward": ward_map[ward_code],
                    "location": Point(lng, lat, srid=4326),
                    "is_active": True,
                },
            )

        for name, landmark_type, ward_code, lng, lat in LANDMARKS:
            Landmark.objects.update_or_create(
                name=name,
                defaults={
                    "type": landmark_type,
                    "ward": ward_map[ward_code],
                    "location": Point(lng, lat, srid=4326),
                    "is_active": True,
                },
            )
        Landmark.objects.exclude(
            type__in=[
                Landmark.Type.UNIVERSITY,
                Landmark.Type.BUS_STOP,
                Landmark.Type.HOSPITAL,
                Landmark.Type.PARK,
                Landmark.Type.SHOPPING_MALL,
            ]
        ).update(is_active=False)

        amenity_map = {}
        for name, code in AMENITIES:
            amenity, _ = Amenity.objects.update_or_create(code=code, defaults={"name": name})
            amenity_map[code] = amenity

        tag_map = {}
        for name, code in LIFESTYLE_TAGS:
            tag, _ = LifestyleTag.objects.update_or_create(code=code, defaults={"name": name})
            tag_map[code] = tag

        landlord_user, _ = User.objects.update_or_create(
            email="hanoi.landlord@example.com",
            defaults={
                "full_name": "Chủ trọ Hà Nội Demo",
                "phone": "0909000000",
                "role": User.Role.LANDLORD,
                "is_active": True,
            },
        )
        landlord_user.set_password("demo-password")
        landlord_user.save(update_fields=("password",))
        landlord_profile, _ = LandlordProfile.objects.update_or_create(
            user=landlord_user,
            defaults={"business_name": "Nhà trọ Hà Nội Demo"},
        )

        for index, (title, ward_code, address, lng, lat, price, area, occupants, amenities) in enumerate(ROOMS, start=1):
            room, _ = Room.objects.update_or_create(
                landlord=landlord_profile,
                title=title,
                defaults={
                    "ward": ward_map[ward_code],
                    "description": "Phòng demo tại Hà Nội dùng để kiểm thử tìm kiếm, bản đồ, landmark và gợi ý cá nhân.",
                    "address": address,
                    "location": Point(lng, lat, srid=4326),
                    "location_status": Room.LocationStatus.GEOCODED,
                    "location_query": address,
                    "location_label": address,
                    "price": Decimal(price),
                    "area": Decimal(area),
                    "max_occupants": occupants,
                    "gender_policy": Room.GenderPolicy.ANY,
                    "electricity_price": Decimal("4000"),
                    "water_price": Decimal("100000"),
                    "status": Room.Status.ACTIVE,
                },
            )
            room.amenities.set(amenity_map[code] for code in amenities)
            RoomImage.objects.update_or_create(
                room=room,
                caption="Ảnh minh họa phòng demo",
                defaults={
                    "image": f"rooms/demo-hanoi-{index}.jpg",
                    "uploaded_by": landlord_user,
                    "source": RoomImage.Source.LANDLORD,
                    "status": RoomImage.ModerationStatus.APPROVED,
                    "is_cover": True,
                },
            )

        university_map = {university.short_name: university for university in University.objects.filter(short_name__in=["HUST", "VNU", "HANU"])}
        for email, name, university_code, districts, tags in (
            ("hanoi.student.hust@example.com", "Sinh viên Bách Khoa", "HUST", ("HN-HBT", "HN-DD"), ("quiet", "clean")),
            ("hanoi.student.vnu@example.com", "Sinh viên Quốc gia", "VNU", ("HN-CG",), ("early-sleeper", "non-smoking")),
            ("hanoi.student.hanu@example.com", "Sinh viên Hà Nội", "HANU", ("HN-TX", "HN-HD"), ("cooking", "clean")),
        ):
            user, _ = User.objects.update_or_create(
                email=email,
                defaults={"full_name": name, "phone": "0919000000", "role": User.Role.STUDENT, "is_active": True},
            )
            user.set_password("demo-password")
            user.save(update_fields=("password",))
            profile, _ = StudentProfile.objects.update_or_create(
                user=user,
                defaults={
                    "university": university_map[university_code],
                    "budget_min": Decimal("2000000"),
                    "budget_max": Decimal("4000000"),
                    "max_distance_km": Decimal("4"),
                },
            )
            profile.preferred_districts.set(district_map[code] for code in districts)
            profile.lifestyle_tags.set(tag_map[code] for code in tags)

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded Hanoi demo data: "
                f"{District.objects.filter(code__startswith='HN-').count()} districts, "
                f"{Ward.objects.filter(code__startswith='HN-').count()} wards, "
                f"{University.objects.count()} universities, "
                f"{Landmark.objects.count()} landmarks, "
                f"{Room.objects.filter(landlord=landlord_profile).count()} Hanoi rooms."
            )
        )
