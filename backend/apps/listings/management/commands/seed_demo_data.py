from decimal import Decimal

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import LandlordProfile, StudentProfile, User
from apps.listings.models import Amenity, Room
from apps.locations.models import District, University, Ward
from apps.roommates.models import LifestyleTag, RoommatePost


DISTRICTS = (
    ("Dong Da", "DD"),
    ("Hai Ba Trung", "HBT"),
    ("Cau Giay", "CG"),
    ("Thanh Xuan", "TX"),
)

WARDS = (
    ("DD", "Phuong Bach Mai", "DD-BM"),
    ("DD", "Phuong Trung Liet", "DD-TL"),
    ("HBT", "Phuong Bach Khoa", "HBT-BK"),
    ("HBT", "Phuong Dong Tam", "HBT-DT"),
    ("CG", "Phuong Dich Vong Hau", "CG-DVH"),
    ("CG", "Phuong Quan Hoa", "CG-QH"),
    ("TX", "Phuong Nhan Chinh", "TX-NC"),
    ("TX", "Phuong Khuong Trung", "TX-KT"),
)

UNIVERSITIES = (
    ("Dai hoc Bach khoa Ha Noi", "HUST", "1 Dai Co Viet, Hai Ba Trung", 105.8435, 21.0059),
    ("Dai hoc Kinh te Quoc dan", "NEU", "207 Giai Phong, Hai Ba Trung", 105.8420, 21.0007),
    ("Dai hoc Xay dung Ha Noi", "HUCE", "55 Giai Phong, Hai Ba Trung", 105.8428, 21.0037),
    ("Dai hoc Quoc gia Ha Noi", "VNU", "144 Xuan Thuy, Cau Giay", 105.7829, 21.0379),
    ("Hoc vien Bao chi va Tuyen truyen", "AJC", "36 Xuan Thuy, Cau Giay", 105.7850, 21.0375),
)

AMENITIES = (
    ("Wifi", "wifi"),
    ("Dieu hoa", "air-conditioner"),
    ("May giat", "washing-machine"),
    ("Cho de xe", "parking"),
    ("Nha tam rieng", "private-bathroom"),
    ("Bep", "kitchen"),
)

LIFESTYLE_TAGS = (
    ("Yen tinh", "quiet"),
    ("Ngu som", "early-sleeper"),
    ("Sach se", "clean"),
    ("Nau an", "cooking"),
    ("Khong hut thuoc", "non-smoking"),
    ("Than thien thu cung", "pet-friendly"),
)

ROOMS = (
    {
        "title": "Phong tro gan Bach khoa, day du noi that",
        "ward_code": "HBT-BK",
        "address": "Ngo 30 Ta Quang Buu, Hai Ba Trung",
        "lng": 105.8461,
        "lat": 21.0072,
        "price": "3200000",
        "area": "22",
        "max_occupants": 2,
        "amenities": ("wifi", "air-conditioner", "parking", "private-bathroom"),
    },
    {
        "title": "Phong khep kin gan NEU, gio giac tu do",
        "ward_code": "HBT-DT",
        "address": "Ngo 121 Le Thanh Nghi, Hai Ba Trung",
        "lng": 105.8448,
        "lat": 21.0023,
        "price": "2800000",
        "area": "18",
        "max_occupants": 1,
        "amenities": ("wifi", "parking", "private-bathroom"),
    },
    {
        "title": "Can ho mini Dich Vong Hau gan Cau Giay",
        "ward_code": "CG-DVH",
        "address": "Ngo 68 Cau Giay, Cau Giay",
        "lng": 105.7904,
        "lat": 21.0328,
        "price": "4200000",
        "area": "28",
        "max_occupants": 2,
        "amenities": ("wifi", "air-conditioner", "washing-machine", "kitchen"),
    },
    {
        "title": "Phong tro gia tot gan Dai hoc Quoc gia",
        "ward_code": "CG-QH",
        "address": "Ngo 79 Cau Giay, Cau Giay",
        "lng": 105.7856,
        "lat": 21.0367,
        "price": "2500000",
        "area": "16",
        "max_occupants": 1,
        "amenities": ("wifi", "parking"),
    },
    {
        "title": "Phong rong Nhan Chinh phu hop o ghep",
        "ward_code": "TX-NC",
        "address": "Ngo 1 Quan Nhan, Thanh Xuan",
        "lng": 105.8031,
        "lat": 21.0052,
        "price": "3600000",
        "area": "26",
        "max_occupants": 3,
        "amenities": ("wifi", "air-conditioner", "washing-machine", "parking"),
    },
)

STUDENTS = (
    ("student.hust@example.com", "Nguyen Minh Anh", "0911000001", "HUST", ("DD", "HBT"), ("quiet", "clean", "non-smoking")),
    ("student.neu@example.com", "Tran Hoang Nam", "0911000002", "NEU", ("HBT",), ("cooking", "clean")),
    ("student.vnu@example.com", "Le Phuong Linh", "0911000003", "VNU", ("CG",), ("quiet", "early-sleeper")),
)

ROOMMATE_POSTS = (
    {
        "email": "student.hust@example.com",
        "type": RoommatePost.Type.LOOKING_TOGETHER,
        "title": "Tim 1 ban nu ghep tro gan Bach khoa",
        "description": "Uu tien ban sach se, gio giac on dinh, ngan sach moi nguoi khoang 2-3 trieu.",
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
        "title": "Da co phong gan NEU can them 1 ban o cung",
        "description": "Phong khep kin, chia tien ro rang, uu tien ban ton trong khong gian chung.",
        "university": "NEU",
        "ward": "HBT-DT",
        "address": "Ngo 121 Le Thanh Nghi, Hai Ba Trung",
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
        "title": "Tim ban cung thue phong khu Cau Giay",
        "description": "Muon tim phong quanh Xuan Thuy, uu tien yen tinh de hoc bai.",
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
                "full_name": "Chu tro demo",
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
                "business_name": "Nha tro demo",
                "verification_status": LandlordProfile.VerificationStatus.APPROVED,
            },
        )

        for item in ROOMS:
            room, _ = Room.objects.update_or_create(
                landlord=landlord_profile,
                title=item["title"],
                defaults={
                    "ward": ward_map[item["ward_code"]],
                    "description": "Phong demo phuc vu prototype tim tro cho sinh vien.",
                    "address": item["address"],
                    "location": Point(item["lng"], item["lat"], srid=4326),
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

