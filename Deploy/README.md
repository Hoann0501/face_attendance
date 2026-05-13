# Face Recognition Attendance – Deploy

Hệ thống điểm danh bằng nhận diện khuôn mặt, tích hợp:
- **Anti-spoofing** (MobileNetV3-small, temporal voting)
- **Face verification** (InsightFace buffalo_l / ArcFace)
- **Face attribute analysis** (gender, age_group, age)
- **FastAPI** backend + **Streamlit** web quản lý
- **OpenCV** camera app riêng biệt

---

## Cấu trúc thư mục

```
Deploy/
├── backend/              FastAPI backend
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── schemas.py
│   ├── services/
│   │   ├── person_service.py
│   │   ├── attendance_service.py
│   │   └── face_service.py
│   └── api/
│       ├── health.py
│       ├── people.py
│       ├── attendance.py
│       └── face.py
├── frontend/             Streamlit web quản lý
│   ├── app.py
│   ├── pages/
│   │   ├── dashboard.py
│   │   ├── people.py
│   │   ├── register.py
│   │   ├── face_search.py
│   │   ├── face_analysis.py
│   │   └── attendance_report.py
│   └── assets/styles.css
├── camera_app/           OpenCV camera attendance
│   ├── attendance_camera.py
│   └── camera_config.py
├── core/                 Shared ML modules
│   ├── antispoof.py
│   ├── face_verifier.py
│   ├── face_attribute.py
│   ├── face_detector.py
│   └── utils.py
├── data/
│   ├── database/attendance.db   SQLite database
│   ├── people/people.csv        Dữ liệu người (seed)
│   ├── attendance_logs/         Log CSV cũ (dùng khi import)
│   ├── attendance_reports/      Báo cáo xuất
│   ├── enroll_images/           Ảnh enroll lưu trữ
│   └── runtime/                 Runtime temp files
├── models/
│   ├── anti_spoof/              Model chống giả mạo
│   ├── verification/            Templates + config InsightFace
│   └── attribute/               Model phân tích thuộc tính
├── scripts/
│   ├── init_deploy.py
│   ├── import_existing_data.py
│   ├── run_backend.bat
│   ├── run_frontend.bat
│   ├── run_camera_checkin.bat
│   └── run_camera_checkout.bat
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup lần đầu

### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

> Nếu có GPU: cài torch với CUDA tương ứng từ [pytorch.org](https://pytorch.org).

### 2. Khởi tạo database và import dữ liệu cũ

```bash
cd C:\Users\Hoannd\Downloads\data_face\Deploy
python scripts/init_deploy.py
```

Script này sẽ:
- Tạo `data/database/attendance.db`
- Import `data/people/people.csv` vào bảng `people`
- Import `data/attendance_logs/*.csv` vào bảng `attendance`

---

## Chạy hệ thống

### Backend API

```bash
scripts\run_backend.bat
```
Hoặc:
```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
API docs: http://127.0.0.1:8000/docs

### Frontend web quản lý

```bash
scripts\run_frontend.bat
```
Hoặc:
```bash
python -m streamlit run frontend/app.py
```
Web: http://localhost:8501

### Camera check-in

```bash
scripts\run_camera_checkin.bat
```

### Camera check-out

```bash
scripts\run_camera_checkout.bat
```

**Phím tắt trong cửa sổ camera:**
- `I` – chuyển sang CHECK-IN mode
- `O` – chuyển sang CHECK-OUT mode
- `Q` – thoát

---

## Luồng điểm danh (Check-in)

```
1. Mở webcam
2. Detect mặt (Haar cascade)
3. Anti-spoofing temporal voting (7 frames, cần 5 real votes)
   ├─ FAKE_OR_SUSPECT → hiển thị cảnh báo, không ghi
   └─ REAL_ATTENDANCE_OK → tiếp tục
4. InsightFace extract embedding
5. So sánh với templates (cosine similarity)
   ├─ similarity < 0.35 → REAL BUT UNKNOWN
   └─ verified → tiếp tục
6. Kiểm tra người có active không
   └─ inactive → INACTIVE USER
7. Gọi POST /attendance/check-in
   ├─ Chưa check-in → ghi CHECK_IN SUCCESS
   └─ Đã check-in → ALREADY CHECKED IN TODAY
```

**Luồng check-out** tương tự, bước 7 gọi POST /attendance/check-out.

---

## API endpoints tóm tắt

| Method | Path | Mô tả |
|--------|------|-------|
| GET | /health | Health check |
| GET | /people | Danh sách người |
| POST | /people | Thêm người |
| PUT | /people/{id} | Cập nhật người |
| PATCH | /people/{id}/status | Active/Inactive |
| DELETE | /people/{id} | Xóa người |
| POST | /face/register | Đăng ký khuôn mặt |
| POST | /face/search | Tìm kiếm top-k |
| POST | /face/verify | Xác minh 1-to-1 |
| POST | /face/analyze | Phân tích ảnh |
| POST | /attendance/check-in | Check in |
| POST | /attendance/check-out | Check out |
| GET | /attendance?date= | Lấy bản ghi theo ngày |
| GET | /attendance/report?date= | Báo cáo PRESENT/ABSENT |
| GET | /attendance/today | Hôm nay |
| GET | /attendance/events/recent | Feed gần đây |

---

## Models đang dùng

| Model | Mô tả | File |
|-------|-------|------|
| MobileNetV3-small | Anti-spoofing liveness | models/anti_spoof/vfa_mobilenetv3_small_best.pth |
| InsightFace buffalo_l | ArcFace face embedding | (download tự động) |
| MobileNetV3-small (multi-task) | Gender + age_group + age | models/attribute/face_attribute_mobilenetv3_best.pth |

---

## Cấu hình

Sửa `.env.example` → copy thành `.env` và đặt các biến môi trường.

Quan trọng nhất:
- `CAMERA_INDEX` – chỉ số webcam (0, 1, 2)
- `REAL_THRESHOLD_FACE` / `REAL_THRESHOLD_FULL` – ngưỡng anti-spoof
- `VERIFY_THRESHOLD` – ngưỡng nhận diện (0.35 = default)

---

## Lưu ý

- Chạy `init_deploy.py` **một lần duy nhất** để khởi tạo DB.
- Backend và camera app phải chạy song song để camera ghi được điểm danh.
- Web frontend refresh mỗi 5 giây (dùng `streamlit-autorefresh`).
- Tất cả dữ liệu lưu tại `Deploy/data/database/attendance.db`.
- Không cần đụng vào project gốc sau khi deploy.
