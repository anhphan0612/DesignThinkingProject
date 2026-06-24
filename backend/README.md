# Rentify

Rentify là ứng dụng hỗ trợ sinh viên tìm phòng trọ và tìm người ở ghép quanh trường đại học. Dự án hiện dùng Django/DRF cho backend, server-rendered templates cho các flow web chính và phần frontend public đặt ở thư mục `frontend/` cùng cấp với `backend/`.

## Trạng Thái Hiện Tại

Sản phẩm đang ở mức prototype nâng cao, có đủ flow chính để chạy thử end-to-end trên local:

- Người dùng đăng ký/đăng nhập theo vai trò `student`, `landlord`, `admin`.
- Sinh viên sau đăng ký có flow nhập nguyện vọng, có thể bỏ qua và đi thẳng tới trang tìm phòng.
- Trang tìm phòng có bộ lọc, gợi ý cá nhân hóa, lưu phòng yêu thích, thông tin liên hệ và bản đồ tương tác.
- Chủ trọ có dashboard riêng, tạo/sửa/xem trước/gửi duyệt phòng, upload ảnh local và quản lý ảnh bìa.
- Admin có dashboard kiểm duyệt phòng, ảnh và báo cáo nội dung.
- Dữ liệu địa lý dùng GeoDjango/PostGIS: quận, phường, trường đại học, landmark và tọa độ phòng.
- Recommendation MVP dựa trên hồ sơ sinh viên, ngân sách, trường, khu vực, khoảng cách, tiện ích, landmark và từ khóa tìm kiếm.
- Tìm người ở ghép có hồ sơ thói quen sống, bài đăng, match cơ bản và API quản lý bài của sinh viên.

Ứng dụng không xử lý xác minh pháp lý, hợp đồng thuê, đặt cọc, thanh toán hoặc pass phòng. Định hướng hiện tại là nền tảng hỗ trợ tìm trọ, tìm người ở ghép và kết nối với chủ trọ.

## Cấu Trúc

```text
backend/   Django project, apps, API, templates auth/dashboard, media local
frontend/  Templates và static assets cho giao diện public
media/     Dữ liệu media local ở workspace, dùng khi chạy thử
```

Backend render các trang public qua `apps.frontend.views`, nhưng template/static public nằm ngoài `backend` để sau này dễ tách hoặc thay frontend framework nếu cần.

## Yêu Cầu

- Python 3.12+ hoặc bản Python đang dùng trong virtualenv của dự án.
- PostgreSQL 15+ có PostGIS.
- GDAL và GEOS cho GeoDjango. Trên Windows có thể cài qua OSGeo4W rồi cấu hình `GDAL_LIBRARY_PATH` và `GEOS_LIBRARY_PATH` nếu Django không tự nhận.
- Docker Desktop nếu muốn chạy database local bằng `compose.yaml`.

Các thư viện Python chính nằm trong `requirements.txt`:

```text
Django 5.2
Django REST Framework
django-allauth
psycopg
Pillow
```

Map frontend dùng Leaflet + OpenStreetMap qua CDN. Nếu CDN không tải được, UI có fallback map nội bộ để không vỡ trang.

## Cài Đặt Local

Chạy trong PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d db
python manage.py migrate
python manage.py seed_districts
python manage.py seed_amenities
python manage.py seed_demo_data
python manage.py seed_hanoi_demo_data
python manage.py configure_oauth
python manage.py createsuperuser
python manage.py runserver
```

Mở ứng dụng tại:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/rooms/
http://127.0.0.1:8000/roommates/
http://127.0.0.1:8000/landlord/
```

Nếu chỉ muốn chạy thử nhanh sau khi đã setup database:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py seed_hanoi_demo_data
python manage.py runserver 127.0.0.1:8000
```

## Dữ Liệu Demo Hà Nội

Lệnh `seed_hanoi_demo_data` tạo dữ liệu đủ lớn để kiểm thử map, landmark và recommendation:

- 6 quận, 10 phường.
- 8 trường đại học tại Hà Nội.
- Landmark trọng tâm: công viên, trường đại học, trạm xe bus, bệnh viện và trung tâm thương mại lớn.
- 10 phòng trọ demo có tọa độ, tiện ích, giá, diện tích và ảnh.
- 3 hồ sơ sinh viên demo phục vụ gợi ý cá nhân hóa.

Ảnh phòng demo được lấy tạm từ:

```text
C:\Users\demod\Downloads\BGround
```

Khi chạy seed, ảnh `.jpg` trong thư mục này sẽ được copy vào `backend/media/rooms/demo-hanoi-*.jpg` nếu file đích chưa tồn tại.

Tài khoản demo do seed tạo:

```text
hanoi.landlord@example.com / demo-password
hanoi.student.hust@example.com / demo-password
hanoi.student.vnu@example.com / demo-password
hanoi.student.hanu@example.com / demo-password
```

## Flow Chính

### Sinh viên

1. Đăng ký tài khoản sinh viên.
2. Nhập nguyện vọng tìm phòng hoặc bỏ qua.
3. Vào trang tìm phòng, dùng bộ lọc và từ khóa.
4. Xem gợi ý cá nhân hóa, lý do gợi ý, landmark gần phòng và bản đồ.
5. Lưu phòng yêu thích hoặc xem thông tin liên hệ chủ trọ.
6. Dùng trang ghép trọ để tìm bài đăng phù hợp theo trường, ngân sách, khu vực và thói quen sống.

### Chủ trọ

1. Đăng ký hoặc đăng nhập bằng vai trò chủ trọ.
2. Vào dashboard riêng qua logo/topbar.
3. Tạo phòng với địa chỉ dạng text; hệ thống cố gắng geocode sang tọa độ.
4. Upload ảnh local, chọn ảnh bìa và xem trước trang công khai.
5. Gửi phòng cho admin duyệt.
6. Phòng đang công khai sẽ quay lại trạng thái cần duyệt nếu chủ trọ sửa nội dung quan trọng.

Chủ trọ không thấy các chức năng không cần thiết như tìm phòng hoặc ghép phòng trong topbar khi đã đăng nhập.

### Admin

1. Xem danh sách phòng, ảnh và báo cáo cần xử lý.
2. Duyệt hoặc từ chối phòng.
3. Duyệt hoặc từ chối ảnh phòng.
4. Xử lý báo cáo nội dung.

## Business Rules Đáng Chú Ý

- Phòng chỉ được gửi duyệt khi có vị trí đã map, giá/diện tích/số người hợp lệ và ít nhất một ảnh đã duyệt.
- Ảnh phòng local chỉ nhận JPG/PNG/WebP, giới hạn bởi `RENTIFY_MAX_ROOM_IMAGE_SIZE_MB` và `RENTIFY_ROOM_IMAGE_LIMIT`.
- Khi chủ trọ sửa phòng đang active, phòng sẽ cần được duyệt lại.
- Recommendation không chỉ dựa vào từ khóa. Nếu người dùng nhập từ khóa lạ, hệ thống vẫn dùng hồ sơ, khoảng cách, giá, khu vực và tiện ích để fallback.
- Vĩ độ/kinh độ không còn là thông tin chính trên UI public; bản đồ và địa chỉ/landmark là bề mặt hiển thị quan trọng hơn.

## Kiểm Tra Và Test

Chạy kiểm tra hệ thống:

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test --keepdb
```

Nếu chạy test lần đầu, PostgreSQL user trong `.env` cần có quyền tạo test database PostGIS, hoặc cần tạo sẵn database test theo `POSTGRES_TEST_DB`.

Kiểm tra nhanh frontend local:

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Sau đó mở:

```text
http://127.0.0.1:8000/rooms/
http://127.0.0.1:8000/roommates/
http://127.0.0.1:8000/auth/login/
http://127.0.0.1:8000/auth/profile/
http://127.0.0.1:8000/dashboard/landlord/
http://127.0.0.1:8000/dashboard/moderation/
```

Các file JavaScript public có thể kiểm tra syntax bằng Node:

```powershell
node --check ..\frontend\static\frontend\app.js
node --check ..\frontend\static\frontend\detail-map.js
node --check ..\frontend\static\frontend\roommates.js
```

## API Chính

| Endpoint | Chức năng |
|---|---|
| `POST /api/auth/register/` | Đăng ký sinh viên hoặc chủ trọ |
| `POST /api/auth/login/` | Lấy authentication token |
| `GET/PATCH /api/auth/me/` | Xem/sửa tài khoản đang đăng nhập |
| `GET/PATCH /api/auth/student-preferences/` | Xem/sửa nguyện vọng sinh viên |
| `GET /api/districts/` | Danh sách quận |
| `GET /api/wards/` | Danh sách phường |
| `GET /api/universities/` | Danh sách trường đại học |
| `GET /api/landmarks/` | Landmark Hà Nội phục vụ map/recommendation |
| `GET /api/amenities/` | Tiện ích phòng |
| `GET /api/rooms/` | Danh sách phòng active và bộ lọc |
| `POST /api/rooms/` | Chủ trọ tạo phòng |
| `GET /api/rooms/mine/` | Chủ trọ xem phòng của mình |
| `POST /api/rooms/{id}/submit/` | Chủ trọ gửi phòng để duyệt |
| `POST /api/rooms/{id}/approve/` | Admin duyệt phòng |
| `POST /api/rooms/{id}/reject/` | Admin từ chối phòng |
| `POST /api/rooms/{id}/favorite/` | Lưu phòng yêu thích |
| `DELETE /api/rooms/{id}/unfavorite/` | Bỏ lưu phòng yêu thích |
| `GET /api/favorites/` | Danh sách phòng yêu thích |
| `POST /api/rooms/{id}/contact/` | Ghi nhận click liên hệ và trả thông tin chủ trọ |
| `GET /api/recommendations/` | Gợi ý phòng cho sinh viên đã đăng nhập |
| `GET /api/lifestyle-tags/` | Thói quen sống |
| `GET /api/roommate-posts/` | Danh sách bài ghép trọ active |
| `POST /api/roommate-posts/` | Sinh viên tạo bài ghép trọ |
| `GET /api/roommate-posts/mine/` | Sinh viên xem bài ghép trọ của mình |
| `GET /api/roommate-posts/matches/` | Gợi ý bài ghép trọ phù hợp |
| `POST /api/roommate-posts/{id}/close/` | Đóng bài ghép trọ |
| `POST /api/events/` | Ghi event hành vi |
| `POST /api/search-logs/` | Ghi log tìm kiếm |
| `POST /api/reports/` | Báo cáo nội dung |

Ví dụ lọc phòng:

```text
GET /api/rooms/?min_price=1500000&max_price=3500000&amenity=1&university=1&max_distance_km=3&q=gan bach khoa
```

Ví dụ lấy gợi ý có xét từ khóa:

```text
GET /api/recommendations/?q=yen tinh gan truong&limit=10
```

## Web Routes Chính

| Route | Chức năng |
|---|---|
| `/` | Trang giới thiệu cho guest |
| `/rooms/` | Tìm phòng |
| `/rooms/<id>/` | Chi tiết phòng |
| `/roommates/` | Tìm người ở ghép |
| `/landlord/` | Trang giới thiệu cho chủ trọ chưa đăng nhập |
| `/auth/login/` | Đăng nhập |
| `/auth/register/` | Đăng ký |
| `/auth/preferences/` | Onboarding nhập nguyện vọng |
| `/auth/profile/` | Hồ sơ người dùng |
| `/dashboard/landlord/` | Dashboard chủ trọ |
| `/dashboard/moderation/` | Dashboard admin |

## Biến Môi Trường

Các biến chính nằm trong `.env.example`.

- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_TEST_DB`
- `GDAL_LIBRARY_PATH`, `GEOS_LIBRARY_PATH` nếu cần trên Windows
- `DJANGO_EMAIL_*` cho email reset mật khẩu
- `RENTIFY_MAX_ROOM_IMAGE_SIZE_MB`, `RENTIFY_ROOM_IMAGE_LIMIT`, `RENTIFY_ALLOWED_ROOM_IMAGE_TYPES`
- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `FACEBOOK_OAUTH_CLIENT_ID`, `FACEBOOK_OAUTH_CLIENT_SECRET`

Local mặc định dùng email backend console.

## OAuth Google/Facebook

Đăng nhập Google/Facebook dùng `django-allauth`. Cần tạo OAuth app trên provider và thêm `Social application` trong Django admin:

- Provider: `Google` hoặc `Facebook`
- Client id / Secret key: lấy từ provider
- Sites: chọn site local `127.0.0.1:8000` hoặc domain production

Callback local:

```text
http://127.0.0.1:8000/accounts/google/login/callback/
http://127.0.0.1:8000/accounts/facebook/login/callback/
```

Có thể cấu hình bằng biến môi trường rồi chạy:

```powershell
$env:GOOGLE_OAUTH_CLIENT_ID = "..."
$env:GOOGLE_OAUTH_CLIENT_SECRET = "..."
$env:FACEBOOK_OAUTH_CLIENT_ID = "..."
$env:FACEBOOK_OAUTH_CLIENT_SECRET = "..."
python manage.py configure_oauth
```

## Giới Hạn Hiện Tại

- Ảnh phòng đang lưu local, chưa tích hợp cloud storage.
- Geocoding text sang tọa độ đang phục vụ demo/local, chưa thay bằng provider bản đồ production.
- Frontend hiện vẫn là template + JavaScript thuần; đủ để prototype nhưng nếu product mở rộng mạnh có thể cân nhắc React/Vue/Svelte hoặc htmx tùy định hướng.
- Chưa có chat real-time; thông tin liên hệ đang là flow kết nối đơn giản.
- Chưa có test tự động trực quan bằng browser/screenshot cho toàn bộ UI.

## Sprint Tiếp Theo Gợi Ý

- QA giao diện thực tế trên desktop/mobile bằng browser và screenshot.
- Hoàn thiện hardening nghiệp vụ cho dashboard chủ trọ, upload ảnh và trạng thái duyệt.
- Bổ sung cloud storage cho ảnh phòng.
- Chuẩn hóa map/geocoding production.
- Mở rộng dữ liệu Hà Nội và đánh giá chất lượng recommendation bằng bộ test thực tế.
