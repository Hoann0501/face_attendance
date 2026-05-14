# Face Recognition Attendance System with Anti-Spoofing

Hệ thống điểm danh bằng nhận diện khuôn mặt kết hợp kiểm tra chống giả mạo sinh trắc học (liveness detection). Dự án bao gồm toàn bộ pipeline từ thu thập dữ liệu, huấn luyện model, đến hệ thống deploy hoàn chỉnh với web quản lý và camera app.

---

## Tổng quan hệ thống

| Thành phần | Mô tả |
|-----------|-------|
| Anti-spoofing | MobileNetV3-small — phân biệt mặt thật / ảnh giả, accuracy ~94.1% |
| Face verification | InsightFace ArcFace, cosine similarity, threshold 0.35 |
| Face attribute | MobileNetV3-small multi-task — gender, age_group, age estimation |
| Attendance | Check-in / Check-out với anti-spoof + face verify, lưu CSV local |
| Face captures | Tự lưu ảnh crop khuôn mặt khi check-in/check-out thành công |
| Web management | SPA (HTML/CSS/JS) — quản lý người, điểm danh, báo cáo, phân tích |
| Camera app | Python OpenCV — nhận diện realtime, chống giả mạo, điểm danh tự động |

---

## Cấu trúc thư mục gốc

```
data_face/
│
├── 02_train_face_crop_model.ipynb       # Train anti-spoofing model
├── 03_face_verification_poc.ipynb       # Face verification POC
├── 04_train_face_attribute_model.ipynb  # Train face attribute model
│
├── models/                              # Model weights gốc
│   ├── vfa_mobilenetv3_small_best.pth
│   ├── vfa_deploy_config.json
│   ├── face_attribute_mobilenetv3_best.pth
│   └── face_attribute_config.json
│
├── face_verification_poc/               # Dữ liệu POC
│   ├── people.csv
│   ├── person_templates.pkl
│   ├── face_verification_config.json
│   └── enroll/                          # Ảnh đăng ký gốc
│
├── attendance_logs/                     # Log điểm danh cũ (đã migrate)
│
├── Deploy/                              # Hệ thống deploy hoàn chỉnh
│   ├── README.md
│   ├── requirements.txt
│   ├── backend/                         # FastAPI backend
│   ├── frontend/static/                 # HTML/CSS/JS SPA
│   ├── camera_app/                      # OpenCV attendance camera
│   ├── core/                            # Shared ML modules
│   ├── data/                            # Runtime data (CSV/JSON/pickle)
│   ├── models/                          # Model weights (copied)
│   └── scripts/                         # Bat scripts & init tools
│
├── webcam_antispoof_demo.py             # POC: anti-spoofing
├── webcam_attendance_poc.py             # POC: full attendance
├── app_poc_ui.py / app_poc_ui_updated.py# POC: Streamlit UI cũ
└── register_new_person.py              # POC: face registration
```

> **Dataset thô** (`Image/`, `UTK_data/`, `processed_vfa/`) không được commit — xem `.gitignore`.

---

## Models đã train

### 1. Anti-Spoofing — `vfa_mobilenetv3_small_best.pth`

- Architecture: MobileNetV3-small, binary classification (fake / real)
- Dataset: ảnh live / not_live thực tế
- Test accuracy: **~94.1%**
- Deploy: temporal voting (window=7, min_votes=5, threshold face=0.75 / full=0.55)
- Notebook: `02_train_face_crop_model.ipynb`

### 2. Face Verification

- Model: InsightFace `buffalo_l` (ArcFace, 512-dim embedding)
- Method: Cosine similarity, threshold = **0.35**
- Template: mean-normalized embedding per person, lưu trong `person_templates.pkl`
- POC: 45 pairs → accuracy **100%** trên sample nhỏ
- Notebook: `03_face_verification_poc.ipynb`

### 3. Face Attribute — `face_attribute_mobilenetv3_best.pth`

- Architecture: MobileNetV3-small multi-task (gender + age_group + age regression)
- Dataset: UTKFace
- Results: gender ~92.2% · age_group ~79.7% · Age MAE ~6.5 năm
- Age normalization: `label / 100.0` khi train → `output × 100.0` khi predict
- Notebook: `04_train_face_attribute_model.ipynb`

---

## Deploy — Chạy hệ thống

Thư mục `Deploy/` là hệ thống hoàn chỉnh, chạy độc lập.

```bash
# Bước 1: Cài thư viện
pip install -r Deploy/requirements.txt

# Bước 2: Khởi tạo (chạy 1 lần)
cd Deploy
python scripts/init_deploy.py

# Bước 3: Chạy backend + web
scripts\run_backend.bat        # http://127.0.0.1:8000

# Bước 4: Camera điểm danh
scripts\run_camera_checkin.bat
scripts\run_camera_checkout.bat
```

### Tính năng chính của Deploy

| Trang / Module | Mô tả |
|---------------|-------|
| Dashboard | Metrics hôm nay, recent events, auto-refresh 5s |
| Quan ly nguoi | Danh sách + tìm kiếm + phân trang + detail page đầy đủ |
| &nbsp;&nbsp;└ Thêm người | Form + upload ảnh khuôn mặt trong cùng 1 bước |
| &nbsp;&nbsp;└ Detail page | Ảnh đăng ký, lịch sử điểm danh, actions |
| Tim kiem / Xac minh | Face search top-K + verification 1-to-1 |
| Phan tich anh | Detect + bbox + gender + age + age_group |
| Bao cao diem danh | Filter, export CSV/Excel, xóa record |
| &nbsp;&nbsp;└ Face Captures | Xem ảnh khuôn mặt đã chụp khi check-in/out |
| Camera app | Startup menu chọn mode + camera, overlay sạch |
| Pipeline Report | Báo cáo kỹ thuật đầy đủ cho trình bày |

Xem hướng dẫn chi tiết tại [`Deploy/README.md`](Deploy/README.md).

---

## POC Scripts (tham khảo)

| File | Mô tả |
|------|-------|
| `webcam_antispoof_demo.py` | Demo anti-spoofing cơ bản |
| `webcam_antispoof_demo_v3_fast_attendance.py` | Demo temporal voting |
| `webcam_attendance_poc.py` | Demo điểm danh chưa tách module |
| `app_poc_ui.py` / `app_poc_ui_updated.py` | Streamlit UI ban đầu (deprecated) |
| `register_new_person.py` | Đăng ký khuôn mặt qua webcam |

---

## Yêu cầu hệ thống

- Python 3.10+
- PyTorch (CPU hoặc CUDA)
- InsightFace, OpenCV, FastAPI + Uvicorn
- Xem đầy đủ: `Deploy/requirements.txt`

---

## Ghi chú quan trọng

- Dataset thô **không** commit — dùng `.gitignore`
- Model weights `.pth` nặng → cân nhắc Git LFS hoặc lưu riêng
- Storage: **local CSV / JSON / pickle** — không cần database server
- Anti-spoofing và face verification là **POC**, chưa validate production quy mô lớn
- Frontend là **HTML/CSS/JS SPA thuần** (không dùng Streamlit/React/Vue)
