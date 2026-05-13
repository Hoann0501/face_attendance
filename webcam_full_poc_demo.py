import cv2
import json
import pickle
from pathlib import Path

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

DEFAULT_REAL_THRESHOLD = 0.90
DEFAULT_VERIFY_THRESHOLD = 0.35

# Baseline anti-spoofing tốt nhất của mình train trên ảnh nguyên tấm.
# Vì vậy để True trước.
USE_FULL_FRAME_FOR_ANTISPOOF = False

# Đỡ lag CPU: chỉ predict mỗi N frame.
PREDICT_EVERY_N_FRAMES = 5


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
        "Thiếu file cần thiết:\n" + "\n".join(missing) +
        "\n\nHãy chạy xong notebook anti-spoofing và Cell 21-24 của face verification trước."
    )


# =========================
# DEVICE
# =========================

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Device:", device)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))


# =========================
# LOAD ANTI-SPOOF CONFIG
# =========================

with open(ANTI_CONFIG_PATH, "r", encoding="utf-8") as f:
    anti_config = json.load(f)

REAL_THRESHOLD = float(
    anti_config.get("deploy_threshold_real", DEFAULT_REAL_THRESHOLD)
)

print("Anti-spoof threshold:", REAL_THRESHOLD)


# =========================
# LOAD VERIFICATION CONFIG
# =========================

with open(VERIFY_CONFIG_PATH, "r", encoding="utf-8") as f:
    verify_config = json.load(f)

VERIFY_THRESHOLD = float(
    verify_config.get("verify_threshold", DEFAULT_VERIFY_THRESHOLD)
)

print("Verify threshold:", VERIFY_THRESHOLD)


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
# LOAD FACE DETECTOR FOR BOX
# =========================

haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(haar_path)

if face_cascade.empty():
    raise RuntimeError("Cannot load Haar Cascade face detector.")

print("Haar Cascade loaded:", haar_path)


# =========================
# LOAD INSIGHTFACE
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

    pred_label = "REAL" if real_score >= REAL_THRESHOLD else "FAKE"

    return pred_label, real_score, fake_score


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


def draw_text_with_bg(img, text, org, font_scale=0.7, color=(255, 255, 255), bg_color=(0, 0, 0)):
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
# WEBCAM LOOP
# =========================

cap = cv2.VideoCapture(CAMERA_INDEX)

if not cap.isOpened():
    raise RuntimeError("Cannot open webcam. Try CAMERA_INDEX = 1 or 2.")

print("Webcam opened.")
print("Press Q to quit.")

frame_id = 0

last_anti_label = "WAIT"
last_real_score = 0.0
last_fake_score = 0.0

last_verify_result = {
    "ok": False,
    "reason": "not_run",
    "best_person": None,
    "best_similarity": None,
    "is_verified": False,
}

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

        # predict mỗi vài frame để đỡ lag
        if frame_id % PREDICT_EVERY_N_FRAMES == 0:
            if USE_FULL_FRAME_FOR_ANTISPOOF:
                anti_input_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            else:
                roi_bgr = frame_bgr[y1:y2, x1:x2]
                anti_input_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)

            last_anti_label, last_real_score, last_fake_score = predict_antispoof_rgb(
                anti_input_rgb
            )

            if last_anti_label == "REAL":
                last_verify_result = verify_identity_bgr(frame_bgr)
            else:
                last_verify_result = {
                    "ok": False,
                    "reason": "antispoof_fake",
                    "best_person": None,
                    "best_similarity": None,
                    "is_verified": False,
                }

        # bbox xanh lá nếu detect mặt
        box_color = (0, 255, 0)
        cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), box_color, 2)

        # anti-spoof text
        if last_anti_label == "REAL":
            anti_color = (0, 255, 0)
        elif last_anti_label == "FAKE":
            anti_color = (0, 0, 255)
        else:
            anti_color = (255, 255, 255)

        anti_text = f"{last_anti_label} | real={last_real_score:.2f} fake={last_fake_score:.2f}"
        draw_text_with_bg(
            frame_bgr,
            anti_text,
            (x1, max(30, y1 - 12)),
            font_scale=0.7,
            color=anti_color,
            bg_color=(0, 0, 0)
        )

        # verification text
        if last_anti_label == "REAL":
            if last_verify_result.get("ok") and last_verify_result.get("is_verified"):
                person = last_verify_result["best_person"]
                sim = last_verify_result["best_similarity"]
                verify_text = f"VERIFIED: {person} | sim={sim:.2f}"
                verify_color = (0, 255, 0)
            elif last_verify_result.get("ok"):
                person = last_verify_result["best_person"]
                sim = last_verify_result["best_similarity"]
                verify_text = f"UNKNOWN / NOT MATCH | best={person} sim={sim:.2f}"
                verify_color = (0, 255, 255)
            else:
                verify_text = f"VERIFY: {last_verify_result.get('reason')}"
                verify_color = (0, 255, 255)
        else:
            verify_text = "VERIFY SKIPPED: FAKE"
            verify_color = (0, 0, 255)

        draw_text_with_bg(
            frame_bgr,
            verify_text,
            (x1, min(img_h - 20, y2 + 30)),
            font_scale=0.65,
            color=verify_color,
            bg_color=(0, 0, 0)
        )

    else:
        draw_text_with_bg(
            frame_bgr,
            "No face detected",
            (30, 40),
            font_scale=0.8,
            color=(0, 0, 255),
            bg_color=(0, 0, 0)
        )

    # footer
    footer = (
        f"anti_threshold={REAL_THRESHOLD:.2f} | "
        f"verify_threshold={VERIFY_THRESHOLD:.2f} | "
        f"press Q to quit"
    )
    draw_text_with_bg(
        frame_bgr,
        footer,
        (10, img_h - 15),
        font_scale=0.55,
        color=(255, 255, 255),
        bg_color=(0, 0, 0)
    )

    cv2.imshow("Full POC: Anti-Spoofing + Face Verification", frame_bgr)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("Webcam closed.")