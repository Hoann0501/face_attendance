import os
import csv
import json
import pickle
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

from insightface.app import FaceAnalysis


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(r"C:\Users\Hoannd\Downloads\data_face")

VERIFY_DIR = BASE_DIR / "face_verification_poc"
ENROLL_DIR = VERIFY_DIR / "enroll"
PEOPLE_CSV_PATH = VERIFY_DIR / "people.csv"
TEMPLATES_PATH = VERIFY_DIR / "person_templates.pkl"

ATTENDANCE_DIR = BASE_DIR / "attendance_logs"

VERIFY_DIR.mkdir(parents=True, exist_ok=True)
ENROLL_DIR.mkdir(parents=True, exist_ok=True)
ATTENDANCE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_VERIFY_THRESHOLD = 0.35


# ============================================================
# STREAMLIT CONFIG
# ============================================================

st.set_page_config(
    page_title="Face Attendance POC",
    page_icon="🧑‍💻",
    layout="wide"
)

st.title("Face Recognition Attendance POC")
st.caption("Quản lý khuôn mặt | Tìm kiếm | Xác minh | Phân tích ảnh khuôn mặt")


# ============================================================
# LOAD INSIGHTFACE
# ============================================================

@st.cache_resource
def load_face_app():
    app = FaceAnalysis(
        name="buffalo_l",
        providers=["CPUExecutionProvider"]
    )
    app.prepare(ctx_id=0, det_size=(640, 640))
    return app


face_app = load_face_app()


# ============================================================
# HELPERS
# ============================================================

def ensure_people_csv():
    if PEOPLE_CSV_PATH.exists():
        return

    with open(PEOPLE_CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "person_id",
            "full_name",
            "student_code",
            "class_name",
            "status"
        ])


def load_people_df():
    ensure_people_csv()
    return pd.read_csv(PEOPLE_CSV_PATH, encoding="utf-8-sig")


def save_people_df(df):
    df.to_csv(PEOPLE_CSV_PATH, index=False, encoding="utf-8-sig")


def load_templates():
    if not TEMPLATES_PATH.exists():
        return {}

    with open(TEMPLATES_PATH, "rb") as f:
        return pickle.load(f)


def save_templates(templates):
    with open(TEMPLATES_PATH, "wb") as f:
        pickle.dump(templates, f)


def get_largest_face(faces):
    if len(faces) == 0:
        return None

    def area(face):
        x1, y1, x2, y2 = face.bbox
        return max(0, x2 - x1) * max(0, y2 - y1)

    return max(faces, key=area)


def pil_to_bgr(pil_img):
    rgb = np.array(pil_img.convert("RGB"))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return bgr


def extract_embedding_from_pil(pil_img):
    bgr = pil_to_bgr(pil_img)
    faces = face_app.get(bgr)
    face = get_largest_face(faces)

    if face is None:
        return None, {
            "ok": False,
            "reason": "no_face",
            "faces": faces
        }

    emb = face.embedding.astype(np.float32)
    emb = emb / np.linalg.norm(emb)

    return emb, {
        "ok": True,
        "reason": "ok",
        "face": face,
        "faces": faces
    }


def draw_faces_on_image(pil_img):
    bgr = pil_to_bgr(pil_img)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    faces = face_app.get(bgr)

    for i, face in enumerate(faces, 1):
        x1, y1, x2, y2 = face.bbox.astype(int)
        cv2.rectangle(rgb, (x1, y1), (x2, y2), (0, 255, 0), 3)

        text = f"face_{i} score={face.det_score:.2f}"
        cv2.putText(
            rgb,
            text,
            (x1, max(20, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
            cv2.LINE_AA
        )

    return Image.fromarray(rgb), faces


def upsert_person(person_id, full_name, student_code, class_name, status="active"):
    df = load_people_df()

    person_id = person_id.strip()

    if person_id in df["person_id"].astype(str).values:
        df.loc[df["person_id"].astype(str) == person_id, "full_name"] = full_name
        df.loc[df["person_id"].astype(str) == person_id, "student_code"] = student_code
        df.loc[df["person_id"].astype(str) == person_id, "class_name"] = class_name
        df.loc[df["person_id"].astype(str) == person_id, "status"] = status
    else:
        new_row = {
            "person_id": person_id,
            "full_name": full_name,
            "student_code": student_code,
            "class_name": class_name,
            "status": status
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    save_people_df(df)


def delete_person(person_id):
    df = load_people_df()
    df = df[df["person_id"].astype(str) != person_id].copy()
    save_people_df(df)

    templates = load_templates()
    if person_id in templates:
        del templates[person_id]
        save_templates(templates)


def search_face(emb, templates, top_k=5):
    rows = []

    for person_id, template in templates.items():
        template = template.astype(np.float32)
        template = template / np.linalg.norm(template)

        sim = float(np.dot(emb, template))

        rows.append({
            "person_id": person_id,
            "similarity": sim
        })

    df = pd.DataFrame(rows)

    if len(df) == 0:
        return df

    return df.sort_values("similarity", ascending=False).head(top_k)


def merge_people_info(search_df):
    people_df = load_people_df()

    if len(search_df) == 0:
        return search_df

    merged = search_df.merge(
        people_df,
        on="person_id",
        how="left"
    )

    return merged


def get_next_person_id():
    df = load_people_df()

    existing = df["person_id"].astype(str).tolist()

    max_num = 0
    for pid in existing:
        if pid.startswith("person_"):
            try:
                num = int(pid.split("_")[1])
                max_num = max(max_num, num)
            except Exception:
                pass

    return f"person_{max_num + 1:03d}"


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("Project Paths")
st.sidebar.write("BASE_DIR")
st.sidebar.code(str(BASE_DIR))
st.sidebar.write("people.csv")
st.sidebar.code(str(PEOPLE_CSV_PATH))
st.sidebar.write("person_templates.pkl")
st.sidebar.code(str(TEMPLATES_PATH))

templates = load_templates()
people_df = load_people_df()

st.sidebar.metric("Registered people", len(people_df))
st.sidebar.metric("Templates", len(templates))


# ============================================================
# TABS
# ============================================================

tab_dashboard, tab_people, tab_register, tab_search, tab_analysis = st.tabs([
    "Dashboard",
    "Quản lý CSDL khuôn mặt",
    "Đăng ký người mới",
    "Tìm kiếm / Xác minh",
    "Phân tích ảnh khuôn mặt"
])


# ============================================================
# TAB 1: DASHBOARD
# ============================================================

with tab_dashboard:
    st.subheader("Tổng quan POC")

    col1, col2, col3 = st.columns(3)

    col1.metric("Người trong people.csv", len(people_df))
    col2.metric("Templates khuôn mặt", len(templates))

    today = datetime.now().strftime("%Y-%m-%d")
    today_log = ATTENDANCE_DIR / f"attendance_{today}.csv"

    if today_log.exists():
        today_df = pd.read_csv(today_log, encoding="utf-8-sig")
        attended_count = len(today_df)
    else:
        today_df = pd.DataFrame()
        attended_count = 0

    col3.metric("Đã điểm danh hôm nay", attended_count)

    st.markdown("### Trạng thái module theo yêu cầu gốc")

    status_df = pd.DataFrame([
        {
            "module": "Quản lý cơ sở dữ liệu khuôn mặt",
            "status": "Đang hoàn thiện",
            "evidence": "people.csv, templates.pkl, UI quản lý"
        },
        {
            "module": "Phân tích hình ảnh khuôn mặt",
            "status": "POC",
            "evidence": "detect face, bbox, score, age/gender nếu model trả"
        },
        {
            "module": "Tìm kiếm khuôn mặt",
            "status": "POC",
            "evidence": "query image → top-k person similarity"
        },
        {
            "module": "Kiểm tra chống giả mạo sinh trắc học",
            "status": "POC đạt",
            "evidence": "MobileNetV3 anti-spoofing + webcam fast liveness"
        },
        {
            "module": "Xác minh khuôn mặt",
            "status": "POC đạt",
            "evidence": "InsightFace embedding + cosine threshold"
        },
    ])

    st.dataframe(status_df, use_container_width=True)

    st.markdown("### Điểm danh hôm nay")

    if len(today_df) > 0:
        st.dataframe(today_df, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu điểm danh hôm nay.")


# ============================================================
# TAB 2: PEOPLE MANAGEMENT
# ============================================================

with tab_people:
    st.subheader("Quản lý cơ sở dữ liệu khuôn mặt")

    people_df = load_people_df()
    templates = load_templates()

    st.markdown("### Danh sách người đăng ký")

    show_df = people_df.copy()
    show_df["has_template"] = show_df["person_id"].astype(str).apply(
        lambda x: x in templates
    )

    st.dataframe(show_df, use_container_width=True)

    st.markdown("### Thêm / cập nhật thông tin người")

    with st.form("upsert_person_form"):
        default_pid = get_next_person_id()

        person_id = st.text_input("person_id", value=default_pid)
        full_name = st.text_input("Họ tên")
        student_code = st.text_input("Mã sinh viên / mã nhân viên")
        class_name = st.text_input("Lớp / phòng ban")
        status = st.selectbox("Trạng thái", ["active", "inactive"])

        submitted = st.form_submit_button("Lưu thông tin")

        if submitted:
            if not person_id.strip():
                st.error("person_id không được rỗng.")
            else:
                upsert_person(
                    person_id=person_id,
                    full_name=full_name,
                    student_code=student_code,
                    class_name=class_name,
                    status=status
                )
                st.success(f"Đã lưu {person_id}.")
                st.rerun()

    st.markdown("### Khóa / mở khóa / xóa người")

    people_df = load_people_df()

    if len(people_df) > 0:
        selected_person = st.selectbox(
            "Chọn person_id",
            people_df["person_id"].astype(str).tolist()
        )

        col_a, col_b, col_c = st.columns(3)

        with col_a:
            if st.button("Set active"):
                df = load_people_df()
                df.loc[df["person_id"].astype(str) == selected_person, "status"] = "active"
                save_people_df(df)
                st.success(f"Đã active {selected_person}.")
                st.rerun()

        with col_b:
            if st.button("Set inactive"):
                df = load_people_df()
                df.loc[df["person_id"].astype(str) == selected_person, "status"] = "inactive"
                save_people_df(df)
                st.success(f"Đã inactive {selected_person}.")
                st.rerun()

        with col_c:
            confirm_delete = st.checkbox("Xác nhận xóa", key="confirm_delete")

            if st.button("Xóa người") and confirm_delete:
                delete_person(selected_person)
                st.success(f"Đã xóa {selected_person} khỏi people.csv và templates.")
                st.rerun()
    else:
        st.info("Chưa có người đăng ký.")


# ============================================================
# TAB 3: REGISTER NEW PERSON
# ============================================================

with tab_register:
    st.subheader("Đăng ký người mới bằng ảnh upload")

    st.info(
        "Upload 2-5 ảnh rõ mặt của cùng một người. "
        "UI sẽ tạo embedding template và cập nhật people.csv."
    )

    with st.form("register_form"):
        default_pid = get_next_person_id()

        person_id = st.text_input("person_id", value=default_pid, key="reg_person_id")
        full_name = st.text_input("Họ tên", key="reg_full_name")
        student_code = st.text_input("Mã sinh viên / mã nhân viên", key="reg_student_code")
        class_name = st.text_input("Lớp / phòng ban", key="reg_class_name")

        uploaded_files = st.file_uploader(
            "Upload ảnh enroll",
            type=["jpg", "jpeg", "png", "bmp", "webp"],
            accept_multiple_files=True
        )

        submitted = st.form_submit_button("Đăng ký người này")

    if submitted:
        if not person_id.strip():
            st.error("person_id không được rỗng.")
        elif not uploaded_files:
            st.error("Cần upload ít nhất 1 ảnh.")
        else:
            person_dir = ENROLL_DIR / person_id
            person_dir.mkdir(parents=True, exist_ok=True)

            embeddings = []
            saved_paths = []

            for idx, file in enumerate(uploaded_files, 1):
                pil_img = Image.open(file).convert("RGB")

                emb, info = extract_embedding_from_pil(pil_img)

                if not info["ok"]:
                    st.warning(f"Ảnh {file.name}: không detect được mặt, bỏ qua.")
                    continue

                save_path = person_dir / f"enroll_{idx:03d}.jpg"
                pil_img.save(save_path)

                embeddings.append(emb)
                saved_paths.append(str(save_path))

            if len(embeddings) == 0:
                st.error("Không tạo được embedding nào. Hãy upload ảnh mặt rõ hơn.")
            else:
                embs = np.stack(embeddings)
                template = embs.mean(axis=0)
                template = template / np.linalg.norm(template)

                templates = load_templates()
                templates[person_id] = template
                save_templates(templates)

                upsert_person(
                    person_id=person_id,
                    full_name=full_name,
                    student_code=student_code,
                    class_name=class_name,
                    status="active"
                )

                st.success(f"Đã đăng ký {person_id} với {len(embeddings)} ảnh.")
                st.write("Ảnh đã lưu:")
                for p in saved_paths:
                    st.code(p)


# ============================================================
# TAB 4: FACE SEARCH / VERIFY
# ============================================================

with tab_search:
    st.subheader("Tìm kiếm / Xác minh khuôn mặt")

    templates = load_templates()

    if len(templates) == 0:
        st.warning("Chưa có templates. Hãy đăng ký người trước.")
    else:
        col_left, col_right = st.columns([1, 1])

        with col_left:
            query_file = st.file_uploader(
                "Upload ảnh query",
                type=["jpg", "jpeg", "png", "bmp", "webp"],
                key="search_query_file"
            )

            verify_threshold = st.slider(
                "Verification threshold",
                min_value=0.0,
                max_value=1.0,
                value=DEFAULT_VERIFY_THRESHOLD,
                step=0.01
            )

            top_k = st.slider("Top K", min_value=1, max_value=10, value=5, step=1)

        if query_file is not None:
            pil_img = Image.open(query_file).convert("RGB")

            with col_left:
                st.image(pil_img, caption="Query image", use_container_width=True)

            emb, info = extract_embedding_from_pil(pil_img)

            if not info["ok"]:
                st.error("Không detect được mặt trong ảnh query.")
            else:
                search_df = search_face(emb, templates, top_k=top_k)
                result_df = merge_people_info(search_df)

                result_df["is_match"] = result_df["similarity"] >= verify_threshold

                with col_right:
                    st.markdown("### Kết quả top-k")
                    st.dataframe(result_df, use_container_width=True)

                    best = result_df.iloc[0]

                    if best["similarity"] >= verify_threshold:
                        st.success(
                            f"MATCH: {best.get('full_name', best['person_id'])} "
                            f"| {best['person_id']} | sim={best['similarity']:.4f}"
                        )
                    else:
                        st.warning(
                            f"UNKNOWN / NOT MATCH. Best={best['person_id']} "
                            f"sim={best['similarity']:.4f}"
                        )


# ============================================================
# TAB 5: FACE IMAGE ANALYSIS
# ============================================================

with tab_analysis:
    st.subheader("Phân tích hình ảnh khuôn mặt")

    analysis_file = st.file_uploader(
        "Upload ảnh để phân tích",
        type=["jpg", "jpeg", "png", "bmp", "webp"],
        key="analysis_file"
    )

    if analysis_file is not None:
        pil_img = Image.open(analysis_file).convert("RGB")

        annotated_img, faces = draw_faces_on_image(pil_img)

        col_img, col_data = st.columns([1, 1])

        with col_img:
            st.image(annotated_img, caption="Detected faces", use_container_width=True)

        rows = []

        for i, face in enumerate(faces, 1):
            row = {
                "face_id": i,
                "det_score": float(face.det_score),
                "bbox_x1": float(face.bbox[0]),
                "bbox_y1": float(face.bbox[1]),
                "bbox_x2": float(face.bbox[2]),
                "bbox_y2": float(face.bbox[3]),
            }

            # InsightFace buffalo_l thường có age/gender nếu model hỗ trợ.
            if hasattr(face, "age"):
                row["age"] = int(face.age)

            if hasattr(face, "gender"):
                # convention thường gặp: 0 female, 1 male
                row["gender_raw"] = int(face.gender)
                row["gender_label"] = "male" if int(face.gender) == 1 else "female"

            rows.append(row)

        analysis_df = pd.DataFrame(rows)

        with col_data:
            st.markdown("### Kết quả phân tích")
            if len(analysis_df) > 0:
                st.dataframe(analysis_df, use_container_width=True)

                st.markdown("### JSON")
                st.json(analysis_df.to_dict(orient="records"))
            else:
                st.warning("Không detect được khuôn mặt.")