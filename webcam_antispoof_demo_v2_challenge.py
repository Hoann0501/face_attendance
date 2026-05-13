import cv2
import json
import time
import random
from pathlib import Path

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np


# =========================
# CONFIG
# =========================

BASE_DIR = Path(r"C:\Users\Hoannd\Downloads\data_face")

MODEL_PATH = BASE_DIR / "models" / "vfa_mobilenetv3_small_best.pth"
CONFIG_PATH = BASE_DIR / "models" / "vfa_deploy_config.json"

IMG_SIZE = 224
CAMERA_INDEX = 2

# Threshold webcam nên nới hơn một chút so với test offline
REAL_THRESHOLD = 0.75

# Predict mỗi N frame cho đỡ lag CPU
PREDICT_EVERY_N_FRAMES = 5

# Challenge config
CHALLENGE_TIME_LIMIT = 5.0
MIN_REAL_FRAMES_REQUIRED = 5

# Mức di chuyển cần đạt
MOVE_X_RATIO = 0.12      # lệch trái/phải 12% chiều rộng frame
MOVE_AREA_RATIO = 0.30   # lại gần: diện tích mặt tăng 30%

CHALLENGES = ["MOVE_LEFT", "MOVE_RIGHT", "MOVE_CLOSER"]


# =========================
# DEVICE
# =========================

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Device:", device)


# =========================
# LOAD MODEL
# =========================

checkpoint = torch.load(MODEL_PATH, map_location=device)

classes = checkpoint.get("classes", ["fake", "real"])
class_to_idx = checkpoint.get("class_to_idx", {"fake": 0, "real": 1})

print("Classes:", classes)
print("Class to idx:", class_to_idx)
print("REAL_THRESHOLD:", REAL_THRESHOLD)

num_classes = len(classes)

model = models.mobilenet_v3_small(weights=None)
in_features = model.classifier[3].in_features
model.classifier[3] = nn.Linear(in_features, num_classes)

model.load_state_dict(checkpoint["model_state_dict"])
model = model.to(device)
model.eval()

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
# FACE DETECTOR
# =========================

haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(haar_path)

if face_cascade.empty():
    raise RuntimeError("Cannot load Haar Cascade face detector.")

print("Haar Cascade loaded:", haar_path)


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


def get_largest_face(faces):
    if len(faces) == 0:
        return None
    faces = sorted(faces, key=lambda box: box[2] * box[3], reverse=True)
    return faces[0]


def predict_rgb_image(img_rgb):
    pil_img = Image.fromarray(img_rgb).convert("RGB")
    x = eval_tfms(pil_img).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(x)
        probs = torch.softmax(logits, dim=1)[0].detach().cpu().numpy()

    fake_score = float(probs[fake_idx])
    real_score = float(probs[real_idx])

    pred_label = "REAL_MODEL" if real_score >= REAL_THRESHOLD else "FAKE_MODEL"

    return pred_label, real_score, fake_score


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


def new_challenge():
    return {
        "type": random.choice(CHALLENGES),
        "start_time": time.time(),
        "start_center_x": None,
        "start_area": None,
        "passed": False,
        "real_frames": 0
    }


def challenge_text(challenge_type):
    if challenge_type == "MOVE_LEFT":
        return "CHALLENGE: Move your face LEFT"
    if challenge_type == "MOVE_RIGHT":
        return "CHALLENGE: Move your face RIGHT"
    if challenge_type == "MOVE_CLOSER":
        return "CHALLENGE: Move CLOSER to camera"
    return "CHALLENGE"


def update_challenge(challenge, center_x, face_area, frame_w, model_is_real):
    if challenge["start_center_x"] is None:
        challenge["start_center_x"] = center_x
        challenge["start_area"] = face_area

    if model_is_real:
        challenge["real_frames"] += 1

    dx = center_x - challenge["start_center_x"]
    area_growth = (face_area - challenge["start_area"]) / max(challenge["start_area"], 1)

    passed_motion = False

    if challenge["type"] == "MOVE_LEFT":
        # Vì frame đã flip mirror, người dùng dịch sang trái màn hình thì center_x giảm
        passed_motion = dx < -MOVE_X_RATIO * frame_w

    elif challenge["type"] == "MOVE_RIGHT":
        passed_motion = dx > MOVE_X_RATIO * frame_w

    elif challenge["type"] == "MOVE_CLOSER":
        passed_motion = area_growth > MOVE_AREA_RATIO

    enough_real_frames = challenge["real_frames"] >= MIN_REAL_FRAMES_REQUIRED

    if passed_motion and enough_real_frames:
        challenge["passed"] = True

    return challenge, dx, area_growth


# =========================
# WEBCAM LOOP
# =========================

cap = cv2.VideoCapture(CAMERA_INDEX)

if not cap.isOpened():
    raise RuntimeError("Cannot open webcam. Try CAMERA_INDEX = 1 or 2.")

print("Webcam opened.")
print("Press Q to quit.")
print("Press R to reset challenge.")

challenge = new_challenge()

frame_id = 0
last_model_label = "WAIT"
last_real_score = 0.0
last_fake_score = 0.0
final_status = "CHECKING"

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

    face = get_largest_face(faces)

    elapsed = time.time() - challenge["start_time"]
    remaining = max(0.0, CHALLENGE_TIME_LIMIT - elapsed)

    if face is not None:
        x, y, w, h = face

        x1, y1, x2, y2 = expand_bbox(
            x, y, w, h,
            img_w=img_w,
            img_h=img_h,
            margin=0.35
        )

        center_x = x + w / 2
        face_area = w * h

        # Predict anti-spoof trên vùng mặt crop
        if frame_id % PREDICT_EVERY_N_FRAMES == 0:
            roi_bgr = frame_bgr[y1:y2, x1:x2]
            roi_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)

            last_model_label, last_real_score, last_fake_score = predict_rgb_image(roi_rgb)

        model_is_real = last_real_score >= REAL_THRESHOLD

        challenge, dx, area_growth = update_challenge(
            challenge,
            center_x=center_x,
            face_area=face_area,
            frame_w=img_w,
            model_is_real=model_is_real
        )

        if challenge["passed"]:
            final_status = "LIVE_REAL"
        elif elapsed > CHALLENGE_TIME_LIMIT:
            final_status = "NOT_LIVE_OR_FAKE"
        else:
            final_status = "CHECKING"

        # Draw bbox
        if final_status == "LIVE_REAL":
            box_color = (0, 255, 0)
        elif final_status == "NOT_LIVE_OR_FAKE":
            box_color = (0, 0, 255)
        else:
            box_color = (0, 255, 255)

        cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), box_color, 2)

        # Texts
        draw_text_with_bg(
            frame_bgr,
            f"MODEL: real={last_real_score:.2f} fake={last_fake_score:.2f}",
            (x1, max(30, y1 - 45)),
            font_scale=0.65,
            color=(255, 255, 255),
            bg_color=(0, 0, 0)
        )

        draw_text_with_bg(
            frame_bgr,
            challenge_text(challenge["type"]),
            (x1, max(60, y1 - 15)),
            font_scale=0.7,
            color=(0, 255, 255),
            bg_color=(0, 0, 0)
        )

        if final_status == "LIVE_REAL":
            status_color = (0, 255, 0)
        elif final_status == "NOT_LIVE_OR_FAKE":
            status_color = (0, 0, 255)
        else:
            status_color = (0, 255, 255)

        draw_text_with_bg(
            frame_bgr,
            f"STATUS: {final_status} | time={remaining:.1f}s",
            (x1, min(img_h - 20, y2 + 30)),
            font_scale=0.75,
            color=status_color,
            bg_color=(0, 0, 0)
        )

        debug_text = (
            f"real_frames={challenge['real_frames']} "
            f"dx={dx:.1f} area_growth={area_growth:.2f}"
        )

        draw_text_with_bg(
            frame_bgr,
            debug_text,
            (10, img_h - 45),
            font_scale=0.55,
            color=(255, 255, 255),
            bg_color=(0, 0, 0)
        )

    else:
        final_status = "NO_FACE"
        draw_text_with_bg(
            frame_bgr,
            "No face detected",
            (30, 40),
            font_scale=0.8,
            color=(0, 0, 255),
            bg_color=(0, 0, 0)
        )

    footer = "Q: quit | R: reset challenge"
    draw_text_with_bg(
        frame_bgr,
        footer,
        (10, img_h - 15),
        font_scale=0.55,
        color=(255, 255, 255),
        bg_color=(0, 0, 0)
    )

    cv2.imshow("VFA Anti-Spoofing Demo V2 - Active Liveness", frame_bgr)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

    if key == ord("r"):
        challenge = new_challenge()
        final_status = "CHECKING"
        print("Challenge reset:", challenge["type"])

    # Nếu challenge timeout, tự tạo challenge mới sau 1 giây
    if final_status == "NOT_LIVE_OR_FAKE" and elapsed > CHALLENGE_TIME_LIMIT + 1.0:
        challenge = new_challenge()
        final_status = "CHECKING"
        print("New challenge:", challenge["type"])

cap.release()
cv2.destroyAllWindows()
print("Webcam closed.")