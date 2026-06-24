from decimal import Decimal

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import LandlordProfile, StudentProfile, User
from apps.listings.models import Amenity, Room
from apps.locations.models import District, University, Ward
from apps.roommates.models import LifestyleTag, RoommatePost


DISTRICTS = (
    ("Đống Đa", "DD"),
    ("Hai Bà Trưng", "HBT"),
    ("Cầu Giấy", "CG"),
    ("Thanh Xuân", "TX"),
)

WARDS = (
    ("DD", "Phường Bạch Mai", "DD-BM"),
    ("DD", "Phường Trung Liệt", "DD-TL"),
    ("HBT", "Phường Bách Khoa", "HBT-BK"),
    ("HBT", "Phường Đồng Tâm", "HBT-DT"),
    ("CG", "Phường Dịch Vọng Hậu", "CG-DVH"),
    ("CG", "Phường Quan Hoa", "CG-QH"),
    ("TX", "Phường Nhân Chính", "TX-NC"),
    ("TX", "Phường Khương Trung", "TX-KT"),
)

UNIVERSITIES = (
    ("Đại học Bách khoa Hà Nội", "HUST", "1 Đại Cồ Việt, Hai Bà Trưng", 105.8435, 21.0059),
    ("Đại học Kinh tế Quốc dân", "NEU", "207 Giải Phóng, Hai Bà Trưng", 105.8420, 21.0007),
    ("Đại học Xây dựng Hà Nội", "HUCE", "55 Giải Phóng, Hai Bà Trưng", 105.8428, 21.0037),
    ("Đại học Quốc gia Hà Nội", "VNU", "144 Xuân Thủy, Cầu Giấy", 105.7829, 21.0379),
    ("Học viện Báo chí và Tuyên truyền", "AJC", "36 Xuân Thủy, Cầu Giấy", 105.7850, 21.0375),
)

AMENITIES = (
    ("Wifi", "wifi"),
    ("Điều hòa", "air-conditioner"),
    ("Máy giặt", "washing-machine"),
    ("Chỗ để xe", "parking"),
    ("Nhà tắm riêng", "private-bathroom"),
    ("Bếp", "kitchen"),
)

LIFESTYLE_TAGS = (
    ("Yên tĩnh", "quiet"),
    ("Ngủ sớm", "early-sleeper"),
    ("Sạch sẽ", "clean"),
    ("Nấu ăn", "cooking"),
    ("Không hút thuốc", "non-smoking"),
    ("Thân thiện thú cưng", "pet-friendly"),
)

ROOMS = (
    {
        "title": "Phòng trọ gần Bách Khoa, đầy đủ nội thất",
        "ward_code": "HBT-BK",
        "address": "Ngõ 30 Tạ Quang Bửu, Hai Bà Trưng",
        "lng": 105.8461,
        "lat": 21.0072,
        "price": "3200000",
        "area": "22",
        "max_occupants": 2,
        "amenities": ("wifi", "air-conditioner", "parking", "private-bathroom"),
    },
    {
        "title": "Phòng khép kín gần NEU, giờ giấc tự do",
        "ward_code": "HBT-DT",
        "address": "Ngõ 121 Lê Thanh Nghị, Hai Bà Trưng",
        "lng": 105.8448,
        "lat": 21.0023,
        "price": "2800000",
        "area": "18",
        "max_occupants": 1,
        "amenities": ("wifi", "parking", "private-bathroom"),
    },
    {
        "title": "Căn hộ mini Dịch Vọng Hậu gần Cầu Giấy",
        "ward_code": "CG-DVH",
        "address": "Ngõ 68 Cầu Giấy, Cầu Giấy",
        "lng": 105.7904,
        "lat": 21.0328,
        "price": "4200000",
        "area": "28",
        "max_occupants": 2,
        "amenities": ("wifi", "air-conditioner", "washing-machine", "kitchen"),
    },
    {
        "title": "Phòng trọ giá tốt gần Đại học Quốc gia",
        "ward_code": "CG-QH",
        "address": "Ngõ 79 Cầu Giấy, Cầu Giấy",
        "lng": 105.7856,
        "lat": 21.0367,
        "price": "2500000",
        "area": "16",
        "max_occupants": 1,
        "amenities": ("wifi", "parking"),
    },
    {
        "title": "Phòng rộng Nhân Chính phù hợp ở ghép",
        "ward_code": "TX-NC",
        "address": "Ngõ 1 Quan Nhân, Thanh Xuân",
        "lng": 105.8031,
        "lat": 21.0052,
        "price": "3600000",
        "area": "26",
        "max_occupants": 3,
        "amenities": ("wifi", "air-conditioner", "washing-machine", "parking"),
    },
)

STUDENTS = (
    ("student.hust@example.com", "Nguyễn Minh Anh", "0911000001", "HUST", ("DD", "HBT"), ("quiet", "clean", "non-smoking")),
    ("student.neu@example.com", "Trần Hoàng Nam", "0911000002", "NEU", ("HBT",), ("cooking", "clean")),
    ("student.vnu@example.com", "Lê Phương Linh", "0911000003", "VNU", ("CG",), ("quiet", "early-sleeper")),
)

ROOMMATE_POSTS = (
    {
        "email": "student.hust@example.com",
        "type": RoommatePost.Type.LOOKING_TOGETHER,
        "title": "Tìm 1 bạn nữ ghép trọ gần Bách Khoa",
        "description": "Ưu tiên bạn sạch sẽ, giờ giấc ổn định, ngân sách mỗi người khoảng 2-3 triệu.",
        "university": "HUST",
        "districts": ("HBT", "DD"),
        "budget_min": "1800000",
        "budget_max": "3200000",
        "available_slots": 1,
        "max_roommates": 2,
        "current_occupants": 1,
        "gender_preference": RoommatePost.GenderPreference.FEMALE,
        "tags": ("quiet", "clean", "non-smoking"),
    },
    {
        "email": "student.neu@example.com",
        "type": RoommatePost.Type.HAS_ROOM,
        "title": "Đã có phòng gần NEU, cần thêm 1 bạn ở cùng",
        "description": "Phòng khép kín, chia tiền rõ ràng, ưu tiên bạn tôn trọng không gian chung.",
        "university": "NEU",
        "ward": "HBT-DT",
        "address": "Ngõ 121 Lê Thanh Nghị, Hai Bà Trưng",
        "budget_min": "1400000",
        "budget_max": "1800000",
        "available_slots": 1,
        "max_roommates": 2,
        "current_occupants": 1,
        "gender_preference": RoommatePost.GenderPreference.ANY,
        "tags": ("cooking", "clean"),
    },
    {
        "email": "student.vnu@example.com",
        "type": RoommatePost.Type.LOOKING_TOGETHER,
        "title": "Tìm bạn cùng thuê phòng khu Cầu Giấy",
        "description": "Muốn tìm phòng quanh Xuân Thủy, ưu tiên yên tĩnh để học bài.",
        "university": "VNU",
        "districts": ("CG",),
        "budget_min": "2000000",
        "budget_max": "3500000",
        "available_slots": 2,
        "max_roommates": 3,
        "current_occupants": 1,
        "gender_preference": RoommatePost.GenderPreference.ANY,
        "tags": ("quiet", "early-sleeper"),
    },
)


class Command(BaseCommand):
    help = "Seed demo data for the first room-search prototype."

    @transaction.atomic
    def handle(self, *args, **options):
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

        for name, short_name, address, lng, lat in UNIVERSITIES:
            University.objects.update_or_create(
                short_name=short_name,
                defaults={
                    "name": name,
                    "address": address,
                    "location": Point(lng, lat, srid=4326),
                    "is_active": True,
                },
            )

        amenity_map = {}
        for name, code in AMENITIES:
            amenity, _ = Amenity.objects.update_or_create(code=code, defaults={"name": name})
            amenity_map[code] = amenity

        lifestyle_tag_map = {}
        for name, code in LIFESTYLE_TAGS:
            tag, _ = LifestyleTag.objects.update_or_create(code=code, defaults={"name": name})
            lifestyle_tag_map[code] = tag

        landlord_user, _ = User.objects.update_or_create(
            email="landlord.demo@example.com",
            defaults={
                "full_name": "Chủ trọ demo",
                "phone": "0900000000",
                "role": User.Role.LANDLORD,
                "is_active": True,
            },
        )
        landlord_user.set_password("demo-password")
        landlord_user.save(update_fields=("password",))
        landlord_profile, _ = LandlordProfile.objects.update_or_create(
            user=landlord_user,
            defaults={
                "business_name": "Nhà trọ demo",
                "verification_status": LandlordProfile.VerificationStatus.APPROVED,
            },
        )

        for item in ROOMS:
            room, _ = Room.objects.update_or_create(
                landlord=landlord_profile,
                title=item["title"],
                defaults={
                    "ward": ward_map[item["ward_code"]],
                    "description": "Phòng mẫu phục vụ trải nghiệm tìm trọ cho sinh viên.",
                    "address": item["address"],
                    "location": Point(item["lng"], item["lat"], srid=4326),
                    "location_status": Room.LocationStatus.GEOCODED,
                    "location_query": item["address"],
                    "location_label": item["address"],
                    "price": Decimal(item["price"]),
                    "area": Decimal(item["area"]),
                    "max_occupants": item["max_occupants"],
                    "gender_policy": Room.GenderPolicy.ANY,
                    "electricity_price": Decimal("4000"),
                    "water_price": Decimal("100000"),
                    "status": Room.Status.ACTIVE,
                },
            )
            room.amenities.set(amenity_map[code] for code in item["amenities"])

        university_map = {university.short_name: university for university in University.objects.all()}
        student_map = {}
        for email, full_name, phone, university_short_name, district_codes, tag_codes in STUDENTS:
            user, _ = User.objects.update_or_create(
                email=email,
                defaults={
                    "full_name": full_name,
                    "phone": phone,
                    "role": User.Role.STUDENT,
                    "is_active": True,
                },
            )
            user.set_password("demo-password")
            user.save(update_fields=("password",))
            profile, _ = StudentProfile.objects.update_or_create(
                user=user,
                defaults={
                    "university": university_map[university_short_name],
                    "budget_min": Decimal("1500000"),
                    "budget_max": Decimal("3500000"),
                    "max_distance_km": Decimal("5"),
                },
            )
            profile.preferred_districts.set(district_map[code] for code in district_codes)
            profile.lifestyle_tags.set(lifestyle_tag_map[code] for code in tag_codes)
            student_map[email] = user

        for item in ROOMMATE_POSTS:
            post, _ = RoommatePost.objects.update_or_create(
                posted_by=student_map[item["email"]],
                title=item["title"],
                defaults={
                    "type": item["type"],
                    "status": RoommatePost.Status.ACTIVE,
                    "description": item["description"],
                    "university": university_map[item["university"]],
                    "ward": ward_map.get(item.get("ward")),
                    "address": item.get("address", ""),
                    "budget_min": Decimal(item["budget_min"]),
                    "budget_max": Decimal(item["budget_max"]),
                    "available_slots": item["available_slots"],
                    "max_roommates": item["max_roommates"],
                    "current_occupants": item["current_occupants"],
                    "gender_preference": item["gender_preference"],
                    "contact_phone": student_map[item["email"]].phone,
                },
            )
            post.preferred_districts.set(district_map[code] for code in item.get("districts", ()))
            post.lifestyle_tags.set(lifestyle_tag_map[code] for code in item["tags"])

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded demo data: "
                f"{District.objects.count()} districts, "
                f"{Ward.objects.count()} wards, "
                f"{University.objects.count()} universities, "
                f"{Amenity.objects.count()} amenities, "
                f"{Room.objects.count()} rooms, "
                f"{LifestyleTag.objects.count()} lifestyle tags, "
                f"{RoommatePost.objects.count()} roommate posts."
            )
        )
