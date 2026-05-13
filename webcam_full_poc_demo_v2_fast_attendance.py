import cv2
import json
import pickle
from pathlib import Path
from collections import deque

import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image, ImageFile

from insightface.app import FaceAnalysis


ImageFile.LOAD_TRUNCATED_IMAGES = True


# =========================
# CONFIG
# =========================

BASE_DIR = Path(r"C:\Users\Hoannd\Downloads\data_face")

ANTI_MODEL_PATH = BASE_DIR / "models" / "vfa_mobilenetv3_small_best.pth"
ANTI_CONFIG_PATH = BASE_DIR / "models" / "vfa_deploy_config.json"

VERIFY_DIR = BASE_DIR / "face_verification_poc"
TEMPLATES_PATH = VERIFY_DIR / "person_templates.pkl"
VERIFY_CONFIG_PATH = VERIFY_DIR / "face_verification_config.json"

CAMERA_INDEX = 2
IMG_SIZE = 224

# Fast attendance anti-spoof config
REAL_THRESHOLD_FACE = 0.75
REAL_THRESHOLD_FULL = 0.55

WINDOW_SIZE = 7
MIN_REAL_VOTES = 5

PREDICT_EVERY_N_FRAMES = 1

DEFAULT_VERIFY_THRESHOLD = 0.35


# =========================
# CHECK FILES
# =========================

required_files = [
    ANTI_MODEL_PATH,
    ANTI_CONFIG_PATH,
    TEMPLATES_PATH,
    VERIFY_CONFIG_PATH,
]

for p in required_files:
    print(p, "exists:", p.exists())

missing = [str(p) for p in required_files if not p.exists()]
if missing:
    raise FileNotFoundError(
        "Thiếu file cần thiết:\n" + "\n".join(missing)
    )


# =========================
# DEVICE
# =========================

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Device:", device)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))


# =========================
# LOAD VERIFICATION CONFIG
# =========================

with open(VERIFY_CONFIG_PATH, "r", encoding="utf-8") as f:
    verify_config = json.load(f)

VERIFY_THRESHOLD = float(
    verify_config.get("verify_threshold", DEFAULT_VERIFY_THRESHOLD)
)

print("VERIFY_THRESHOLD:", VERIFY_THRESHOLD)


# =========================
# LOAD PERSON TEMPLATES
# =========================

with open(TEMPLATES_PATH, "rb") as f:
    person_templates = pickle.load(f)

print("Loaded persons:", list(person_templates.keys()))


# =========================
# LOAD ANTI-SPOOF MODEL
# =========================

anti_checkpoint = torch.load(ANTI_MODEL_PATH, map_location=device)

classes = anti_checkpoint.get("classes", ["fake", "real"])
class_to_idx = anti_checkpoint.get("class_to_idx", {"fake": 0, "real": 1})

print("Anti-spoof classes:", classes)
print("Anti-spoof class_to_idx:", class_to_idx)
print("REAL_THRESHOLD_FACE:", REAL_THRESHOLD_FACE)
print("REAL_THRESHOLD_FULL:", REAL_THRESHOLD_FULL)

num_classes = len(classes)

anti_model = models.mobilenet_v3_small(weights=None)
in_features = anti_model.classifier[3].in_features
anti_model.classifier[3] = nn.Linear(in_features, num_classes)

anti_model.load_state_dict(anti_checkpoint["model_state_dict"])
anti_model = anti_model.to(device)
anti_model.eval()

fake_idx = class_to_idx["fake"]
real_idx = class_to_idx["real"]


# =========================
# TRANSFORM
# =========================

eval_tfms = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


# =========================
# HAAR FACE DETECTOR FOR BOX
# =========================

haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(haar_path)

if face_cascade.empty():
    raise RuntimeError("Cannot load Haar Cascade face detector.")

print("Haar Cascade loaded:", haar_path)


# =========================
# INSIGHTFACE
# =========================

face_app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)

face_app.prepare(ctx_id=0, det_size=(640, 640))

print("InsightFace loaded.")


# =========================
# HELPER FUNCTIONS
# =========================

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


def draw_text_with_bg(
    img,
    text,
    org,
    font_scale=0.7,
    color=(255, 255, 255),
    bg_color=(0, 0, 0)
):
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 2

    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    x, y = org

    cv2.rectangle(
        img,
        (x - 4, y - th - 8),
        (x + tw + 4, y + baseline + 4),
        bg_color,
        -1
    )

    cv2.putText(
        img,
        text,
        (x, y),
        font,
        font_scale,
        color,
        thickness,
        cv2.LINE_AA
    )


# =========================
# TEMPORAL BUFFER
# =========================

score_buffer = deque(maxlen=WINDOW_SIZE)

last_status = "WAITING"
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


# =========================
# WEBCAM LOOP
# =========================

cap = cv2.VideoCapture(CAMERA_INDEX)

if not cap.isOpened():
    raise RuntimeError("Cannot open webcam. Try CAMERA_INDEX = 1 or 2.")

print("Webcam opened.")
print("Press Q to quit.")
print("Full POC fast attendance mode.")

frame_id = 0

while True:
    ret, frame_bgr = cap.read()

    if not ret:
        print("Cannot read frame from webcam.")
        break

    frame_id += 1

    frame_bgr = cv2.flip(frame_bgr, 1)
    img_h, img_w = frame_bgr.shape[:2]

    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80)
    )

    face = get_largest_haar_face(faces)

    if face is not None:
        x, y, w, h = face

        x1, y1, x2, y2 = expand_bbox(
            x, y, w, h,
            img_w=img_w,
            img_h=img_h,
            margin=0.35
        )

        if frame_id % PREDICT_EVERY_N_FRAMES == 0:
            # 1. Anti-spoof trên face crop
            roi_bgr = frame_bgr[y1:y2, x1:x2]
            roi_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
            face_real, face_fake = predict_antispoof_rgb(roi_rgb)

            # 2. Anti-spoof trên full frame
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
                "is_real": frame_is_real
            })

            if len(score_buffer) < WINDOW_SIZE:
                last_status = "CHECKING"
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

                if (
                    real_votes >= MIN_REAL_VOTES and
                    avg_face_real >= REAL_THRESHOLD_FACE and
                    avg_full_real >= REAL_THRESHOLD_FULL
                ):
                    last_status = "REAL_ATTENDANCE_OK"
                    last_verify_result = verify_identity_bgr(frame_bgr)
                else:
                    last_status = "FAKE_OR_SUSPECT"
                    last_verify_result = {
                        "ok": False,
                        "reason": "antispoof_failed",
                        "best_person": None,
                        "best_similarity": None,
                        "is_verified": False,
                    }

        # box color
        if last_status == "REAL_ATTENDANCE_OK":
            box_color = (0, 255, 0)
        elif last_status == "FAKE_OR_SUSPECT":
            box_color = (0, 0, 255)
        else:
            box_color = (0, 255, 255)

        cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), box_color, 2)

        # anti-spoof status
        if last_status == "REAL_ATTENDANCE_OK":
            status_color = (0, 255, 0)
        elif last_status == "FAKE_OR_SUSPECT":
            status_color = (0, 0, 255)
        else:
            status_color = (0, 255, 255)

        draw_text_with_bg(
            frame_bgr,
            last_status,
            (x1, max(30, y1 - 70)),
            font_scale=0.75,
            color=status_color,
            bg_color=(0, 0, 0)
        )

        score_text = (
            f"face_real={last_face_real:.2f} full_real={last_full_real:.2f} "
            f"buffer={len(score_buffer)}/{WINDOW_SIZE}"
        )

        draw_text_with_bg(
            frame_bgr,
            score_text,
            (x1, max(60, y1 - 40)),
            font_scale=0.55,
            color=(255, 255, 255),
            bg_color=(0, 0, 0)
        )

        if len(score_buffer) == WINDOW_SIZE:
            real_votes = sum(1 for item in score_buffer if item["is_real"])
            vote_text = f"real_votes={real_votes}/{WINDOW_SIZE}"
        else:
            vote_text = f"collecting frames {len(score_buffer)}/{WINDOW_SIZE}"

        draw_text_with_bg(
            frame_bgr,
            vote_text,
            (x1, max(90, y1 - 10)),
            font_scale=0.55,
            color=(255, 255, 255),
            bg_color=(0, 0, 0)
        )

        # verification status
        if last_status == "REAL_ATTENDANCE_OK":
            if last_verify_result.get("ok") and last_verify_result.get("is_verified"):
                person = last_verify_result["best_person"]
                sim = last_verify_result["best_similarity"]
                verify_text = f"VERIFIED: {person} | sim={sim:.2f}"
                verify_color = (0, 255, 0)
            elif last_verify_result.get("ok"):
                person = last_verify_result["best_person"]
                sim = last_verify_result["best_similarity"]
                verify_text = f"REAL BUT UNKNOWN | best={person} sim={sim:.2f}"
                verify_color = (0, 255, 255)
            else:
                verify_text = f"VERIFY: {last_verify_result.get('reason')}"
                verify_color = (0, 255, 255)
        elif last_status == "FAKE_OR_SUSPECT":
            verify_text = "VERIFY SKIPPED: FAKE/SUSPECT"
            verify_color = (0, 0, 255)
        else:
            verify_text = "VERIFY WAITING: liveness check"
            verify_color = (0, 255, 255)

        draw_text_with_bg(
            frame_bgr,
            verify_text,
            (x1, min(img_h - 20, y2 + 30)),
            font_scale=0.65,
            color=verify_color,
            bg_color=(0, 0, 0)
        )

    else:
        score_buffer.clear()
        last_status = "NO_FACE"
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
            bg_color=(0, 0, 0)
        )

    footer = (
        f"Fast attendance | verify_th={VERIFY_THRESHOLD:.2f} | "
        f"Q: quit"
    )

    draw_text_with_bg(
        frame_bgr,
        footer,
        (10, img_h - 15),
        font_scale=0.55,
        color=(255, 255, 255),
        bg_color=(0, 0, 0)
    )

    cv2.imshow("Full POC V2 - Fast Attendance AntiSpoof + Verification", frame_bgr)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("Webcam closed.")