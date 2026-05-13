import cv2
import json
import pickle
import csv
from pathlib import Path
from collections import deque
from datetime import datetime, date

import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image, ImageFile

from insightface.app import FaceAnalysis


ImageFile.LOAD_TRUNCATED_IMAGES = True


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(r"C:\Users\Hoannd\Downloads\data_face")

# Anti-spoofing model
ANTI_MODEL_PATH = BASE_DIR / "models" / "vfa_mobilenetv3_small_best.pth"
ANTI_CONFIG_PATH = BASE_DIR / "models" / "vfa_deploy_config.json"

# Face verification
VERIFY_DIR = BASE_DIR / "face_verification_poc"
TEMPLATES_PATH = VERIFY_DIR / "person_templates.pkl"
VERIFY_CONFIG_PATH = VERIFY_DIR / "face_verification_config.json"
PEOPLE_CSV_PATH = VERIFY_DIR / "people.csv"

# Attendance logs
ATTENDANCE_DIR = BASE_DIR / "attendance_logs"
ATTENDANCE_DIR.mkdir(parents=True, exist_ok=True)

# Camera
CAMERA_INDEX = 2
IMG_SIZE = 224

# Anti-spoofing fast attendance config
# Nếu người thật bị FAKE nhiều: giảm FACE xuống 0.70, FULL xuống 0.45
# Nếu ảnh màn hình vẫn qua: tăng FACE lên 0.80, FULL lên 0.65, MIN_REAL_VOTES lên 6
REAL_THRESHOLD_FACE = 0.75
REAL_THRESHOLD_FULL = 0.55

WINDOW_SIZE = 7
MIN_REAL_VOTES = 5

PREDICT_EVERY_N_FRAMES = 1

# Face verification config
DEFAULT_VERIFY_THRESHOLD = 0.35

# Chỉ điểm danh 1 lần/ngày
ONLY_ONCE_PER_DAY = True


# ============================================================
# FILE CHECK
# ============================================================

required_files = [
    ANTI_MODEL_PATH,
    ANTI_CONFIG_PATH,
    TEMPLATES_PATH,
    VERIFY_CONFIG_PATH,
    PEOPLE_CSV_PATH,
]

print("=" * 70)
print("CHECK REQUIRED FILES")
print("=" * 70)

missing = []

for p in required_files:
    exists = p.exists()
    print(f"{str(p):90s} exists={exists}")
    if not exists:
        missing.append(str(p))

if missing:
    raise FileNotFoundError(
        "Thiếu file cần thiết:\n" + "\n".join(missing)
    )


# ============================================================
# PEOPLE DATABASE
# ============================================================

def load_people_database(csv_path):
    """
    Load danh sách người đăng ký từ people.csv.

    CSV columns:
    person_id,full_name,student_code,class_name,status
    """
    people = {}

    with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            person_id = row.get("person_id", "").strip()

            if not person_id:
                continue

            people[person_id] = {
                "person_id": person_id,
                "full_name": row.get("full_name", "").strip(),
                "student_code": row.get("student_code", "").strip(),
                "class_name": row.get("class_name", "").strip(),
                "status": row.get("status", "active").strip().lower(),
            }

    return people


def get_person_info(person_id, people_db):
    if person_id in people_db:
        return people_db[person_id]

    return {
        "person_id": person_id,
        "full_name": person_id,
        "student_code": "",
        "class_name": "",
        "status": "unknown",
    }


def format_person_display(person_id, people_db):
    info = get_person_info(person_id, people_db)

    full_name = info.get("full_name", person_id) or person_id
    student_code = info.get("student_code", "")
    class_name = info.get("class_name", "")

    parts = [full_name]

    if student_code:
        parts.append(student_code)

    if class_name:
        parts.append(class_name)

    return " | ".join(parts)


# ============================================================
# ATTENDANCE HELPERS
# ============================================================

def get_today_attendance_path():
    today_str = date.today().strftime("%Y-%m-%d")
    return ATTENDANCE_DIR / f"attendance_{today_str}.csv"


def ensure_attendance_file(csv_path):
    if csv_path.exists():
        return

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp",
            "person_id",
            "full_name",
            "student_code",
            "class_name",
            "attendance_status",
            "similarity",
            "liveness_status",
            "face_real_score",
            "full_real_score",
        ])


def load_today_attended(csv_path):
    """
    Load danh sách người đã điểm danh hôm nay.
    Trả về dict:
    {
        person_id: timestamp_datetime
    }
    """
    attended = {}

    if not csv_path.exists():
        return attended

    with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            person_id = row.get("person_id", "").strip()
            ts_str = row.get("timestamp", "").strip()

            if not person_id or not ts_str:
                continue

            try:
                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                attended[person_id] = ts
            except Exception:
                pass

    return attended


def can_log_attendance(person_id, attended_cache):
    """
    Chỉ cho điểm danh 1 lần/ngày.
    Nếu person_id đã có trong file attendance hôm nay thì không ghi nữa.
    """
    if person_id not in attended_cache:
        return True, "not_logged_today"

    return False, "already_attended_today"


def log_attendance(
    person_id,
    person_info,
    similarity,
    liveness_status,
    face_real_score,
    full_real_score,
    attended_cache,
):
    csv_path = get_today_attendance_path()
    ensure_attendance_file(csv_path)

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp,
            person_id,
            person_info.get("full_name", ""),
            person_info.get("student_code", ""),
            person_info.get("class_name", ""),
            "ATTENDED",
            round(float(similarity), 4),
            liveness_status,
            round(float(face_real_score), 4),
            round(float(full_real_score), 4),
        ])

    attended_cache[person_id] = now

    return csv_path


# ============================================================
# DEVICE
# ============================================================

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print()
print("=" * 70)
print("DEVICE")
print("=" * 70)
print("Device:", device)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))


# ============================================================
# LOAD PEOPLE
# ============================================================

people_db = load_people_database(PEOPLE_CSV_PATH)

print()
print("=" * 70)
print("PEOPLE DATABASE")
print("=" * 70)
print("People CSV:", PEOPLE_CSV_PATH)
print("People loaded:", len(people_db))
print("People IDs:", list(people_db.keys()))


# ============================================================
# INIT ATTENDANCE
# ============================================================

today_csv = get_today_attendance_path()
ensure_attendance_file(today_csv)
attended_cache = load_today_attended(today_csv)

print()
print("=" * 70)
print("ATTENDANCE")
print("=" * 70)
print("Attendance file:", today_csv)
print("Already attended today:", list(attended_cache.keys()))


# ============================================================
# LOAD VERIFICATION CONFIG
# ============================================================

with open(VERIFY_CONFIG_PATH, "r", encoding="utf-8") as f:
    verify_config = json.load(f)

VERIFY_THRESHOLD = float(
    verify_config.get("verify_threshold", DEFAULT_VERIFY_THRESHOLD)
)

print()
print("=" * 70)
print("FACE VERIFICATION CONFIG")
print("=" * 70)
print("VERIFY_THRESHOLD:", VERIFY_THRESHOLD)


# ============================================================
# LOAD PERSON TEMPLATES
# ============================================================

with open(TEMPLATES_PATH, "rb") as f:
    person_templates = pickle.load(f)

print("Templates loaded:", list(person_templates.keys()))


# ============================================================
# LOAD ANTI-SPOOF MODEL
# ============================================================

anti_checkpoint = torch.load(ANTI_MODEL_PATH, map_location=device)

classes = anti_checkpoint.get("classes", ["fake", "real"])
class_to_idx = anti_checkpoint.get("class_to_idx", {"fake": 0, "real": 1})

num_classes = len(classes)

anti_model = models.mobilenet_v3_small(weights=None)
in_features = anti_model.classifier[3].in_features
anti_model.classifier[3] = nn.Linear(in_features, num_classes)

anti_model.load_state_dict(anti_checkpoint["model_state_dict"])
anti_model = anti_model.to(device)
anti_model.eval()

fake_idx = class_to_idx["fake"]
real_idx = class_to_idx["real"]

print()
print("=" * 70)
print("ANTI-SPOOF MODEL")
print("=" * 70)
print("Model:", ANTI_MODEL_PATH)
print("Classes:", classes)
print("Class to idx:", class_to_idx)
print("REAL_THRESHOLD_FACE:", REAL_THRESHOLD_FACE)
print("REAL_THRESHOLD_FULL:", REAL_THRESHOLD_FULL)
print("WINDOW_SIZE:", WINDOW_SIZE)
print("MIN_REAL_VOTES:", MIN_REAL_VOTES)


# ============================================================
# TRANSFORM
# ============================================================

eval_tfms = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])


# ============================================================
# FACE DETECTOR
# ============================================================

haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(haar_path)

if face_cascade.empty():
    raise RuntimeError("Cannot load Haar Cascade face detector.")

print()
print("=" * 70)
print("FACE DETECTOR")
print("=" * 70)
print("Haar Cascade loaded:", haar_path)


# ============================================================
# INSIGHTFACE
# ============================================================

face_app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"],
)

face_app.prepare(ctx_id=0, det_size=(640, 640))

print()
print("=" * 70)
print("INSIGHTFACE")
print("=" * 70)
print("InsightFace buffalo_l loaded.")


# ============================================================
# AI HELPERS
# ============================================================

def expand_bbox(x, y, w, h, img_w, img_h, margin=0.35):
    mx = int(w * margin)
    my = int(h * margin)

    x1 = max(0, x - mx)
    y1 = max(0, y - my)
    x2 = min(img_w, x + w + mx)
    y2 = min(img_h, y + h + my)

    return x1, y1, x2, y2


def get_largest_haar_face(faces):
    if len(faces) == 0:
        return None

    faces = sorted(faces, key=lambda box: box[2] * box[3], reverse=True)
    return faces[0]


def predict_antispoof_rgb(img_rgb):
    pil_img = Image.fromarray(img_rgb).convert("RGB")
    x = eval_tfms(pil_img).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = anti_model(x)
        probs = torch.softmax(logits, dim=1)[0].detach().cpu().numpy()

    fake_score = float(probs[fake_idx])
    real_score = float(probs[real_idx])

    return real_score, fake_score


def get_largest_insightface(faces):
    if len(faces) == 0:
        return None

    def area(face):
        x1, y1, x2, y2 = face.bbox
        return max(0, x2 - x1) * max(0, y2 - y1)

    return max(faces, key=area)


def verify_identity_bgr(frame_bgr):
    """
    Trả về best match trong person_templates.
    Nếu similarity >= VERIFY_THRESHOLD thì is_verified=True.
    """
    faces = face_app.get(frame_bgr)
    face = get_largest_insightface(faces)

    if face is None:
        return {
            "ok": False,
            "reason": "no_face",
            "best_person": None,
            "best_similarity": None,
            "is_verified": False,
        }

    emb = face.embedding.astype(np.float32)
    emb = emb / np.linalg.norm(emb)

    best_person = None
    best_similarity = -1.0

    for person_id, template in person_templates.items():
        template = template.astype(np.float32)
        template = template / np.linalg.norm(template)

        sim = float(np.dot(emb, template))

        if sim > best_similarity:
            best_similarity = sim
            best_person = person_id

    is_verified = best_similarity >= VERIFY_THRESHOLD

    return {
        "ok": True,
        "reason": "ok",
        "best_person": best_person,
        "best_similarity": best_similarity,
        "is_verified": is_verified,
    }


# ============================================================
# UI HELPERS
# ============================================================

def draw_text_with_bg(
    img,
    text,
    org,
    font_scale=0.7,
    color=(255, 255, 255),
    bg_color=(0, 0, 0),
    thickness=2,
):
    font = cv2.FONT_HERSHEY_SIMPLEX

    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    x, y = org

    cv2.rectangle(
        img,
        (x - 4, y - th - 8),
        (x + tw + 4, y + baseline + 4),
        bg_color,
        -1,
    )

    cv2.putText(
        img,
        text,
        (x, y),
        font,
        font_scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


def status_color(status):
    if status == "REAL_ATTENDANCE_OK":
        return (0, 255, 0)

    if status == "FAKE_OR_SUSPECT":
        return (0, 0, 255)

    if status == "CHECKING":
        return (0, 255, 255)

    return (255, 255, 255)


# ============================================================
# TEMPORAL STATE
# ============================================================

score_buffer = deque(maxlen=WINDOW_SIZE)

last_liveness_status = "WAITING"

last_face_real = 0.0
last_face_fake = 0.0
last_full_real = 0.0
last_full_fake = 0.0

last_verify_result = {
    "ok": False,
    "reason": "not_run",
    "best_person": None,
    "best_similarity": None,
    "is_verified": False,
}

last_attendance_message = "NO ATTENDANCE YET"


# ============================================================
# WEBCAM LOOP
# ============================================================

cap = cv2.VideoCapture(CAMERA_INDEX)

if not cap.isOpened():
    raise RuntimeError("Cannot open webcam. Try CAMERA_INDEX = 1 or 2.")

print()
print("=" * 70)
print("WEBCAM")
print("=" * 70)
print("Webcam opened.")
print("Press Q to quit.")
print("Attendance POC running.")
print("=" * 70)

frame_id = 0

while True:
    ret, frame_bgr = cap.read()

    if not ret:
        print("Cannot read frame from webcam.")
        break

    frame_id += 1

    # Mirror view
    frame_bgr = cv2.flip(frame_bgr, 1)

    img_h, img_w = frame_bgr.shape[:2]

    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80),
    )

    face = get_largest_haar_face(faces)

    if face is not None:
        x, y, w, h = face

        x1, y1, x2, y2 = expand_bbox(
            x,
            y,
            w,
            h,
            img_w=img_w,
            img_h=img_h,
            margin=0.35,
        )

        if frame_id % PREDICT_EVERY_N_FRAMES == 0:
            # ------------------------------------------------------------
            # 1. Anti-spoof on face crop
            # ------------------------------------------------------------
            roi_bgr = frame_bgr[y1:y2, x1:x2]

            if roi_bgr.size > 0:
                roi_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
                face_real, face_fake = predict_antispoof_rgb(roi_rgb)
            else:
                face_real, face_fake = 0.0, 1.0

            # ------------------------------------------------------------
            # 2. Anti-spoof on full frame
            # ------------------------------------------------------------
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            full_real, full_fake = predict_antispoof_rgb(frame_rgb)

            last_face_real = face_real
            last_face_fake = face_fake
            last_full_real = full_real
            last_full_fake = full_fake

            frame_is_real = (
                face_real >= REAL_THRESHOLD_FACE and
                full_real >= REAL_THRESHOLD_FULL
            )

            score_buffer.append({
                "face_real": face_real,
                "full_real": full_real,
                "is_real": frame_is_real,
            })

            # ------------------------------------------------------------
            # 3. Liveness decision by temporal voting
            # ------------------------------------------------------------
            if len(score_buffer) < WINDOW_SIZE:
                last_liveness_status = "CHECKING"
                last_verify_result = {
                    "ok": False,
                    "reason": "checking_liveness",
                    "best_person": None,
                    "best_similarity": None,
                    "is_verified": False,
                }

            else:
                real_votes = sum(1 for item in score_buffer if item["is_real"])
                avg_face_real = float(np.mean([item["face_real"] for item in score_buffer]))
                avg_full_real = float(np.mean([item["full_real"] for item in score_buffer]))

                is_live_real = (
                    real_votes >= MIN_REAL_VOTES and
                    avg_face_real >= REAL_THRESHOLD_FACE and
                    avg_full_real >= REAL_THRESHOLD_FULL
                )

                if is_live_real:
                    last_liveness_status = "REAL_ATTENDANCE_OK"

                    # ----------------------------------------------------
                    # 4. Face verification
                    # ----------------------------------------------------
                    last_verify_result = verify_identity_bgr(frame_bgr)

                    if (
                        last_verify_result.get("ok") and
                        last_verify_result.get("is_verified")
                    ):
                        person_id = last_verify_result["best_person"]
                        similarity = last_verify_result["best_similarity"]

                        person_info = get_person_info(person_id, people_db)

                        if person_info.get("status") != "active":
                            last_attendance_message = f"INACTIVE USER: {person_id}"

                        else:
                            can_log, reason = can_log_attendance(
                                person_id,
                                attended_cache,
                            )

                            display_name = person_info.get("full_name", person_id) or person_id
                            student_code = person_info.get("student_code", "")
                            class_name = person_info.get("class_name", "")

                            if can_log:
                                csv_path = log_attendance(
                                    person_id=person_id,
                                    person_info=person_info,
                                    similarity=similarity,
                                    liveness_status=last_liveness_status,
                                    face_real_score=last_face_real,
                                    full_real_score=last_full_real,
                                    attended_cache=attended_cache,
                                )

                                if student_code:
                                    last_attendance_message = (
                                        f"ATTENDED: {display_name} ({student_code})"
                                    )
                                else:
                                    last_attendance_message = f"ATTENDED: {display_name}"

                                print(
                                    f"[ATTENDANCE] {person_id} - {display_name} "
                                    f"- {student_code} - {class_name} logged to {csv_path}"
                                )

                            else:
                                if student_code:
                                    last_attendance_message = (
                                        f"ALREADY ATTENDED TODAY: {display_name} ({student_code})"
                                    )
                                else:
                                    last_attendance_message = (
                                        f"ALREADY ATTENDED TODAY: {display_name}"
                                    )

                    elif last_verify_result.get("ok"):
                        person = last_verify_result.get("best_person")
                        sim = last_verify_result.get("best_similarity")

                        person_display = format_person_display(person, people_db)

                        last_attendance_message = (
                            f"REAL BUT UNKNOWN | best={person_display} sim={sim:.2f}"
                        )

                    else:
                        last_attendance_message = (
                            f"VERIFY FAILED: {last_verify_result.get('reason')}"
                        )

                else:
                    last_liveness_status = "FAKE_OR_SUSPECT"
                    last_verify_result = {
                        "ok": False,
                        "reason": "antispoof_failed",
                        "best_person": None,
                        "best_similarity": None,
                        "is_verified": False,
                    }
                    last_attendance_message = "NO LOG: FAKE/SUSPECT"

        # ------------------------------------------------------------
        # DRAW UI
        # ------------------------------------------------------------

        box_color = status_color(last_liveness_status)
        cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), box_color, 2)

        # Liveness status
        draw_text_with_bg(
            frame_bgr,
            last_liveness_status,
            (x1, max(30, y1 - 105)),
            font_scale=0.75,
            color=status_color(last_liveness_status),
            bg_color=(0, 0, 0),
        )

        # Scores
        score_text = (
            f"face_real={last_face_real:.2f} full_real={last_full_real:.2f} "
            f"buffer={len(score_buffer)}/{WINDOW_SIZE}"
        )

        draw_text_with_bg(
            frame_bgr,
            score_text,
            (x1, max(60, y1 - 75)),
            font_scale=0.55,
            color=(255, 255, 255),
            bg_color=(0, 0, 0),
        )

        # Votes
        if len(score_buffer) == WINDOW_SIZE:
            real_votes = sum(1 for item in score_buffer if item["is_real"])
            vote_text = f"real_votes={real_votes}/{WINDOW_SIZE}"
        else:
            vote_text = f"collecting frames {len(score_buffer)}/{WINDOW_SIZE}"

        draw_text_with_bg(
            frame_bgr,
            vote_text,
            (x1, max(90, y1 - 45)),
            font_scale=0.55,
            color=(255, 255, 255),
            bg_color=(0, 0, 0),
        )

        # Verification text
        if last_liveness_status == "REAL_ATTENDANCE_OK":
            if last_verify_result.get("ok") and last_verify_result.get("is_verified"):
                person = last_verify_result["best_person"]
                sim = last_verify_result["best_similarity"]

                person_display = format_person_display(person, people_db)

                verify_text = f"VERIFIED: {person_display} | sim={sim:.2f}"
                verify_color = (0, 255, 0)

            elif last_verify_result.get("ok"):
                person = last_verify_result["best_person"]
                sim = last_verify_result["best_similarity"]

                person_display = format_person_display(person, people_db)

                verify_text = f"REAL BUT UNKNOWN | best={person_display} sim={sim:.2f}"
                verify_color = (0, 255, 255)

            else:
                verify_text = f"VERIFY: {last_verify_result.get('reason')}"
                verify_color = (0, 255, 255)

        elif last_liveness_status == "FAKE_OR_SUSPECT":
            verify_text = "VERIFY SKIPPED: FAKE/SUSPECT"
            verify_color = (0, 0, 255)

        else:
            verify_text = "VERIFY WAITING"
            verify_color = (0, 255, 255)

        draw_text_with_bg(
            frame_bgr,
            verify_text,
            (x1, min(img_h - 60, y2 + 30)),
            font_scale=0.62,
            color=verify_color,
            bg_color=(0, 0, 0),
        )

        # Attendance message
        if last_attendance_message.startswith("ATTENDED"):
            attend_color = (0, 255, 0)
        elif last_attendance_message.startswith("ALREADY"):
            attend_color = (0, 255, 255)
        elif "UNKNOWN" in last_attendance_message:
            attend_color = (0, 255, 255)
        elif "NO LOG" in last_attendance_message or "FAILED" in last_attendance_message:
            attend_color = (0, 0, 255)
        else:
            attend_color = (255, 255, 255)

        draw_text_with_bg(
            frame_bgr,
            last_attendance_message,
            (x1, min(img_h - 20, y2 + 60)),
            font_scale=0.62,
            color=attend_color,
            bg_color=(0, 0, 0),
        )

    else:
        # Nếu không có mặt thì reset temporal buffer để không dùng score cũ
        score_buffer.clear()
        last_liveness_status = "NO_FACE"
        last_verify_result = {
            "ok": False,
            "reason": "no_face",
            "best_person": None,
            "best_similarity": None,
            "is_verified": False,
        }

        draw_text_with_bg(
            frame_bgr,
            "No face detected",
            (30, 40),
            font_scale=0.8,
            color=(0, 0, 255),
            bg_color=(0, 0, 0),
        )

    # Footer
    footer = (
        f"Attendance POC | log={today_csv.name} | "
        f"people={len(people_db)} | Q: quit"
    )

    draw_text_with_bg(
        frame_bgr,
        footer,
        (10, img_h - 15),
        font_scale=0.55,
        color=(255, 255, 255),
        bg_color=(0, 0, 0),
    )

    cv2.imshow("Attendance POC - AntiSpoof + Verification + Logging", frame_bgr)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break


cap.release()
cv2.destroyAllWindows()

print("Webcam closed.")
print("Attendance file:", today_csv)