import cv2
import csv
import pickle
from pathlib import Path
from datetime import datetime

import numpy as np
from insightface.app import FaceAnalysis


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(r"C:\Users\Hoannd\Downloads\data_face")

VERIFY_DIR = BASE_DIR / "face_verification_poc"

ENROLL_DIR = VERIFY_DIR / "enroll"
PEOPLE_CSV_PATH = VERIFY_DIR / "people.csv"
TEMPLATES_PATH = VERIFY_DIR / "person_templates.pkl"

CAMERA_INDEX = 2

NUM_IMAGES_TO_CAPTURE = 5
MIN_FACE_SCORE = 0.5


# ============================================================
# INIT
# ============================================================

ENROLL_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("REGISTER NEW PERSON")
print("=" * 70)

print("VERIFY_DIR:", VERIFY_DIR)
print("ENROLL_DIR:", ENROLL_DIR)
print("PEOPLE_CSV_PATH:", PEOPLE_CSV_PATH)
print("TEMPLATES_PATH:", TEMPLATES_PATH)


# ============================================================
# INPUT PERSON INFO
# ============================================================

person_id = input("Nhập person_id, ví dụ person_004: ").strip()
full_name = input("Nhập họ tên: ").strip()
student_code = input("Nhập mã sinh viên / mã nhân viên: ").strip()
class_name = input("Nhập lớp / phòng ban: ").strip()

if not person_id:
    raise ValueError("person_id không được rỗng.")

person_dir = ENROLL_DIR / person_id
person_dir.mkdir(parents=True, exist_ok=True)

print()
print("Thông tin đăng ký:")
print("person_id:", person_id)
print("full_name:", full_name)
print("student_code:", student_code)
print("class_name:", class_name)
print("person_dir:", person_dir)


# ============================================================
# LOAD INSIGHTFACE
# ============================================================

print()
print("Loading InsightFace...")

face_app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)

face_app.prepare(ctx_id=0, det_size=(640, 640))

print("InsightFace loaded.")


# ============================================================
# HELPERS
# ============================================================

def get_largest_face(faces):
    if len(faces) == 0:
        return None

    def area(face):
        x1, y1, x2, y2 = face.bbox
        return max(0, x2 - x1) * max(0, y2 - y1)

    return max(faces, key=area)


def extract_embedding_from_bgr(frame_bgr):
    faces = face_app.get(frame_bgr)
    face = get_largest_face(faces)

    if face is None:
        return None, None

    if float(face.det_score) < MIN_FACE_SCORE:
        return None, face

    emb = face.embedding.astype(np.float32)
    emb = emb / np.linalg.norm(emb)

    return emb, face


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


def ensure_people_csv(csv_path):
    if csv_path.exists():
        return

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "person_id",
            "full_name",
            "student_code",
            "class_name",
            "status",
        ])


def load_people_rows(csv_path):
    ensure_people_csv(csv_path)

    with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def save_people_rows(csv_path, rows):
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = [
            "person_id",
            "full_name",
            "student_code",
            "class_name",
            "status",
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            writer.writerow({
                "person_id": row.get("person_id", ""),
                "full_name": row.get("full_name", ""),
                "student_code": row.get("student_code", ""),
                "class_name": row.get("class_name", ""),
                "status": row.get("status", "active"),
            })


def upsert_people_csv(csv_path, person_id, full_name, student_code, class_name):
    rows = load_people_rows(csv_path)

    updated = False

    for row in rows:
        if row.get("person_id") == person_id:
            row["full_name"] = full_name
            row["student_code"] = student_code
            row["class_name"] = class_name
            row["status"] = "active"
            updated = True
            break

    if not updated:
        rows.append({
            "person_id": person_id,
            "full_name": full_name,
            "student_code": student_code,
            "class_name": class_name,
            "status": "active",
        })

    save_people_rows(csv_path, rows)


def load_templates(path):
    if not path.exists():
        return {}

    with open(path, "rb") as f:
        return pickle.load(f)


def save_templates(path, templates):
    with open(path, "wb") as f:
        pickle.dump(templates, f)


# ============================================================
# CAPTURE ENROLL IMAGES
# ============================================================

cap = cv2.VideoCapture(CAMERA_INDEX)

if not cap.isOpened():
    raise RuntimeError("Không mở được webcam. Thử CAMERA_INDEX = 1 hoặc 2.")

print()
print("Webcam opened.")
print("Hướng dẫn:")
print("- Nhìn thẳng camera.")
print("- Bấm SPACE để chụp ảnh hợp lệ.")
print("- Bấm Q để thoát.")
print(f"- Cần chụp {NUM_IMAGES_TO_CAPTURE} ảnh.")

captured_embeddings = []
captured_paths = []

while True:
    ret, frame_bgr = cap.read()

    if not ret:
        print("Không đọc được frame webcam.")
        break

    frame_bgr = cv2.flip(frame_bgr, 1)
    display_frame = frame_bgr.copy()

    emb, face = extract_embedding_from_bgr(frame_bgr)

    if face is not None:
        x1, y1, x2, y2 = face.bbox.astype(int)

        if emb is not None:
            box_color = (0, 255, 0)
            status_text = "FACE OK - Press SPACE to capture"
        else:
            box_color = (0, 255, 255)
            status_text = "FACE LOW SCORE"

        cv2.rectangle(display_frame, (x1, y1), (x2, y2), box_color, 2)
    else:
        status_text = "NO FACE"

    draw_text_with_bg(
        display_frame,
        f"Register: {person_id} | {full_name}",
        (20, 35),
        font_scale=0.75,
        color=(255, 255, 255),
        bg_color=(0, 0, 0),
    )

    draw_text_with_bg(
        display_frame,
        status_text,
        (20, 70),
        font_scale=0.75,
        color=(0, 255, 0) if emb is not None else (0, 255, 255),
        bg_color=(0, 0, 0),
    )

    draw_text_with_bg(
        display_frame,
        f"Captured: {len(captured_embeddings)}/{NUM_IMAGES_TO_CAPTURE}",
        (20, 105),
        font_scale=0.75,
        color=(255, 255, 255),
        bg_color=(0, 0, 0),
    )

    draw_text_with_bg(
        display_frame,
        "SPACE: capture | Q: quit",
        (20, display_frame.shape[0] - 20),
        font_scale=0.65,
        color=(255, 255, 255),
        bg_color=(0, 0, 0),
    )

    cv2.imshow("Register New Person", display_frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        print("User quit.")
        break

    if key == ord(" "):
        if emb is None:
            print("Không chụp: chưa detect được mặt hợp lệ.")
            continue

        img_idx = len(captured_embeddings) + 1
        img_path = person_dir / f"enroll_{img_idx:03d}.jpg"

        cv2.imwrite(str(img_path), frame_bgr)

        captured_embeddings.append(emb)
        captured_paths.append(str(img_path))

        print(f"Captured {img_idx}: {img_path}")

        if len(captured_embeddings) >= NUM_IMAGES_TO_CAPTURE:
            print("Đã chụp đủ ảnh.")
            break

cap.release()
cv2.destroyAllWindows()


# ============================================================
# SAVE TEMPLATE
# ============================================================

if len(captured_embeddings) == 0:
    raise RuntimeError("Không có ảnh/embedding nào được chụp. Hủy đăng ký.")

embs = np.stack(captured_embeddings)

template = embs.mean(axis=0)
template = template / np.linalg.norm(template)

templates = load_templates(TEMPLATES_PATH)
templates[person_id] = template

save_templates(TEMPLATES_PATH, templates)

print()
print("Saved template:", TEMPLATES_PATH)
print("Template persons:", list(templates.keys()))


# ============================================================
# UPDATE PEOPLE CSV
# ============================================================

upsert_people_csv(
    PEOPLE_CSV_PATH,
    person_id=person_id,
    full_name=full_name,
    student_code=student_code,
    class_name=class_name,
)

print("Updated people.csv:", PEOPLE_CSV_PATH)


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 70)
print("REGISTER DONE")
print("=" * 70)
print("person_id:", person_id)
print("full_name:", full_name)
print("student_code:", student_code)
print("class_name:", class_name)
print("captured_images:", len(captured_paths))

for p in captured_paths:
    print("-", p)