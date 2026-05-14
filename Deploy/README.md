# Face Attendance — Deploy

Hệ thống điểm danh bằng nhận diện khuôn mặt có chống giả mạo sinh trắc học.  
Thư mục này chạy **hoàn toàn độc lập** khỏi project gốc.

---

## Cấu trúc thư mục

```
Deploy/
├── backend/                    FastAPI backend
│   ├── main.py                 Entry point (serve API + frontend)
│   ├── config.py               Tất cả đường dẫn và tham số
│   ├── database.py             Storage init (no SQL/SQLite)
│   ├── schemas.py              Pydantic schemas
│   ├── services/
│   │   ├── person_service.py   CRUD people.csv
│   │   ├── attendance_service.py  Check-in/out, report, history
│   │   └── face_service.py     Register, search, verify, analyze
│   └── api/
│       ├── health.py
│       ├── people.py           + /attendance + /enroll-images endpoints
│       ├── attendance.py       + /captures endpoint
│       └── face.py
│
├── frontend/static/            HTML/CSS/JS Single Page App
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── api.js              Fetch wrapper with timeout
│       ├── app.js              SPA router + sub-routing (#people/id)
│       └── pages/
│           ├── dashboard.js    Metrics + recent events (auto-refresh 5s)
│           ├── people.js       List + detail page + inline face upload
│           ├── face_search.js  Search 1-to-N + verify 1-to-1
│           ├── face_analysis.js  Detect + canvas annotation
│           ├── attendance.js   Report + face captures tab
│           └── pipeline.js     Technical overview report
│
├── camera_app/
│   ├── attendance_camera.py    OpenCV camera (startup menu, sharp-frame buffer)
│   └── camera_config.py
│
├── core/                       Shared ML modules (no UI dependencies)
│   ├── antispoof.py            AntiSpoofService (temporal voting)
│   ├── face_verifier.py        FaceVerifier (InsightFace ArcFace)
│   ├── face_attribute.py       FaceAttributeAnalyzer (gender, age)
│   ├── face_detector.py        FaceDetector helper
│   └── utils.py                Image conversion, drawing helpers
│
├── data/                       Runtime data (local file storage)
│   ├── people/
│   │   └── people.csv
│   ├── attendance/
│   │   └── attendance_YYYY-MM-DD.csv
│   ├── enroll_images/
│   │   └── {person_id}/        Face images saved on registration
│   ├── face_captures/
│   │   └── YYYY-MM-DD/
│   │       ├── checkin/        Face photos auto-saved on check-in
│   │       └── checkout/       Face photos auto-saved on check-out
│   ├── reports/                Export CSV/Excel
│   └── runtime/
│       └── recent_events.json  Last 50 events (frontend polling)
│
├── models/
│   ├── anti_spoof/
│   │   ├── vfa_mobilenetv3_small_best.pth
│   │   └── vfa_deploy_config.json
│   ├── verification/
│   │   ├── person_templates.pkl
│   │   └── face_verification_config.json
│   └── attribute/
│       ├── face_attribute_mobilenetv3_best.pth
│       └── face_attribute_config.json
│
├── scripts/
│   ├── init_deploy.py          Khoi tao du lieu, copy enroll images
│   ├── import_existing_data.py Re-run migration
│   ├── run_backend.bat         Chay backend + frontend
│   ├── run_camera_checkin.bat
│   └── run_camera_checkout.bat
│
├── requirements.txt
├── .env.example
└── README.md
```

> **Storage**: Local CSV / JSON / pickle — khong dung SQL/SQLite.  
> **Frontend**: HTML/CSS/JS SPA — khong dung Streamlit/React/Vue.

---

## Setup lan dau (chay 1 lan)

### 1. Cai thu vien

```bash
pip install -r requirements.txt
```

> GPU: cai PyTorch voi CUDA tuong ung tu [pytorch.org](https://pytorch.org) truoc.

### 2. Khoi tao du lieu

```bash
cd C:\Users\Hoannd\Downloads\data_face\Deploy
python scripts/init_deploy.py
```

Script nay se:
- Tao cac thu muc `data/`
- Chuan hoa `people.csv` (them cot `created_at`, `updated_at` neu chua co)
- Copy anh dang ky (`enroll_images/`) tu project goc
- Migrate log diem danh cu vao `data/attendance/`

---

## Chay he thong

### Backend + Frontend (bat buoc)

```bat
scripts\run_backend.bat
```

- API: `http://127.0.0.1:8000`
- Web quan ly: `http://127.0.0.1:8000` (may chu)
- **May khac cung Wi-Fi / LAN:** mo `http://<IPv4-may-chay-backend>:8000` (xem `ipconfig` tren Windows). Script `run_backend.bat` da lang nghe `0.0.0.0`. Neu khong vao duoc: mo **Firewall** cho `python.exe` hoac cong `8000`.
- API docs (Swagger): `http://127.0.0.1:8000/docs`

Khi backend khoi dong, console se in them dong `LAN: http://...` neu phat hien duoc IPv4 noi bo.

Hoac chay tay:

```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Chi cho may chu thi co the dung `--host 127.0.0.1`.

### Camera diem danh

```bat
scripts\run_camera_checkin.bat    # mode Check-In
scripts\run_camera_checkout.bat   # mode Check-Out
```

**Phim tat trong cua so camera:**

| Phim | Chuc nang |
|------|-----------|
| `1`  | Chuyen sang Check-In mode |
| `2`  | Chuyen sang Check-Out mode |
| `Q`  | Thoat |

Neu khong truyen `--camera`, app tu scan va hoi chon camera khi khoi dong.

```bat
scripts\run_camera_checkin.bat --camera 2   # chi dinh camera index
```

---

## Tinh nang Web Management

| Trang | Chuc nang chinh |
|-------|----------------|
| Dashboard | Metrics hom nay, recent events feed, auto-refresh 5s |
| Quan ly nguoi | Danh sach + tim kiem + phan trang, click mo detail page |
| &nbsp;&nbsp;Them nguoi | Form thong tin + upload anh khuon mat cung 1 buoc |
| &nbsp;&nbsp;Detail page | Thong tin, anh dang ky, lich su diem danh, actions |
| &nbsp;&nbsp;Cap nhat khuon mat | Upload anh truc tiep trong tab "Anh dang ky" |
| Tim kiem / Xac minh | Face search top-K va verification 1-to-1 |
| Phan tich anh | Detect bbox, gender, age, age_group |
| Bao cao diem danh | Filter, export CSV/Excel, xoa record |
| Face Captures | Xem anh khuon mat da chup khi check-in/out |
| Pipeline Report | Bao cao ky thuat day du |

---

## Luong diem danh

### Check-In

```
1. Camera detect mat (Haar cascade)
2. Tich luy frame vao Sharp-Frame Buffer (20 frames)
3. Anti-spoofing temporal voting
   FAKE_OR_SUSPECT -> hien canh bao, khong ghi, khong luu anh
   REAL_ATTENDANCE_OK -> tiep tuc
4. InsightFace ArcFace extract embedding (512-dim)
5. Cosine similarity < 0.35 -> REAL BUT UNKNOWN, khong ghi
6. Verified -> kiem tra person status
   inactive -> INACTIVE USER, khong ghi
   active -> ghi check_in_time vao CSV
7. Luu anh khuon mat sac net nhat vao face_captures/date/checkin/
8. Hien thi CHECK IN SUCCESS
```

### Check-Out (tuong tu)

```
1-6. Nhu Check-In
7.   Kiem tra da check-in chua
     Chua -> BAO LOI
     Da check-out -> ALREADY CHECKED OUT
     Da check-in, chua check-out -> ghi check_out_time + luu anh
8.   Hien thi CHECK OUT SUCCESS
```

---

## API Endpoints

| Method | Path | Mo ta |
|--------|------|-------|
| GET  | `/health` | Health check |
| GET  | `/people` | Danh sach nguoi (kem last check-in/out) |
| POST | `/people` | Them nguoi moi |
| PUT  | `/people/{id}` | Cap nhat thong tin |
| PATCH| `/people/{id}/status` | Doi active/inactive |
| DELETE| `/people/{id}` | Xoa nguoi + template |
| GET  | `/people/{id}/attendance?days=7` | Lich su diem danh |
| GET  | `/people/{id}/enroll-images` | Danh sach anh dang ky |
| GET  | `/people/{id}/enroll-images/{filename}` | Serve anh dang ky |
| POST | `/face/register` | Dang ky khuon mat (luu anh + tao template) |
| POST | `/face/search?top_k=5` | Tim kiem top-K |
| POST | `/face/verify` | Xac minh 1-to-1 |
| POST | `/face/analyze` | Phan tich anh (bbox, gender, age) |
| POST | `/attendance/check-in` | Check in |
| POST | `/attendance/check-out` | Check out |
| GET  | `/attendance?date=` | Ban ghi theo ngay |
| GET  | `/attendance/report?date=` | Bao cao PRESENT/ABSENT/CHECKED_OUT |
| GET  | `/attendance/today` | Hom nay |
| GET  | `/attendance/events/recent?limit=20` | Feed gan day |
| GET  | `/attendance/captures?date=` | Danh sach anh capture |
| GET  | `/attendance/captures/image?date=&mode=&filename=` | Serve anh capture |
| DELETE | `/attendance?person_id=&date=` | Xoa record + cascade anh |
| GET  | `/attendance/export?date=&format=csv\|xlsx` | Export bao cao |

---

## Models

| Model | Mo ta | File |
|-------|-------|------|
| MobileNetV3-small | Anti-spoofing (fake/real) | `models/anti_spoof/vfa_mobilenetv3_small_best.pth` |
| InsightFace buffalo_l | ArcFace face embedding | Tai tu insightface (tu dong) |
| MobileNetV3-small multi-task | Gender + age_group + age | `models/attribute/face_attribute_mobilenetv3_best.pth` |

---

## Cau hinh (.env)

Copy `.env.example` thanh `.env` roi chinh:

```env
CAMERA_INDEX=0              # Index webcam (0, 1, 2...)
CAMERA_COOLDOWN_SECONDS=4   # Giay giua cac lan ghi

REAL_THRESHOLD_FACE=0.75    # Anti-spoof: face crop threshold
REAL_THRESHOLD_FULL=0.55    # Anti-spoof: full frame threshold
WINDOW_SIZE=7               # Temporal voting window
MIN_REAL_VOTES=5            # Min real votes to pass

VERIFY_THRESHOLD=0.35       # Face verification threshold
# Camera goi API: tren cung may de mac dinh 127.0.0.1. Neu camera chay may KHAC trong LAN, dat IP may chu:
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
```

---

## Luu y quan trong

- Chay `init_deploy.py` **mot lan duy nhat** khi setup moi.
- Backend phai chay truoc khi mo web hoac chay camera.
- Web tu dong refresh sau 5 giay (polling recent events).
- Tat ca du lieu luu trong `Deploy/data/` — khong can database server.
- Xoa attendance record se cascade xoa luon anh capture tuong ung.
- De them nguoi moi co khuon mat ngay: dung modal "+ Them nguoi moi" tren web.
