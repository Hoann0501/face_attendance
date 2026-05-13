# Face Recognition Attendance System with Anti-Spoofing

Hệ thống điểm danh bằng nhận diện khuôn mặt kết hợp kiểm tra chống giả mạo sinh trắc học (liveness detection). Dự án bao gồm toàn bộ pipeline từ thu thập dữ liệu, huấn luyện model, đến tích hợp hệ thống production-ready.

---

## Tổng quan

| Thành phần | Mô tả |
|-----------|-------|
| Anti-spoofing | MobileNetV3-small, phân biệt mặt thật / ảnh giả, accuracy ~94% |
| Face verification | InsightFace ArcFace, cosine similarity, threshold 0.35 |
| Face attribute | MobileNetV3-small multi-task, gender + age_group + age estimation |
| Attendance system | Check-in / Check-out, local CSV storage, realtime web report |

---

## Cấu trúc thư mục

```
data_face/
│
├── 02_train_face_crop_model.ipynb       # Train anti-spoofing model
├── 03_face_verification_poc.ipynb       # Face verification POC
├── 04_train_face_attribute_model.ipynb  # Train face attribute model
│
├── models/                              # Trained model weights
│   ├── vfa_mobilenetv3_small_best.pth   # Anti-spoofing model
│   ├── vfa_deploy_config.json
│   ├── face_attribute_mobilenetv3_best.pth  # Attribute model
│   └── face_attribute_config.json
│
├── face_verification_poc/               # Verification data & templates
│   ├── people.csv
│   ├── person_templates.pkl
│   ├── face_verification_config.json
│   ├── enroll/                          # Enrolled face images
│   └── query/
│
├── attendance_logs/                     # Old attendance CSV logs
│
├── Deploy/                              # Production-ready deployment
│   ├── README.md                        # Deploy-specific guide
│   ├── requirements.txt
│   ├── backend/                         # FastAPI backend
│   ├── frontend/                        # HTML/CSS/JS web management
│   ├── camera_app/                      # OpenCV attendance camera
│   ├── core/                            # Shared ML modules
│   ├── data/                            # Runtime data storage
│   ├── models/                          # Copied model weights
│   └── scripts/                         # Bat scripts & init tools
│
├── webcam_antispoof_demo.py             # POC: anti-spoofing webcam
├── webcam_attendance_poc.py             # POC: full attendance webcam
├── app_poc_ui.py                        # POC: Streamlit UI
└── register_new_person.py              # POC: face registration
```

> **Dataset thô** (`Image/`, `UTK_data/`, `processed_vfa/`) không được đẩy lên Git do dung lượng lớn. Xem `.gitignore`.

---

## Models đã train

### 1. Anti-Spoofing — `vfa_mobilenetv3_small_best.pth`

- Architecture: MobileNetV3-small, binary classification (fake / real)
- Dataset: ảnh live/not_live thu thập thực tế
- Test accuracy: **~94.1%**
- Notebook: `02_train_face_crop_model.ipynb`
- Deploy config: `models/vfa_deploy_config.json`

### 2. Face Verification

- Backend: InsightFace `buffalo_l` (ArcFace, 512-dim embedding)
- Method: Cosine similarity, threshold = **0.35**
- POC: 45 pairs (15 positive, 30 negative), accuracy **100%** trên sample nhỏ
- Templates: `face_verification_poc/person_templates.pkl`
- Notebook: `03_face_verification_poc.ipynb`

### 3. Face Attribute — `face_attribute_mobilenetv3_best.pth`

- Architecture: MobileNetV3-small multi-task
- Heads: gender (binary) + age_group (5 class) + age (regression)
- Dataset: UTKFace
- Gender accuracy: **~92.2%** · Age-group accuracy: **~79.7%** · Age MAE: **~6.5 năm**
- Age normalization: `label / 100.0` khi train, `output × 100.0` khi predict
- Notebook: `04_train_face_attribute_model.ipynb`

---

## Deploy

Thư mục `Deploy/` chứa hệ thống hoàn chỉnh, chạy độc lập, không phụ thuộc vào project gốc.

```
# Bước 1: Cài thư viện
pip install -r Deploy/requirements.txt

# Bước 2: Khởi tạo dữ liệu (chạy 1 lần)
cd Deploy
python scripts/init_deploy.py

# Bước 3: Chạy hệ thống
scripts\run_backend.bat        # Backend API + Web → http://127.0.0.1:8000
scripts\run_camera_checkin.bat # Camera check-in
scripts\run_camera_checkout.bat# Camera check-out
```

Xem hướng dẫn chi tiết tại [`Deploy/README.md`](Deploy/README.md).

---

## POC Scripts

Các file POC dùng để thử nghiệm trước khi tích hợp vào Deploy:

| File | Mô tả |
|------|-------|
| `webcam_antispoof_demo.py` | Demo anti-spoofing đơn giản với webcam |
| `webcam_antispoof_demo_v3_fast_attendance.py` | Demo liveness fast temporal voting |
| `webcam_attendance_poc.py` | Demo điểm danh đầy đủ (chưa tách module) |
| `app_poc_ui.py` / `app_poc_ui_updated.py` | Streamlit UI quản lý ban đầu |
| `register_new_person.py` | Script đăng ký khuôn mặt qua webcam |

---

## Yêu cầu hệ thống

- Python 3.10+
- PyTorch (CPU hoặc CUDA)
- InsightFace
- OpenCV
- FastAPI + Uvicorn
- Xem đầy đủ: `Deploy/requirements.txt`

---

## Ghi chú

- Dataset thô **không** được commit vào repo (xem `.gitignore`).
- Model weights (`.pth`) có thể được bỏ khỏi repo nếu dung lượng quá lớn — dùng Git LFS hoặc lưu riêng.
- Hệ thống Deploy dùng **local file storage** (CSV / JSON / pickle) để dễ demo và kiểm tra — không cần database server.
- Anti-spoofing và face verification là POC, chưa được validate trên dataset production quy mô lớn.
