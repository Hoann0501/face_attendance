import cv2
import json
from pathlib import Path

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np


# CONFIG
BASE_DIR = Path(r"C:\Users\Hoannd\Downloads\data_face")

MODEL_PATH = BASE_DIR / "models" / "vfa_mobilenetv3_small_best.pth"
CONFIG_PATH = BASE_DIR / "models" / "vfa_deploy_config.json"

IMG_SIZE = 224
DEFAULT_THRESHOLD_REAL = 0.90

CAMERA_INDEX = 2

USE_FACE_CROP_FOR_CLASSIFICATION = True


# LOAD CONFIG
if CONFIG_PATH.exists():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        deploy_config = json.load(f)

    THRESHOLD_REAL = float(
        deploy_config.get("deploy_threshold_real", DEFAULT_THRESHOLD_REAL)
    )
else:
    deploy_config = {}
    THRESHOLD_REAL = DEFAULT_THRESHOLD_REAL

print("MODEL_PATH:", MODEL_PATH)
print("CONFIG_PATH:", CONFIG_PATH)
print("THRESHOLD_REAL:", THRESHOLD_REAL)


# DEVICE
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Device:", device)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))


# TRANSFORM
eval_tfms = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


# LOAD MODEL
checkpoint = torch.load(MODEL_PATH, map_location=device)

classes = checkpoint.get("classes", ["fake", "real"])
class_to_idx = checkpoint.get("class_to_idx", {"fake": 0, "real": 1})

print("Classes:", classes)
print("Class to idx:", class_to_idx)

num_classes = len(classes)

model = models.mobilenet_v3_small(weights=None)
in_features = model.classifier[3].in_features
model.classifier[3] = nn.Linear(in_features, num_classes)

model.load_state_dict(checkpoint["model_state_dict"])
model = model.to(device)
model.eval()

fake_idx = class_to_idx["fake"]
real_idx = class_to_idx["real"]


# FACE DETECTOR
haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(haar_path)

if face_cascade.empty():
    raise RuntimeError("Cannot load Haar Cascade face detector.")

print("Haar Cascade loaded:", haar_path)


# HELPER FUNCTIONS
def expand_bbox(x, y, w, h, img_w, img_h, margin=0.35):
    mx = int(w * margin)
    my = int(h * margin)

    x1 = max(0, x - mx)
    y1 = max(0, y - my)
    x2 = min(img_w, x + w + mx)
    y2 = min(img_h, y + h + my)

    return x1, y1, x2, y2


def predict_rgb_image(img_rgb):
    """
    img_rgb: numpy RGB image
    return: pred_label, real_score, fake_score
    """
    pil_img = Image.fromarray(img_rgb).convert("RGB")
    x = eval_tfms(pil_img).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(x)
        probs = torch.softmax(logits, dim=1)[0].detach().cpu().numpy()

    fake_score = float(probs[fake_idx])
    real_score = float(probs[real_idx])

    if real_score >= THRESHOLD_REAL:
        pred_label = "REAL"
    else:
        pred_label = "FAKE"

    return pred_label, real_score, fake_score


def get_largest_face(faces):
    if len(faces) == 0:
        return None

    faces = sorted(faces, key=lambda box: box[2] * box[3], reverse=True)
    return faces[0]


# WEBCAM LOOP
cap = cv2.VideoCapture(CAMERA_INDEX)

if not cap.isOpened():
    raise RuntimeError("Cannot open webcam. Try CAMERA_INDEX = 1 or 2.")

print("Webcam opened.")
print("Press Q to quit.")

while True:
    ret, frame_bgr = cap.read()

    if not ret:
        print("Cannot read frame from webcam.")
        break

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

    if face is not None:
        x, y, w, h = face

        x1, y1, x2, y2 = expand_bbox(
            x, y, w, h,
            img_w=img_w,
            img_h=img_h,
            margin=0.35
        )

        # Vẽ bbox xanh lá quanh mặt
        cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)

        if USE_FACE_CROP_FOR_CLASSIFICATION:
            roi_bgr = frame_bgr[y1:y2, x1:x2]
            roi_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
            pred_label, real_score, fake_score = predict_rgb_image(roi_rgb)
        else:
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            pred_label, real_score, fake_score = predict_rgb_image(frame_rgb)

        if pred_label == "REAL":
            text_color = (0, 255, 0)
        else:
            text_color = (0, 0, 255)

        label_text = f"{pred_label} | real={real_score:.2f} fake={fake_score:.2f}"

        cv2.putText(
            frame_bgr,
            label_text,
            (x1, max(30, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            text_color,
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            frame_bgr,
            f"threshold_real={THRESHOLD_REAL:.2f}",
            (10, img_h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

    else:
        cv2.putText(
            frame_bgr,
            "No face detected",
            (30, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 0, 255),
            2,
            cv2.LINE_AA
        )

    cv2.imshow("VFA Anti-Spoofing Webcam Demo", frame_bgr)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("Webcam closed.")