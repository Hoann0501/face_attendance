"""
Attendance Camera App — Multi-Face Mode (optimised for smooth FPS)

Usage:
    python camera_app/attendance_camera.py [--mode checkin|checkout] [--camera N] [--single]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import requests

DEPLOY_ROOT = Path(__file__).resolve().parent.parent
if str(DEPLOY_ROOT) not in sys.path:
    sys.path.insert(0, str(DEPLOY_ROOT))

from camera_app.camera_config import (
    ANTI_SPOOF_MODEL_PATH,
    TEMPLATES_PATH,
    BACKEND_URL,
    REAL_THRESHOLD_FACE,
    REAL_THRESHOLD_FULL,
    WINDOW_SIZE,
    MIN_REAL_VOTES,
    VERIFY_THRESHOLD,
    CAMERA_COOLDOWN_SECONDS,
)
from core.antispoof import AntiSpoofService
from core.face_verifier import FaceVerifier
from backend.config import FACE_CAPTURES_DIR


# ────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────

FONT      = cv2.FONT_HERSHEY_SIMPLEX
COL_WHITE  = (255, 255, 255)
COL_GREEN  = (50,  220,  80)
COL_RED    = (60,   60, 220)
COL_YELLOW = (30,  200, 220)
COL_BLUE   = (220, 150,  60)
COL_DARK   = (18,   18,  18)
COL_GRAY   = (120, 120, 120)

MODE_LABELS = { 'checkin': 'CHECK-IN', 'checkout': 'CHECK-OUT' }
MODE_COLORS = { 'checkin': COL_GREEN, 'checkout': COL_BLUE }


# ────────────────────────────────────────────────────────────
# Sharp-frame buffer
# ────────────────────────────────────────────────────────────

class SharpFrameBuffer:
    def __init__(self, maxlen: int = 20):
        self.maxlen = maxlen
        self._buf: list[tuple[np.ndarray, tuple, float]] = []

    def push(self, frame_bgr: np.ndarray, bbox: tuple | None) -> None:
        if bbox is None:
            return
        x1, y1, x2, y2 = bbox
        face = frame_bgr[y1:y2, x1:x2]
        if face.size == 0:
            return
        gray  = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
        score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        self._buf.append((frame_bgr.copy(), bbox, score))
        if len(self._buf) > self.maxlen:
            self._buf.pop(0)

    def get_sharpest(self) -> tuple[np.ndarray | None, tuple | None, float]:
        if not self._buf:
            return None, None, 0.0
        best = max(self._buf, key=lambda x: x[2])
        return best[0], best[1], best[2]

    def clear(self) -> None:
        self._buf.clear()

    def __len__(self) -> int:
        return len(self._buf)


# ────────────────────────────────────────────────────────────
# Face save
# ────────────────────────────────────────────────────────────

def _crop_face(frame_bgr: np.ndarray, bbox: tuple, margin: float = 0.45) -> np.ndarray | None:
    h, w = frame_bgr.shape[:2]
    x1, y1, x2, y2 = bbox
    bw, bh = x2 - x1, y2 - y1
    mx, my = int(bw * margin), int(bh * margin)
    cx1 = max(0, x1 - mx); cy1 = max(0, y1 - my)
    cx2 = min(w, x2 + mx); cy2 = min(h, y2 + my)
    crop = frame_bgr[cy1:cy2, cx1:cx2]
    return crop if crop.size > 0 else None


def _unsharp(img: np.ndarray, strength: float = 0.4, blur_sigma: float = 1.0) -> np.ndarray:
    blurred = cv2.GaussianBlur(img, (0, 0), blur_sigma)
    return cv2.addWeighted(img, 1.0 + strength, blurred, -strength, 0)


def _save_face_capture(
    frame_bgr: np.ndarray, bbox: tuple,
    person_id: str, mode: str,
    sharp_buffer: SharpFrameBuffer | None = None,
) -> str | None:
    try:
        if sharp_buffer and len(sharp_buffer) > 0:
            best_frame, best_bbox, score = sharp_buffer.get_sharpest()
            use_frame = best_frame if best_frame is not None else frame_bgr
            use_bbox  = best_bbox  if best_bbox  is not None else bbox
        else:
            use_frame = frame_bgr
            use_bbox  = bbox

        crop = _crop_face(use_frame, use_bbox, margin=0.45)
        if crop is None:
            return None
        crop = _unsharp(crop, strength=0.4)

        now      = time.strftime("%Y-%m-%d_%H-%M-%S")
        date_str = time.strftime("%Y-%m-%d")
        filename = f"{person_id}_{now}_{mode}.jpg"

        save_dir  = FACE_CAPTURES_DIR / date_str / mode
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / filename

        cv2.imwrite(str(save_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return str(save_path)
    except Exception as e:
        print(f"[Camera] Warning: could not save face capture: {e}")
        return None


# ────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────

def _parse_args():
    p = argparse.ArgumentParser(description="Attendance Camera")
    p.add_argument("--mode",   choices=["checkin", "checkout"], default=None)
    p.add_argument("--camera", type=int, default=None)
    p.add_argument(
        "--single",
        action="store_true",
        help="Disable multi-face mode (single-face only)",
    )
    return p.parse_args()


# ────────────────────────────────────────────────────────────
# Startup selection
# ────────────────────────────────────────────────────────────

def _probe_cameras(limit: int = 6) -> list[int]:
    available = []
    for i in range(limit):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available.append(i)
            cap.release()
    return available


def _select_interactively(mode_arg, camera_arg) -> tuple[str, int]:
    mode = mode_arg
    if mode is None:
        print()
        print("  ATTENDANCE CAMERA")
        print("  " + "─" * 30)
        print("  [1]  Check-In")
        print("  [2]  Check-Out")
        print()
        while True:
            try:
                c = input("  Select mode [1/2]: ").strip()
            except (EOFError, KeyboardInterrupt):
                sys.exit(0)
            if c == "1":
                mode = "checkin"; break
            elif c == "2":
                mode = "checkout"; break
            print("  Enter 1 or 2.")

    cam_idx = camera_arg
    if cam_idx is None:
        available = _probe_cameras()
        if not available:
            print("  No cameras found. Defaulting to index 0.")
            cam_idx = 0
        elif len(available) == 1:
            cam_idx = available[0]
            print(f"  Camera {cam_idx} selected (only option).")
        else:
            print()
            print("  Available cameras:")
            for idx in available:
                print(f"    [{idx}]  Camera {idx}")
            default = available[0]
            while True:
                try:
                    raw = input(f"  Select camera [{default}]: ").strip()
                    cam_idx = int(raw) if raw else default
                    if cam_idx not in available:
                        print(f"  Invalid index, choose from {available}.")
                    else:
                        break
                except (ValueError, EOFError, KeyboardInterrupt):
                    cam_idx = default; break

    print()
    print(f"  Mode:   {MODE_LABELS[mode]}")
    print(f"  Camera: {cam_idx}")
    print(f"  Backend: {BACKEND_URL}")
    print()
    return mode, cam_idx


# ────────────────────────────────────────────────────────────
# Backend calls
# ────────────────────────────────────────────────────────────

def _api_checkin_or_out(person_id, mode, sim, liveness, face_r, full_r) -> dict:
    path = "/attendance/check-in" if mode == "checkin" else "/attendance/check-out"
    try:
        r = requests.post(
            f"{BACKEND_URL}{path}",
            json={
                "person_id": person_id,
                "similarity": sim,
                "liveness_status": liveness,
                "face_real_score": face_r,
                "full_real_score": full_r,
            },
            timeout=5,
        )
        return r.json()
    except Exception as e:
        return {"ok": False, "action": "API_ERROR", "message": str(e)}


def _api_get_person(person_id) -> dict | None:
    try:
        r = requests.get(f"{BACKEND_URL}/people/{person_id}", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _precheck_can_check_out(person_id: str) -> tuple[bool, str]:
    try:
        r = requests.get(f"{BACKEND_URL}/attendance/today", timeout=3)
        if r.status_code != 200:
            return True, ""
        records = r.json().get("records") or []
        pid = str(person_id).strip()
        for rec in records:
            if str(rec.get("person_id", "")).strip() != pid:
                continue
            cin  = str(rec.get("check_in_time")  or "").strip()
            cout = str(rec.get("check_out_time") or "").strip()
            if not cin or cin.lower() in ("nan", "none", "null"):
                return False, "Chua check-in hom nay — hay Check-In (phim 1) truoc."
            if cout and cout.lower() not in ("nan", "none", "null"):
                return False, "Da check-out hom nay roi."
            return True, ""
        return False, "Chua check-in hom nay — chua co ban ghi diem danh."
    except Exception:
        return True, ""


# ────────────────────────────────────────────────────────────
# Drawing helpers
# ────────────────────────────────────────────────────────────

def _text_box(
    frame: np.ndarray, text: str, origin: tuple[int, int],
    font_scale: float = 0.55, color=COL_WHITE,
    bg=COL_DARK, pad: int = 6, thickness: int = 1,
):
    (tw, th), base = cv2.getTextSize(text, FONT, font_scale, thickness)
    x, y = origin
    cv2.rectangle(frame, (x - pad, y - th - pad), (x + tw + pad, y + base + pad // 2), bg, -1)
    cv2.putText(frame, text, (x, y), FONT, font_scale, color, thickness, cv2.LINE_AA)


def _draw_corner_marks(frame, x1, y1, x2, y2, color=COL_GREEN, length=14, thickness=2):
    for (cx, cy, dx, dy) in [
        (x1, y1,  1,  1), (x2, y1, -1,  1),
        (x1, y2,  1, -1), (x2, y2, -1, -1),
    ]:
        cv2.line(frame, (cx, cy), (cx + dx * length, cy), color, thickness)
        cv2.line(frame, (cx, cy), (cx, cy + dy * length), color, thickness)


def _draw_name_tag(frame, name: str, sub: str, x1: int, y2: int, x2: int, color=COL_GREEN):
    h, w = frame.shape[:2]
    pad = 8
    (nw, nh), _ = cv2.getTextSize(name, FONT, 0.60, 1)
    sw = 0
    if sub:
        (sw, _), _ = cv2.getTextSize(sub, FONT, 0.42, 1)
    box_w = max(nw, sw) + pad * 2
    box_h = nh + (16 if sub else 0) + pad * 2
    bx = max(0, min(x1, w - box_w))
    by = min(y2 + 4, h - box_h)
    overlay = frame.copy()
    cv2.rectangle(overlay, (bx, by), (bx + box_w, by + box_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
    cv2.putText(frame, name, (bx + pad, by + pad + nh), FONT, 0.60, color, 1, cv2.LINE_AA)
    if sub:
        cv2.putText(frame, sub, (bx + pad, by + pad + nh + 14), FONT, 0.42, COL_GRAY, 1, cv2.LINE_AA)


def _draw_topbar(frame, mode: str, multi: bool, fps: float, h: int, w: int):
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 34), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    col   = MODE_COLORS.get(mode, COL_WHITE)
    label = f"{MODE_LABELS.get(mode, mode.upper())} {'| MULTI' if multi else ''}"
    cv2.putText(frame, label, (12, 24), FONT, 0.55, col, 1, cv2.LINE_AA)

    fps_col = COL_GREEN if fps >= 20 else (COL_YELLOW if fps >= 10 else COL_RED)
    cv2.putText(frame, f"{fps:.0f} FPS", (w - 80, 24), FONT, 0.48, fps_col, 1, cv2.LINE_AA)


def _draw_bottombar(frame, h: int, w: int):
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - 26), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    cv2.putText(frame, "1: Check-In    2: Check-Out    Q: Quit",
                (12, h - 9), FONT, 0.38, COL_GRAY, 1, cv2.LINE_AA)


# ────────────────────────────────────────────────────────────
# Fast face detector — Haar cascade (runs in <5ms per frame)
# ────────────────────────────────────────────────────────────

class FastFaceDetector:
    """
    Uses OpenCV Haar cascade for detection (<5ms/frame on CPU).
    Lightweight and very fast — much better for real-time than
    running InsightFace detection every frame.
    """

    def __init__(self):
        self._cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        print("[FastFaceDetector] Haar cascade loaded (fast mode)")

    def detect(self, frame_bgr: np.ndarray, margin: float = 0.35) -> list[tuple]:
        """
        Returns list of (x1, y1, x2, y2) bboxes sorted by size descending.
        Runs in <5ms on CPU.
        """
        from core.utils import expand_bbox
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        raw = self._cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80),
        )
        img_h, img_w = frame_bgr.shape[:2]
        bboxes = []
        for (x, y, w, h) in raw:
            x1, y1, x2, y2 = expand_bbox(x, y, w, h, img_w, img_h, margin=margin)
            bboxes.append((x1, y1, x2, y2))
        bboxes.sort(key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True)
        return bboxes


# ────────────────────────────────────────────────────────────
# IoU-based face tracker
# ────────────────────────────────────────────────────────────

class FaceTracker:
    """
    Tracks faces across frames using IoU. Each detected face gets a stable
    ID that persists even when faces move. Unmatched faces get new IDs.
    """

    def __init__(self, iou_thresh: float = 0.25):
        self.iou_thresh = iou_thresh
        self._faces: dict[int, dict] = {}   # tid -> face dict
        self._next_id: int = 1

    def _iou(self, a: tuple, b: tuple) -> float:
        x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
        x2 = min(a[2], b[2]); y2 = min(a[3], b[3])
        if x2 <= x1 or y2 <= y1:
            return 0.0
        inter = (x2 - x1) * (y2 - y1)
        area_a = (a[2]-a[0]) * (a[3]-a[1])
        area_b = (b[2]-b[0]) * (b[3]-b[1])
        return inter / (area_a + area_b - inter + 1e-9)

    def update(self, bboxes: list[tuple]) -> dict[int, dict]:
        """Returns {tracker_id: face_dict} for current frame."""
        now = time.time()

        # Reset "matched" flag on all existing faces
        for fd in self._faces.values():
            fd["_matched"] = False

        # Expire stale faces (>4s unseen)
        for tid in list(self._faces.keys()):
            if now - self._faces[tid]["last_seen"] > 4.0:
                del self._faces[tid]

        used: set[int] = set()

        for bbox in bboxes:
            best_iou, best_tid = -1.0, None
            for tid, fdict in self._faces.items():
                if tid in used:
                    continue
                iou = self._iou(fdict["bbox"], bbox)
                if iou > best_iou:
                    best_iou, best_tid = iou, tid

            if best_tid is not None and best_iou >= self.iou_thresh:
                self._faces[best_tid]["bbox"] = bbox
                self._faces[best_tid]["last_seen"] = now
                self._faces[best_tid]["_matched"] = True
                used.add(best_tid)
            else:
                # New face: assign next available ID
                while self._next_id in self._faces:
                    self._next_id += 1
                tid = self._next_id
                self._next_id += 1
                self._faces[tid] = {
                    "bbox": bbox,
                    "last_seen": now,
                    "name": "",
                    "sub": "",
                    "tag_color": COL_GRAY,
                    "spoof_status": "NO_FACE",
                    "buf_stats": {},
                    "verified": False,
                    "attendance_done": False,
                    "person_id": "",
                    "best_sim": 0.0,
                    "code": "",
                    "cooldown_until": 0.0,
                    "sharp_buf": SharpFrameBuffer(maxlen=20),
                    "frame_counter": 0,
                    "_matched": True,
                    "_skipped_frames": 0,
                    "_spoof_buffer": [],
                }

        # Count consecutive skipped frames for unmatched faces
        for fd in self._faces.values():
            if not fd["_matched"]:
                fd["_skipped_frames"] = fd.get("_skipped_frames", 0) + 1
            else:
                fd["_skipped_frames"] = 0

        return dict(self._faces)


# ────────────────────────────────────────────────────────────
# Anti-spoof instance pool — ONE instance, reused per face via throttle
# ────────────────────────────────────────────────────────────

class AntiSpoofPool:
    """
    ONE AntiSpoofService model shared by all faces.
    Temporal buffers are per-face (not shared) to prevent vote mixing.
    """

    def __init__(
        self,
        model_path: str | Path,
        real_threshold_face: float = REAL_THRESHOLD_FACE,
        real_threshold_full: float = REAL_THRESHOLD_FULL,
        window_size: int = WINDOW_SIZE,
        min_real_votes: int = MIN_REAL_VOTES,
        throttle_frames: int = 5,
    ):
        self.throttle = throttle_frames
        self._model_path = model_path
        self._th_face   = real_threshold_face
        self._th_full   = real_threshold_full
        self._win_size  = window_size
        self._min_votes = min_real_votes

        self._service = AntiSpoofService(
            model_path=model_path,
            real_threshold_face=real_threshold_face,
            real_threshold_full=real_threshold_full,
            window_size=window_size,
            min_real_votes=min_real_votes,
        )
        print(f"[AntiSpoofPool] Shared model, per-face buffers, throttle={throttle_frames}")

    def process(self, face_dict: dict, face_crop_rgb: np.ndarray, frame_bgr: np.ndarray, frame_rgb: np.ndarray) -> None:
        """
        Call every frame for each tracked face.
        Updates spoof status only every N frames to keep FPS high.
        Temporal buffer is per-face (isolated from other faces).
        """
        fd = face_dict
        fd["frame_counter"] += 1

        # Throttle: skip anti-spoof most frames
        if fd["frame_counter"] % self.throttle != 0:
            return

        # Get per-face buffer from face_dict (isolated from other faces)
        buffer: list = fd.get("_spoof_buffer", [])
        if len(buffer) > self._win_size:
            buffer = buffer[-self._win_size:]

        # Predict
        face_real, _ = self._service.predict_face_crop(face_crop_rgb)
        full_real, _ = self._service.predict_full_frame(frame_rgb)
        fd["last_face_real"] = face_real
        fd["last_full_real"] = full_real

        frame_is_real = (
            face_real >= self._th_face
            and full_real >= self._th_full
        )

        buffer.append({"face_real": face_real, "full_real": full_real, "is_real": frame_is_real})
        fd["_spoof_buffer"] = buffer[-self._win_size:]

        if len(buffer) < self._win_size:
            fd["spoof_status"] = "CHECKING"
            fd["buf_stats"] = {"buffer_len": len(buffer), "window_size": self._win_size, "real_votes": 0}
            return

        real_votes = sum(1 for item in buffer if item["is_real"])
        avg_face = sum(item["face_real"] for item in buffer) / len(buffer)
        avg_full = sum(item["full_real"] for item in buffer) / len(buffer)

        if real_votes >= self._min_votes and avg_face >= self._th_face and avg_full >= self._th_full:
            fd["spoof_status"] = "REAL_ATTENDANCE_OK"
        else:
            fd["spoof_status"] = "FAKE_OR_SUSPECT"

        fd["buf_stats"] = {
            "buffer_len": len(buffer),
            "window_size": self._win_size,
            "real_votes": real_votes,
        }

        if fd["spoof_status"] in ("CHECKING", "REAL_ATTENDANCE_OK"):
            fd["sharp_buf"].push(frame_bgr, fd["bbox"])
        if fd["spoof_status"] == "FAKE_OR_SUSPECT":
            fd["sharp_buf"].clear()

    def reset_face(self, face_dict: dict) -> None:
        face_dict["sharp_buf"].clear()
        face_dict["frame_counter"] = 0
        face_dict["spoof_status"] = "NO_FACE"
        face_dict["buf_stats"] = {}
        face_dict["_spoof_buffer"] = []


# ────────────────────────────────────────────────────────────
# Face crop helper
# ────────────────────────────────────────────────────────────

def _extract_face_crop_rgb(frame_bgr: np.ndarray, bbox: tuple, margin=0.35) -> np.ndarray | None:
    x1, y1, x2, y2 = bbox
    ih, iw = frame_bgr.shape[:2]
    bw, bh = x2 - x1, y2 - y1
    mx, my = int(bw * margin), int(bh * margin)
    cx1 = max(0, x1 - mx); cy1 = max(0, y1 - my)
    cx2 = min(iw, x2 + mx); cy2 = min(ih, y2 + my)
    crop = frame_bgr[cy1:cy2, cx1:cx2]
    if crop.size == 0:
        return None
    return cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)


# ────────────────────────────────────────────────────────────
# Shared multi-face run logic (used by both modes)
# ────────────────────────────────────────────────────────────

def _run_multi(mode: str, cam_idx: int):
    # ── Load verifier (InsightFace for embedding only) ───────────
    print("[Camera] Loading face verifier (InsightFace for embedding)...")
    try:
        verifier = FaceVerifier(templates_path=TEMPLATES_PATH, verify_threshold=VERIFY_THRESHOLD)
    except Exception as e:
        print(f"[Camera] ERROR loading face verifier: {e}"); sys.exit(1)

    # ── Fast detector (Haar, <5ms/frame) ─────────────────────────
    print("[Camera] Loading fast face detector (Haar cascade)...")
    detector = FastFaceDetector()

    # ── Anti-spoof pool (one shared instance, throttled) ─────────
    print("[Camera] Loading anti-spoof pool...")
    anti_spoof_pool = AntiSpoofPool(
        model_path=ANTI_SPOOF_MODEL_PATH,
        real_threshold_face=REAL_THRESHOLD_FACE,
        real_threshold_full=REAL_THRESHOLD_FULL,
        window_size=WINDOW_SIZE,
        min_real_votes=MIN_REAL_VOTES,
        throttle_frames=5,
    )

    # ── Camera ───────────────────────────────────────────────────
    print(f"[Camera] Opening camera {cam_idx}...")
    cap = cv2.VideoCapture(cam_idx)
    if not cap.isOpened():
        print(f"[Camera] Cannot open camera {cam_idx}."); sys.exit(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    tracker = FaceTracker(iou_thresh=0.25)
    global_cooldown: dict[str, float] = {}
    fps_meter = 0.0
    fps_alpha = 0.1

    print("[Camera] Ready. Press Q to quit.")

    frame_count = 0
    last_fps_time = time.time()

    while True:
        t_loop_start = time.time()
        ret, frame = cap.read()
        if not ret:
            print("[Camera] Cannot read frame."); break

        frame = cv2.flip(frame, 1)
        h, w  = frame.shape[:2]
        frame_count += 1

        # Convert BGR→RGB once (used by anti-spoof and verifier)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # ── Detect all faces (Haar: <5ms) ────────────────────────────
        bboxes = detector.detect(frame, margin=0.35)
        faces = tracker.update(bboxes)  # {tid: face_dict}

        # ── Per-face processing ───────────────────────────────────────
        for tid, fd in faces.items():
            # Face not detected this frame → clear visual state immediately
            if not fd.get("_matched", True):
                fd["name"] = ""
                fd["sub"] = ""
                fd["tag_color"] = COL_GRAY
                fd["verified"] = False
                anti_spoof_pool.reset_face(fd)

            face_crop_rgb = _extract_face_crop_rgb(frame, fd["bbox"], margin=0.35)

            if face_crop_rgb is not None:
                # Anti-spoof (throttled: every 5th frame)
                anti_spoof_pool.process(fd, face_crop_rgb, frame, frame_rgb)
            else:
                anti_spoof_pool.reset_face(fd)
                fd["spoof_status"] = "NO_FACE"

            # ── Verification (once per face, when spoof passes) ────────
            now = time.time()
            in_cooldown = now < fd["cooldown_until"]
            pid_in_global = fd["person_id"] in global_cooldown

            if (
                fd["spoof_status"] == "REAL_ATTENDANCE_OK"
                and not fd["verified"]
                and not in_cooldown
                and not pid_in_global
            ):
                if face_crop_rgb is not None:
                    from PIL import Image as _PILImage
                    pil_crop = _PILImage.fromarray(face_crop_rgb)
                    emb, info = verifier.extract_embedding_pil(pil_crop)

                    if info.get("ok") and emb is not None:
                        top = verifier.search_top_k(emb, top_k=1)
                        if top and top[0]["similarity"] >= VERIFY_THRESHOLD:
                            fd["person_id"]  = top[0]["person_id"]
                            fd["best_sim"]   = top[0]["similarity"]
                            fd["verified"]   = True
                        else:
                            sim_val = top[0]["similarity"] if top else 0.0
                            fd["name"] = "Unknown"
                            fd["sub"]  = f"sim {sim_val:.3f}"
                            fd["cooldown_until"] = now + 3.0

            # ── Attendance (triggered once when verified + spoof OK) ─
            if (
                fd["verified"]
                and fd["spoof_status"] == "REAL_ATTENDANCE_OK"
                and not fd["attendance_done"]
                and not pid_in_global
            ):
                pid = fd["person_id"]
                person = _api_get_person(pid)

                if person and person.get("status") == "inactive":
                    fd["name"] = f"[Inactive] {person.get('full_name', pid)}"
                    fd["sub"]  = ""
                    fd["cooldown_until"] = now + CAMERA_COOLDOWN_SECONDS
                    global_cooldown[pid] = now + CAMERA_COOLDOWN_SECONDS
                else:
                    name = person.get("full_name", pid) if person else pid
                    code = person.get("student_code", "") if person else ""
                    fd["name"] = name
                    fd["code"] = code

                    proceed = True
                    if mode == "checkout":
                        ok_co, why = _precheck_can_check_out(pid)
                        if not ok_co:
                            fd["name"] = why
                            fd["sub"]  = ""
                            fd["cooldown_until"] = now + CAMERA_COOLDOWN_SECONDS
                            global_cooldown[pid] = now + CAMERA_COOLDOWN_SECONDS
                            proceed = False

                    if proceed:
                        result = _api_checkin_or_out(
                            pid, mode, fd["best_sim"],
                            fd["spoof_status"],
                            fd.get("last_face_real", 0.0),
                            fd.get("last_full_real", 0.0),
                        )
                        action = result.get("action", "")
                        if result.get("ok") and action in ("CHECKED_IN", "CHECKED_OUT"):
                            label = "Check-In OK" if action == "CHECKED_IN" else "Check-Out OK"
                            fd["name"] = name
                            fd["sub"]  = f"{code}  sim {fd['best_sim']:.3f}"
                            fd["tag_color"] = COL_GREEN
                            fd["attendance_done"] = True
                            global_cooldown[pid] = now + CAMERA_COOLDOWN_SECONDS

                            saved = _save_face_capture(
                                frame, fd["bbox"], pid, mode,
                                sharp_buffer=fd["sharp_buf"],
                            )
                            if saved:
                                print(f"[Camera] Saved: {saved}")
                            fd["sharp_buf"].clear()
                        elif action == "ALREADY_CHECKED_IN":
                            fd["name"] = name
                            fd["sub"]  = "Already checked in today"
                            fd["attendance_done"] = True
                            global_cooldown[pid] = now + CAMERA_COOLDOWN_SECONDS
                        elif action == "ALREADY_CHECKED_OUT":
                            fd["name"] = name
                            fd["sub"]  = "Already checked out today"
                            fd["attendance_done"] = True
                            global_cooldown[pid] = now + CAMERA_COOLDOWN_SECONDS
                        elif action == "NOT_CHECKED_IN":
                            fd["name"] = "Chua check-in"
                            fd["sub"]  = result.get("message", "")[:60] or "Hay Check-In (phim 1) truoc."
                            global_cooldown[pid] = now + CAMERA_COOLDOWN_SECONDS
                        else:
                            fd["name"] = action.replace("_", " ").title()
                            fd["sub"]  = result.get("message", "")[:50]
                            global_cooldown[pid] = now + CAMERA_COOLDOWN_SECONDS

            # ── Set tag color ─────────────────────────────────────────
            if fd["attendance_done"]:
                fd["tag_color"] = COL_GREEN
            elif fd["verified"]:
                fd["tag_color"] = COL_YELLOW
            elif fd["name"]:
                fd["tag_color"] = COL_GRAY

        # ── Expire stale global cooldowns ────────────────────────────
        now = time.time()
        global_cooldown = { pid: ts for pid, ts in global_cooldown.items() if ts > now }

        # ── Draw UI ──────────────────────────────────────────────────
        _draw_topbar(frame, mode, True, fps_meter, h, w)

        # Only draw faces that are currently detected (matched)
        matched_faces = {tid: fd for tid, fd in faces.items() if fd.get("_matched", True)}

        if not matched_faces:
            _draw_status_overlay_thin(frame, "No face detected", COL_GRAY)

        for tid, fd in matched_faces.items():
            x1, y1, x2, y2 = fd["bbox"]

            if fd["spoof_status"] == "REAL_ATTENDANCE_OK":
                col = COL_GREEN
            elif fd["spoof_status"] == "FAKE_OR_SUSPECT":
                col = COL_RED
            elif fd["spoof_status"] == "CHECKING":
                col = COL_YELLOW
            else:
                col = COL_GRAY

            _draw_corner_marks(frame, x1, y1, x2, y2, color=col, thickness=2)

            # Status label
            if fd["spoof_status"] == "CHECKING":
                buf = fd["buf_stats"]
                txt = f"Checking {buf.get('buffer_len',0)}/{buf.get('window_size',0)}"
                _draw_status_label(frame, txt, x1, y1, col)
            elif fd["spoof_status"] == "FAKE_OR_SUSPECT":
                _draw_status_label(frame, "Spoof!", x1, y1, col)

            # Name tag
            if fd["name"]:
                _draw_name_tag(
                    frame, fd["name"], fd["sub"],
                    x1, y2, x2, color=fd["tag_color"],
                )

        # Face count badge — only matched faces
        n = len(matched_faces)
        if n > 0:
            badge = f"{n} face{'s' if n > 1 else ''}"
            (tw, th), _ = cv2.getTextSize(badge, FONT, 0.44, 1)
            bx = max(0, w - tw - 24)
            cv2.rectangle(frame, (bx - 8, 36), (bx + tw + 8, 36 + th + 12), (0, 0, 0), -1)
            cv2.addWeighted(frame[36:36 + th + 12, bx - 8:bx + tw + 8], 0.65,
                            frame[36:36 + th + 12, bx - 8:bx + tw + 8], 0.35, 0, frame)
            cv2.putText(frame, badge, (bx, 36 + th + 4), FONT, 0.44, COL_WHITE, 1, cv2.LINE_AA)

        _draw_bottombar(frame, h, w)
        cv2.imshow("Face Attendance", frame)

        # ── FPS metering ─────────────────────────────────────────────
        elapsed = time.time() - t_loop_start
        fps_meter = fps_meter * (1 - fps_alpha) + (1.0 / elapsed) * fps_alpha if elapsed > 0 else 0

        # ── Key handling ──────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):
            break
        elif key == ord('1'):
            mode = "checkin"
            for fd in faces.values():
                anti_spoof_pool.reset_face(fd)
            global_cooldown.clear()
        elif key == ord('2'):
            mode = "checkout"
            for fd in faces.values():
                anti_spoof_pool.reset_face(fd)
            global_cooldown.clear()

    cap.release()
    cv2.destroyAllWindows()
    print("[Camera] Closed.")


def _draw_status_overlay_thin(frame, text: str, color):
    (tw, th), _ = cv2.getTextSize(text, FONT, 0.55, 1)
    x, y = 12, 60
    cv2.rectangle(frame, (x - 6, y - th - 6), (x + tw + 6, y + 6), (0, 0, 0), -1)
    cv2.putText(frame, text, (x, y), FONT, 0.55, color, 1, cv2.LINE_AA)


def _draw_status_label(frame, text: str, x1: int, y1: int, color):
    (tw, th), _ = cv2.getTextSize(text, FONT, 0.38, 1)
    cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw + 10, y1), (0, 0, 0), -1)
    cv2.putText(frame, text, (x1 + 5, y1 - 4), FONT, 0.38, color, 1, cv2.LINE_AA)


# ────────────────────────────────────────────────────────────
# Single-face run
# ────────────────────────────────────────────────────────────

def _run_single(mode: str, cam_idx: int):
    print("[Camera] Loading anti-spoof model...")
    try:
        spoof = AntiSpoofService(
            model_path=ANTI_SPOOF_MODEL_PATH,
            real_threshold_face=REAL_THRESHOLD_FACE,
            real_threshold_full=REAL_THRESHOLD_FULL,
            window_size=WINDOW_SIZE,
            min_real_votes=MIN_REAL_VOTES,
        )
    except Exception as e:
        print(f"[Camera] ERROR loading anti-spoof: {e}"); sys.exit(1)

    print("[Camera] Loading face verifier...")
    try:
        verifier = FaceVerifier(templates_path=TEMPLATES_PATH, verify_threshold=VERIFY_THRESHOLD)
    except Exception as e:
        print(f"[Camera] ERROR loading face verifier: {e}"); sys.exit(1)

    print(f"[Camera] Opening camera {cam_idx}...")
    cap = cv2.VideoCapture(cam_idx)
    if not cap.isOpened():
        print(f"[Camera] Cannot open camera {cam_idx}."); sys.exit(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    detector = FastFaceDetector()
    sharp_buf = SharpFrameBuffer(maxlen=20)
    last_bbox = None
    spoof_status = "WAITING"
    fps_meter = 0.0
    fps_alpha = 0.1
    cooldown_until = 0.0

    name = sub = ""
    tag_color = COL_WHITE
    show_tag = False

    print("[Camera] Ready (single-face mode).")

    while True:
        t_start = time.time()
        ret, frame = cap.read()
        if not ret:
            print("[Camera] Cannot read frame."); break

        frame = cv2.flip(frame, 1)
        h, w  = frame.shape[:2]

        bboxes = detector.detect(frame, margin=0.35)
        bbox = bboxes[0] if bboxes else None
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if bbox is not None:
            last_bbox = bbox
            face_crop_rgb = _extract_face_crop_rgb(frame, bbox, margin=0.35)
            if face_crop_rgb is not None:
                spoof_status = spoof.update(face_crop_rgb, frame_rgb)
                if spoof_status in ("CHECKING", "REAL_ATTENDANCE_OK"):
                    sharp_buf.push(frame, bbox)
        else:
            spoof.reset_buffer()
            spoof_status = "NO_FACE"
            last_bbox = None

        if spoof_status in ("FAKE_OR_SUSPECT", "NO_FACE"):
            show_tag = False
            if spoof_status == "FAKE_OR_SUSPECT":
                sharp_buf.clear()

        now = time.time()
        if spoof_status == "REAL_ATTENDANCE_OK" and now > cooldown_until:
            face_crop_rgb = _extract_face_crop_rgb(frame, last_bbox, margin=0.35) if last_bbox else None
            if face_crop_rgb is not None:
                from PIL import Image as _PILImage
                pil_crop = _PILImage.fromarray(face_crop_rgb)
                emb, info = verifier.extract_embedding_pil(pil_crop)

                if info.get("ok") and emb is not None:
                    top = verifier.search_top_k(emb, top_k=1)
                    if top and top[0]["similarity"] >= VERIFY_THRESHOLD:
                        best_pid = top[0]["person_id"]
                        best_sim = top[0]["similarity"]
                        person   = _api_get_person(best_pid)

                        if person and person.get("status") == "inactive":
                            name = f"[Inactive] {person.get('full_name', best_pid)}"
                            sub = ""; tag_color = COL_YELLOW; show_tag = True
                            cooldown_until = now + CAMERA_COOLDOWN_SECONDS
                        else:
                            name = person.get("full_name", best_pid) if person else best_pid
                            code = person.get("student_code", "") if person else ""
                            proceed = True
                            if mode == "checkout":
                                ok_co, why = _precheck_can_check_out(best_pid)
                                if not ok_co:
                                    name = why; sub = ""; tag_color = COL_RED; show_tag = True
                                    cooldown_until = now + CAMERA_COOLDOWN_SECONDS
                                    proceed = False
                            if proceed:
                                result = _api_checkin_or_out(
                                    best_pid, mode, best_sim, spoof_status,
                                    spoof.last_face_real, spoof.last_full_real,
                                )
                                action = result.get("action", "")
                                if result.get("ok") and action in ("CHECKED_IN", "CHECKED_OUT"):
                                    label = "Check-In OK" if action == "CHECKED_IN" else "Check-Out OK"
                                    name = label; sub = f"{name}  |  {code}  sim {best_sim:.3f}"
                                    tag_color = COL_GREEN; show_tag = True
                                    cooldown_until = now + CAMERA_COOLDOWN_SECONDS
                                    if last_bbox:
                                        saved = _save_face_capture(frame, last_bbox, best_pid, mode, sharp_buffer=sharp_buf)
                                        if saved:
                                            print(f"[Camera] Saved: {saved}")
                                        sharp_buf.clear()
                                elif action == "ALREADY_CHECKED_IN":
                                    name = "Already checked in today"; sub = name; tag_color = COL_YELLOW; show_tag = True
                                    cooldown_until = now + CAMERA_COOLDOWN_SECONDS
                                elif action == "ALREADY_CHECKED_OUT":
                                    name = "Already checked out today"; sub = name; tag_color = COL_YELLOW; show_tag = True
                                    cooldown_until = now + CAMERA_COOLDOWN_SECONDS
                                elif action == "NOT_CHECKED_IN":
                                    name = "Chua check-in"; sub = "Hay Check-In (phim 1) truoc."; tag_color = COL_RED
                                    cooldown_until = now + CAMERA_COOLDOWN_SECONDS
                                else:
                                    name = action.replace("_", " ").title()
                                    sub = result.get("message", "")[:50]; tag_color = COL_RED
                                    cooldown_until = now + CAMERA_COOLDOWN_SECONDS
                    else:
                        sim_val = top[0]["similarity"] if top else 0
                        name = "Unknown"; sub = f"sim {sim_val:.3f}"; tag_color = COL_YELLOW
                        cooldown_until = now + 3.0
                else:
                    name = "No face by verifier"; sub = ""; tag_color = COL_YELLOW

        # ── Draw UI ──────────────────────────────────────────────
        _draw_topbar(frame, mode, False, fps_meter, h, w)

        if last_bbox and spoof_status != "NO_FACE":
            x1, y1, x2, y2 = last_bbox
            col = COL_GREEN if spoof_status == "REAL_ATTENDANCE_OK" else (COL_RED if spoof_status == "FAKE_OR_SUSPECT" else (100, 100, 100))
            _draw_corner_marks(frame, x1, y1, x2, y2, color=col)
            if show_tag:
                _draw_name_tag(frame, name, sub, x1, y2, x2, color=tag_color)
            if spoof_status == "CHECKING":
                buf = spoof.get_buffer_stats()
                txt = f"Checking {buf.get('buffer_len',0)}/{buf.get('window_size',0)}"
                _draw_status_label(frame, txt, x1, y1, COL_GRAY)
            elif spoof_status == "FAKE_OR_SUSPECT":
                _draw_status_label(frame, "Spoof!", x1, y1, COL_RED)
        elif spoof_status == "NO_FACE":
            _draw_status_overlay_thin(frame, "No face detected", COL_GRAY)

        _draw_bottombar(frame, h, w)
        cv2.imshow("Face Attendance", frame)

        elapsed = time.time() - t_start
        fps_meter = fps_meter * (1 - fps_alpha) + (1.0 / elapsed) * fps_alpha if elapsed > 0 else 0

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):
            break
        elif key == ord('1'):
            mode = "checkin"; spoof.reset_buffer(); sharp_buf.clear(); cooldown_until = 0
        elif key == ord('2'):
            mode = "checkout"; spoof.reset_buffer(); sharp_buf.clear(); cooldown_until = 0

    cap.release()
    cv2.destroyAllWindows()
    print("[Camera] Closed.")


# ────────────────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────────────────

def run(mode: str, cam_idx: int, multi: bool = True):
    if multi:
        _run_multi(mode, cam_idx)
    else:
        _run_single(mode, cam_idx)


if __name__ == "__main__":
    args = _parse_args()
    mode, cam_idx = _select_interactively(args.mode, args.camera)
    run(mode, cam_idx, multi=not args.single)
