"""
Attendance Camera App

Usage:
    python camera_app/attendance_camera.py [--mode checkin|checkout] [--camera N]

Keyboard shortcuts (OpenCV window):
    1  –  Check-In mode
    2  –  Check-Out mode
    Q  –  Quit
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
    CAMERA_INDEX,
    CAMERA_COOLDOWN_SECONDS,
)
from core.antispoof import AntiSpoofService
from core.face_verifier import FaceVerifier
from backend.config import FACE_CAPTURES_DIR


# ────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────

FONT        = cv2.FONT_HERSHEY_SIMPLEX
COL_WHITE   = (255, 255, 255)
COL_GREEN   = (50,  220,  80)
COL_RED     = (60,   60, 220)   # BGR → red
COL_YELLOW  = (30,  200, 220)
COL_BLUE    = (220, 150,  60)
COL_DARK    = (18,   18,  18)
COL_GRAY    = (120, 120, 120)

MODE_LABELS = { 'checkin': 'CHECK-IN', 'checkout': 'CHECK-OUT' }
MODE_COLORS = { 'checkin': COL_GREEN, 'checkout': COL_BLUE }


# ────────────────────────────────────────────────────────────
# Sharp-frame buffer  — pick the clearest frame to capture
# ────────────────────────────────────────────────────────────

class SharpFrameBuffer:
    """
    Rolling buffer of recent frames.
    Scores each frame by Laplacian variance on the face crop
    (higher = sharper).  When saving, returns the sharpest frame
    seen in the last `maxlen` frames instead of the current one.
    """

    def __init__(self, maxlen: int = 20):
        self.maxlen = maxlen
        self._buf: list[tuple[np.ndarray, tuple, float]] = []  # (frame, bbox, score)

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
        """Return (frame, bbox, score) of the sharpest buffered frame."""
        if not self._buf:
            return None, None, 0.0
        best = max(self._buf, key=lambda x: x[2])
        return best[0], best[1], best[2]

    def clear(self) -> None:
        self._buf.clear()

    def __len__(self) -> int:
        return len(self._buf)


# ────────────────────────────────────────────────────────────
# Face capture save
# ────────────────────────────────────────────────────────────

def _crop_face(frame_bgr: np.ndarray, bbox: tuple, margin: float = 0.45) -> np.ndarray | None:
    """Crop face with margin.  Returns BGR crop or None."""
    h, w = frame_bgr.shape[:2]
    x1, y1, x2, y2 = bbox
    bw, bh = x2 - x1, y2 - y1
    mx, my = int(bw * margin), int(bh * margin)
    cx1, cy1 = max(0, x1 - mx), max(0, y1 - my)
    cx2, cy2 = min(w, x2 + mx), min(h, y2 + my)
    crop = frame_bgr[cy1:cy2, cx1:cx2]
    return crop if crop.size > 0 else None


def _save_face_capture(
    frame_bgr: np.ndarray,
    bbox: tuple,
    person_id: str,
    mode: str,
    sharp_buffer: SharpFrameBuffer | None = None,
) -> str | None:
    """
    Save the sharpest available face crop to:
      data/face_captures/{YYYY-MM-DD}/{checkin|checkout}/{person_id}_{YYYY-MM-DD}_{HH-MM-SS}_{mode}.jpg

    If sharp_buffer is provided, uses the sharpest frame from the buffer;
    otherwise falls back to the current frame.
    """
    try:
        # Pick the sharpest frame
        if sharp_buffer and len(sharp_buffer) > 0:
            best_frame, best_bbox, score = sharp_buffer.get_sharpest()
            use_frame = best_frame if best_frame is not None else frame_bgr
            use_bbox  = best_bbox  if best_bbox  is not None else bbox
            print(f"[Camera] Capture: sharpest frame score={score:.1f} (buffer={len(sharp_buffer)} frames)")
        else:
            use_frame = frame_bgr
            use_bbox  = bbox

        crop = _crop_face(use_frame, use_bbox, margin=0.45)
        if crop is None:
            return None

        # Optional: mild unsharp mask to further enhance edges
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


def _unsharp(img: np.ndarray, strength: float = 0.4, blur_sigma: float = 1.0) -> np.ndarray:
    """Mild unsharp mask to recover edge detail lost during camera motion."""
    blurred = cv2.GaussianBlur(img, (0, 0), blur_sigma)
    sharp   = cv2.addWeighted(img, 1.0 + strength, blurred, -strength, 0)
    return sharp


# ────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────

def _parse_args():
    p = argparse.ArgumentParser(description="Attendance Camera")
    p.add_argument("--mode",   choices=["checkin", "checkout"], default=None)
    p.add_argument("--camera", type=int, default=None)
    return p.parse_args()


# ────────────────────────────────────────────────────────────
# Startup selection (terminal)
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
    """Return (mode, camera_index) after prompting the user if needed."""

    # ── Mode ──────────────────────────────────────────────────
    mode = mode_arg
    if mode is None:
        print()
        print("  ATTENDANCE CAMERA")
        print("  " + "─" * 30)
        print("  [1]  Check-In")
        print("  [2]  Check-Out")
        print()
        while mode is None:
            try:
                c = input("  Select mode [1/2]: ").strip()
            except (EOFError, KeyboardInterrupt):
                sys.exit(0)
            if c == "1":
                mode = "checkin"
            elif c == "2":
                mode = "checkout"
            else:
                print("  Enter 1 or 2.")

    # ── Camera ────────────────────────────────────────────────
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
            while cam_idx is None:
                try:
                    raw = input(f"  Select camera [{default}]: ").strip()
                    cam_idx = int(raw) if raw else default
                    if cam_idx not in available:
                        print(f"  Invalid index, choose from {available}.")
                        cam_idx = None
                except (ValueError, EOFError, KeyboardInterrupt):
                    cam_idx = default

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
    """
    Client-side guard: checkout requires today's row with check-in and no check-out yet.
    Returns (allowed, reason_vi when not allowed). On HTTP errors, allows and lets API decide.
    """
    try:
        r = requests.get(f"{BACKEND_URL}/attendance/today", timeout=3)
        if r.status_code != 200:
            return True, ""
        records = r.json().get("records") or []
        pid = str(person_id).strip()
        for rec in records:
            if str(rec.get("person_id", "")).strip() != pid:
                continue
            cin = str(rec.get("check_in_time") or "").strip()
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
# Drawing helpers  (clean, production style)
# ────────────────────────────────────────────────────────────

def _text_box(
    frame: np.ndarray,
    text: str,
    origin: tuple[int, int],
    font_scale: float = 0.55,
    color=COL_WHITE,
    bg=COL_DARK,
    pad: int = 6,
    thickness: int = 1,
):
    (tw, th), base = cv2.getTextSize(text, FONT, font_scale, thickness)
    x, y = origin
    cv2.rectangle(frame, (x - pad, y - th - pad), (x + tw + pad, y + base + pad // 2), bg, -1)
    cv2.putText(frame, text, (x, y), FONT, font_scale, color, thickness, cv2.LINE_AA)


def _draw_bbox(frame: np.ndarray, x1, y1, x2, y2, color=COL_GREEN, thickness: int = 2):
    """Draw thin clean rectangle around face."""
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)


def _draw_corner_marks(frame: np.ndarray, x1, y1, x2, y2, color=COL_GREEN, length: int = 14):
    """Draw corner tick marks for a cleaner look than a full rectangle."""
    t = 2
    for (cx, cy, dx, dy) in [
        (x1, y1,  1,  1),
        (x2, y1, -1,  1),
        (x1, y2,  1, -1),
        (x2, y2, -1, -1),
    ]:
        cv2.line(frame, (cx, cy), (cx + dx * length, cy), color, t)
        cv2.line(frame, (cx, cy), (cx, cy + dy * length), color, t)


def _draw_name_tag(frame: np.ndarray, name: str, sub: str, x1: int, y2: int, x2: int, color=COL_GREEN):
    """Draw name + sub-label below the face bbox."""
    h, w = frame.shape[:2]
    pad = 8
    fs_name = 0.60
    fs_sub  = 0.42

    (nw, nh), _ = cv2.getTextSize(name, FONT, fs_name, 1)
    (sw, _),  _ = cv2.getTextSize(sub,  FONT, fs_sub,  1)
    box_w = max(nw, sw) + pad * 2
    box_h = nh + (16 if sub else 0) + pad * 2

    bx = max(0, min(x1, w - box_w))
    by = min(y2 + 4, h - box_h)

    overlay = frame.copy()
    cv2.rectangle(overlay, (bx, by), (bx + box_w, by + box_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    cv2.putText(frame, name, (bx + pad, by + pad + nh), FONT, fs_name, color, 1, cv2.LINE_AA)
    if sub:
        cv2.putText(frame, sub, (bx + pad, by + pad + nh + 14), FONT, fs_sub, COL_GRAY, 1, cv2.LINE_AA)


def _draw_topbar(frame: np.ndarray, mode: str, h: int, w: int):
    """Top bar: mode label."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 32), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    col   = MODE_COLORS.get(mode, COL_WHITE)
    label = MODE_LABELS.get(mode, mode.upper())
    cv2.putText(frame, label, (12, 22), FONT, 0.55, col, 1, cv2.LINE_AA)

    ts = time.strftime("%H:%M:%S")
    (tw, _), _ = cv2.getTextSize(ts, FONT, 0.45, 1)
    cv2.putText(frame, ts, (w - tw - 12, 22), FONT, 0.45, COL_GRAY, 1, cv2.LINE_AA)


def _draw_bottombar(frame: np.ndarray, h: int, w: int):
    """Bottom bar: keyboard shortcuts."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - 26), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    hint = "1: Check-In    2: Check-Out    Q: Quit"
    cv2.putText(frame, hint, (12, h - 9), FONT, 0.38, COL_GRAY, 1, cv2.LINE_AA)


def _draw_status_overlay(frame: np.ndarray, line1: str, col1, line2: str = "", col2=None, h: int = 0):
    """Central status text shown while no name_tag is needed (CHECKING, FAKE, etc.)."""
    if col2 is None:
        col2 = COL_GRAY
    _text_box(frame, line1, (12, 60), font_scale=0.62, color=col1)
    if line2:
        _text_box(frame, line2, (12, 86), font_scale=0.46, color=col2)


# ────────────────────────────────────────────────────────────
# Identity result state
# ────────────────────────────────────────────────────────────

class _IdentState:
    def __init__(self):
        self.line1      : str   = ""
        self.col1               = COL_WHITE
        self.line2      : str   = ""
        self.name       : str   = ""
        self.sub        : str   = ""
        self.tag_color          = COL_WHITE
        self.show_tag   : bool  = False
        self.cooldown_until: float = 0.0

    def in_cooldown(self): return time.time() < self.cooldown_until
    def set_cooldown(self): self.cooldown_until = time.time() + CAMERA_COOLDOWN_SECONDS

    def set(self, line1, col1=COL_WHITE, line2="", col2=COL_GRAY, name="", sub="", tag_color=COL_WHITE, show_tag=False):
        self.line1 = line1; self.col1 = col1
        self.line2 = line2
        self.name  = name;  self.sub = sub
        self.tag_color = tag_color
        self.show_tag  = show_tag


# ────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────

def run(mode: str, cam_idx: int):
    print(f"[Camera] Loading anti-spoof model...")
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

    print(f"[Camera] Loading face verifier...")
    try:
        verifier = FaceVerifier(templates_path=TEMPLATES_PATH, verify_threshold=VERIFY_THRESHOLD)
    except Exception as e:
        print(f"[Camera] ERROR loading face verifier: {e}"); sys.exit(1)

    print(f"[Camera] Opening camera {cam_idx}...")
    cap = cv2.VideoCapture(cam_idx)
    if not cap.isOpened():
        print(f"[Camera] Cannot open camera {cam_idx}."); sys.exit(1)

    # Prefer 1280x720 for a cleaner image
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    haar = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    print("[Camera] Ready.")

    state        = _IdentState()
    spoof_status = "WAITING"
    last_bbox: tuple | None = None
    sharp_buf    = SharpFrameBuffer(maxlen=20)  # accumulate recent clear frames

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[Camera] Cannot read frame."); break

        frame = cv2.flip(frame, 1)
        h, w  = frame.shape[:2]

        # ── Anti-spoof face crop ──────────────────────────────
        face_crop_rgb, bbox = AntiSpoofService.get_haar_face_crop(frame, haar, margin=0.35)

        if face_crop_rgb is not None:
            last_bbox    = bbox
            frame_rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            spoof_status = spoof.update(face_crop_rgb, frame_rgb)

            # Accumulate frames during CHECKING + REAL for best-frame selection
            if spoof_status in ("CHECKING", "REAL_ATTENDANCE_OK"):
                sharp_buf.push(frame, bbox)
        else:
            spoof.reset_buffer()
            spoof_status = "NO_FACE"
            last_bbox    = None

        # Clear name tag + discard spoofed frames
        if spoof_status in ("FAKE_OR_SUSPECT", "NO_FACE"):
            state.show_tag = False
            if spoof_status == "FAKE_OR_SUSPECT":
                sharp_buf.clear()

        # ── Identity + attendance ─────────────────────────────
        if spoof_status == "REAL_ATTENDANCE_OK" and not state.in_cooldown():
            from PIL import Image as _PILImage
            pil_frame = _PILImage.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            emb, info = verifier.extract_embedding_pil(pil_frame)

            if not info["ok"] or emb is None:
                state.set("No face detected by verifier", COL_YELLOW)
            else:
                top = verifier.search_top_k(emb, top_k=1)
                if not top or top[0]["similarity"] < VERIFY_THRESHOLD:
                    sim_val = top[0]["similarity"] if top else 0
                    state.set("Unknown person", COL_YELLOW,
                              f"Best similarity: {sim_val:.3f}  (threshold {VERIFY_THRESHOLD})")
                    state.set_cooldown()
                else:
                    best_pid = top[0]["person_id"]
                    best_sim = top[0]["similarity"]
                    person   = _api_get_person(best_pid)

                    if person and person.get("status") == "inactive":
                        state.set("Inactive user", COL_YELLOW,
                                  person.get("full_name", best_pid))
                        state.set_cooldown()
                    else:
                        name = person.get("full_name", best_pid) if person else best_pid
                        code = person.get("student_code", "") if person else ""
                        proceed = True
                        if mode == "checkout":
                            ok_co, why = _precheck_can_check_out(best_pid)
                            if not ok_co:
                                state.set("Check-out bi chan", COL_RED, why)
                                state.set_cooldown()
                                proceed = False
                        if proceed:
                            result = _api_checkin_or_out(
                                best_pid, mode, best_sim, spoof_status,
                                spoof.last_face_real, spoof.last_full_real,
                            )
                            action = result.get("action", "")
                            if result.get("ok") and action in ("CHECKED_IN", "CHECKED_OUT"):
                                label = "Check-In OK" if action == "CHECKED_IN" else "Check-Out OK"
                                state.set(label, COL_GREEN, f"{name}  |  {code}",
                                          name=name, sub=f"sim {best_sim:.3f}", tag_color=COL_GREEN, show_tag=True)
                                # Save the sharpest buffered frame instead of current frame
                                if last_bbox:
                                    saved = _save_face_capture(
                                        frame, last_bbox, best_pid, mode,
                                        sharp_buffer=sharp_buf,
                                    )
                                    if saved:
                                        print(f"[Camera] Saved capture: {saved}")
                                    sharp_buf.clear()  # reset for next person
                            elif action == "ALREADY_CHECKED_IN":
                                state.set("Already checked in today", COL_YELLOW,
                                          name, name=name, sub=code, tag_color=COL_YELLOW, show_tag=True)
                            elif action == "ALREADY_CHECKED_OUT":
                                state.set("Already checked out today", COL_YELLOW,
                                          name, name=name, sub=code, tag_color=COL_YELLOW, show_tag=True)
                            elif action == "NOT_CHECKED_IN":
                                state.set("Chua check-in — khong the check-out", COL_RED,
                                          result.get("message", "")[:80] or "Hay Check-In (phim 1) truoc.")
                            else:
                                state.set(action.replace("_", " ").title(), COL_RED,
                                          result.get("message", "")[:50])
                            state.set_cooldown()

        # ── Draw UI ───────────────────────────────────────────
        _draw_topbar(frame, mode, h, w)

        if last_bbox and spoof_status != "NO_FACE":
            x1, y1, x2, y2 = last_bbox

            if spoof_status == "REAL_ATTENDANCE_OK":
                bbox_col = COL_GREEN
            elif spoof_status == "FAKE_OR_SUSPECT":
                bbox_col = COL_RED
            else:
                bbox_col = (100, 100, 100)  # gray while CHECKING

            _draw_corner_marks(frame, x1, y1, x2, y2, color=bbox_col)
            _draw_bbox(frame, x1, y1, x2, y2, color=bbox_col, thickness=1)

            # Name tag – only when verified and face is real (not fake)
            if state.show_tag and spoof_status != "FAKE_OR_SUSPECT":
                _draw_name_tag(frame, state.name, state.sub, x1, y2, x2, color=state.tag_color)

            # Status line (liveness + result)
            if spoof_status == "CHECKING":
                buf = spoof.get_buffer_stats()
                votes = buf.get("real_votes", 0)
                total = buf.get("window_size", WINDOW_SIZE)
                _draw_status_overlay(frame, "Checking...", COL_GRAY, f"Frames: {buf.get('buffer_len',0)}/{total}  Votes: {votes}")
            elif spoof_status == "FAKE_OR_SUSPECT":
                _draw_status_overlay(frame, "Liveness check failed", COL_RED, "Face may be spoofed")
            elif state.line1:
                _draw_status_overlay(frame, state.line1, state.col1, state.line2)

        elif spoof_status == "NO_FACE":
            _draw_status_overlay(frame, "No face detected", COL_GRAY)

        _draw_bottombar(frame, h, w)

        cv2.imshow("Face Attendance", frame)

        key = cv2.waitKey(1) & 0xFF
        if   key in (ord('q'), ord('Q'), 27):
            break
        elif key == ord('1'):
            mode = "checkin";  spoof.reset_buffer(); state.set("Mode: Check-In",  COL_GREEN)
        elif key == ord('2'):
            mode = "checkout"; spoof.reset_buffer(); state.set("Mode: Check-Out", COL_BLUE)

    cap.release()
    cv2.destroyAllWindows()
    print("[Camera] Closed.")


if __name__ == "__main__":
    args   = _parse_args()
    mode, cam_idx = _select_interactively(args.mode, args.camera)
    run(mode, cam_idx)
