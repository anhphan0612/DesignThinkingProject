# DesignThinkingProject
1. Các chức năng chính

# Dành cho sinh viên (người thuê)
- Xem danh sách phòng trọ với các bộ lọc (giá, vị trí, diện tích, tiện ích)
- Hệ thống đề xuất thông minh: nhập nhu cầu → hệ thống tính điểm phù hợp và gợi ý các phòng trọ tốt nhất
- Xem chi tiết phòng trọ với hình ảnh, thông tin liên hệ
- Nhắn tin trực tiếp với chủ trọ (real-time)
- Lưu tin yêu thích
- Đánh giá chủ trọ sau khi thuê
- Quản lý hồ sơ cá nhân

# Dành cho chủ trọ
- Đăng tin cho thuê với đầy đủ thông tin: giá, diện tích, địa chỉ, tiện ích, hình ảnh
- Quản lý tin đã đăng: sửa, xóa, ẩn/hiện
- Xem và trả lời tin nhắn từ sinh viên
- Quản lý thông tin cá nhân

# Hệ thống đề xuất
- Dựa trên các tiêu chí sinh viên nhập:
- Giá thuê tối đa
- Vị trí mong muốn (quận/huyện)
- Diện tích tối thiểu
- Danh sách tiện ích cần có (máy lạnh, nóng lạnh, wifi, chỗ để xe, ...)
- Loại hình (phòng trọ, căn hộ mini, ở ghép)
- Mỗi phòng trọ sẽ được tính điểm theo độ phù hợp, sau đó sắp xếp giảm dần.

2. Framework

# Frontend
- ReactJS
- TailwindCSS

# Backend
- Python (Django + GeoDjango/FastAPI)

# Realtime chat
- Socket.IO

# Authentication
- JWT

# Database
- PostgreSQL
- PostGIS

