# Student Housing Backend

Backend Django cho ung dung tim va goi y phong tro cho sinh vien.

## Cau truc

```text
backend/   Django API, auth, dashboard, database models va server-side views
frontend/  Template va static asset cua giao dien public tim phong
```

Backend van render cac template public qua `apps.frontend.views`, nhung file HTML/CSS/JS cua giao dien public duoc dat ngoai thu muc `backend` de de quan ly rieng.

## Pham vi hien tai

- Custom user dang nhap bang email, vai tro `student`, `landlord`, `admin`.
- Ho so sinh vien va chu tro.
- Du lieu dia ly dung GeoDjango/PostGIS: quan, phuong, truong dai hoc, landmark.
- Phong tro, tien ich, anh phong va quy trinh duyet bai.
- API tim kiem cong khai theo gia, dien tich, tien ich, dia ban, van ban va khoang cach den truong.
- Token authentication cho API.
- Favorite, event tracking, search log va recommendation MVP cho sinh vien da dang nhap.

## Yeu cau

- Python 3.12+
- PostgreSQL 15+ voi PostGIS, hoac Docker de khoi dong database local
- GDAL va GEOS native libraries de GeoDjango khoi dong. Tren Windows co the cai qua OSGeo4W va cau hinh `GDAL_LIBRARY_PATH` neu Django khong tu nhan dien duoc.

## Cai dat local

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
python manage.py configure_oauth
python manage.py createsuperuser
python manage.py runserver
```

Bien moi truong trong `.env` can duoc nap vao terminal hoac cau hinh bang cong cu chay ung dung. Du an doc truc tiep cac bien `DJANGO_*` va `POSTGRES_*`.

## Kiem tra va test

Chay bang virtualenv Python 3.12 cua du an:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

Django can tao database test PostGIS, mac dinh la `test_student_housing` hoac gia tri `POSTGRES_TEST_DB`.
User PostgreSQL trong `POSTGRES_USER` can co quyen `CREATEDB`, hoac database test can duoc tao san va chay test voi `--keepdb`.

## API ban dau

Prototype frontend co san tai:

```text
http://127.0.0.1:8000/
```

Dashboard web:

```text
http://127.0.0.1:8000/dashboard/landlord/
http://127.0.0.1:8000/dashboard/moderation/
```

| Endpoint | Chuc nang |
|---|---|
| `POST /api/auth/register/` | Dang ky sinh vien hoac chu tro |
| `POST /api/auth/login/` | Lay authentication token |
| `GET /auth/login/` | Trang dang nhap web |
| `GET /auth/register/` | Trang dang ky web |
| `GET /auth/profile/` | Ho so web |
| `GET /dashboard/landlord/` | Dashboard chu tro |
| `GET /dashboard/moderation/` | Dashboard admin kiem duyet |
| `GET /accounts/google/login/` | OAuth Google qua django-allauth |
| `GET /accounts/facebook/login/` | OAuth Facebook qua django-allauth |
| `GET/PATCH /api/auth/me/` | Xem/sua tai khoan dang nhap |
| `GET/PATCH /api/auth/student-preferences/` | Nhu cau ngan sach/truong cua sinh vien |
| `GET /api/districts/`, `/api/wards/`, `/api/universities/` | Du lieu tham chieu |
| `GET /api/rooms/` | Danh sach phong active va bo loc |
| `POST /api/rooms/{id}/favorite/` | Luu phong yeu thich |
| `DELETE /api/rooms/{id}/unfavorite/` | Bo luu phong yeu thich |
| `POST /api/rooms/{id}/contact/` | Ghi nhan click lien he va tra thong tin chu tro |
| `GET /api/favorites/` | Danh sach phong yeu thich cua user |
| `POST /api/events/` | Ghi event hanh vi |
| `POST /api/search-logs/` | Ghi log tim kiem |
| `GET /api/recommendations/` | Goi y phong MVP cho sinh vien da dang nhap |
| `POST /api/rooms/` | Chu tro da xac minh tao phong nhap |
| `GET /api/rooms/mine/` | Chu tro xem cac phong cua minh |
| `POST /api/rooms/{id}/submit/` | Gui phong cho admin duyet |
| `POST /api/rooms/{id}/approve/` | Admin phe duyet phong |
| `POST /api/rooms/{id}/reject/` | Admin tu choi phong |

Vi du bo loc:

```text
GET /api/rooms/?min_price=1500000&max_price=3500000&amenity=1&university=1&max_distance_km=3
```

Phong dang cong khai se quay lai trang thai cho duyet khi chu tro sua noi dung, gia, toa do hoac tien ich.

## Buoc tiep theo

- Mo dashboard chu tro de dang phong bang giao dien web.
- Bo sung upload anh va workflow admin duyet phong tren giao dien.
- Nang cap recommendation bang so thich tien ich va du lieu hanh vi that.

## OAuth Google/Facebook

Dang nhap Google/Facebook dung `django-allauth`. Can tao OAuth app tren Google/Facebook va them `Social application` trong Django admin:

- Provider: `Google` hoac `Facebook`
- Client id / Secret key: lay tu provider
- Sites: chon site local `127.0.0.1:8000` hoac domain production

Callback local:

```text
http://127.0.0.1:8000/accounts/google/login/callback/
http://127.0.0.1:8000/accounts/facebook/login/callback/
```

Co the cau hinh bang bien moi truong thay vi nhap tay trong admin:

```powershell
$env:GOOGLE_OAUTH_CLIENT_ID = "..."
$env:GOOGLE_OAUTH_CLIENT_SECRET = "..."
$env:FACEBOOK_OAUTH_CLIENT_ID = "..."
$env:FACEBOOK_OAUTH_CLIENT_SECRET = "..."
python manage.py configure_oauth
```
