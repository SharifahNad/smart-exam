import streamlit as st
import base64
from pathlib import Path

from firebase_service import db

LECTURER_CODE = "LECTURER2026"

def get_logo_base64(path="assets/logo.png"):
    """Baca fail logo dan tukar ke base64 supaya boleh embed terus dalam HTML."""
    logo_file = Path(path)
    if logo_file.exists():
        data = base64.b64encode(logo_file.read_bytes()).decode()
        return f"data:image/png;base64,{data}"
    return None

# --- Firebase ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
firebase_file = os.path.join(BASE_DIR, "firebase_config.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_file)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def get_logo_base64(path="assets/logo.png"):
    """Baca fail logo dan tukar ke base64 supaya boleh embed terus dalam HTML."""
    logo_file = Path(path)
    if logo_file.exists():
        data = base64.b64encode(logo_file.read_bytes()).decode()
        return f"data:image/png;base64,{data}"
    return None

def login_page():

    st.markdown("""
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Orbitron:wght@700;800;900&display=swap');

    [data-testid="stSidebar"] { display: none; }
    header[data-testid="stHeader"] { background: transparent; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    .stApp {
        background: linear-gradient(160deg, #faf8f3 0%, #efe8d8 100%);
        font-family: 'Poppins', sans-serif;
    }

    .block-container {
        max-width: 620px;
        padding-top: 30px;
    }

    /* ===== HEKSAGON LOGO ===== */
    .logo-wrap { text-align: center; margin-bottom: 6px; }

    .logo-hex {
        width: 110px;
        height: 122px;
        margin: 0 auto 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
        background: linear-gradient(135deg, #b8912f 0%, #7d5f1c 100%);
        box-shadow: 0 12px 30px rgba(110, 85, 40, 0.25);
    }

    .logo-hex-inner {
        width: 102px;
        height: 114px;
        clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
        background: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .logo-hex-inner img {
        width: 72px;
        height: 72px;
        object-fit: contain;
    }

    .brand-name {
        font-family: 'Orbitron', sans-serif;
        font-size: 30px;
        font-weight: 800;
        letter-spacing: 3px;
        color: #241d10;
        text-align: center;
    }

    .brand-accent {
        background: linear-gradient(135deg, #a8842f 0%, #7d5f1c 100%);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .login-subtitle {
        text-align: center;
        font-size: 16px;
        letter-spacing: 4px;
        text-transform: uppercase;
        color: #7d5f1c;
        margin-top: 10px;
        margin-bottom: 36px;
        font-weight: 700;
    }

    [data-testid="stTextInput"] label p {
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #4a4030 !important;
        letter-spacing: 0.3px;
    }

    [data-baseweb="input"] {
        border-radius: 12px !important;
    }
    [data-baseweb="input"] > div {
        border-radius: 12px !important;
        border: 2px solid #d8cdb5 !important;
        background: #ffffff !important;
        min-height: 4rem !important;
    }
    [data-baseweb="input"] > div:focus-within {
        border-color: #a8842f !important;
        box-shadow: 0 0 0 3px rgba(168, 132, 47, 0.18) !important;
    }
    [data-baseweb="input"] input {
        color: #241d10 !important;
        font-size: 18px !important;
    }
    [data-baseweb="input"] input::placeholder {
        font-size: 16px !important;
        color: #b3a892 !important;
    }

    .stButton > button, [data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #a8842f 0%, #7d5f1c 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        letter-spacing: 1.5px !important;
        min-height: 4rem !important;
        font-family: 'Poppins', sans-serif !important;
        margin-top: 20px;
    }
    .stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
        filter: brightness(1.08);
        box-shadow: 0 10px 28px rgba(125, 95, 28, 0.4);
    }
    .stButton > button p, [data-testid="stFormSubmitButton"] > button p,
    .stButton > button span, [data-testid="stFormSubmitButton"] > button span {
        color: #ffffff !important;
        font-size: 18px !important;
    }

    </style>
    """, unsafe_allow_html=True)

    # --- Header: heksagon logo + tajuk ---
    logo_src = get_logo_base64("assets/logo.png")

    if logo_src:
        st.markdown(
            f'<div class="logo-wrap">'
            f'  <div class="logo-hex">'
            f'    <div class="logo-hex-inner">'
            f'      <img src="{logo_src}" alt="logo">'
            f'    </div>'
            f'  </div>'
            f'  <div class="brand-name"><span class="brand-accent">SMART</span> EXAM</div>'
            f'  <div class="login-subtitle">Lecturer Login</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="logo-wrap">'
            '  <div class="brand-name"><span class="brand-accent">SMART</span> EXAM</div>'
            '  <div class="login-subtitle">Lecturer Login</div>'
            '</div>',
            unsafe_allow_html=True
        )

    lecturer_code = st.text_input(
        "Lecturer Secret Code",
        type="password",
        placeholder="Enter lecturer secret code"
    )

    course_code = st.text_input(
        "Course Code",
        placeholder="Example: DFK50083"
    )

    class_name = st.text_input(
        "Class",
        placeholder="Example: DDT1A"
    )

    if st.button(
        "LOGIN",
        use_container_width=True,
        type="primary"
    ):

        # 1. Semak secret code.
        if lecturer_code != LECTURER_CODE:
            st.error("Invalid lecturer secret code.")
            return

        if course_code.strip() == "":
            st.error("Please enter Course Code.")
            return

        if class_name.strip() == "":
            st.error("Please enter Class.")
            return

        # Normalise course code (sama macam student/admin).
        import re
        normalised = re.sub(
            r"[^A-Za-z0-9_-]", "-", course_code.strip()
        ).upper()

        # 2. Semak Course Code WUJUD dalam Firebase (collection exams).
        try:
            exam_doc = db.collection("exams").document(normalised).get()
        except Exception as e:
            st.error(f"Unable to verify course. {e}")
            return

        if not exam_doc.exists:
            st.error("Course Code not found. Please check and try again.")
            return

        # 3. Semak CLASS wujud untuk course ini
        #    (padan dengan className dalam exam_locations atau exam_students).
        input_class = class_name.strip().casefold()
        class_found = False

        try:
            for loc in db.collection("exam_locations").where("examId", "==", normalised).stream():
                loc_class = str(loc.to_dict().get("className", "")).strip().casefold()
                if loc_class == input_class:
                    class_found = True
                    break
        except Exception:
            pass

        if not class_found:
            try:
                for stu in db.collection("exam_students").where("examId", "==", normalised).stream():
                    stu_class = str(stu.to_dict().get("className", "")).strip().casefold()
                    if stu_class == input_class:
                        class_found = True
                        break
            except Exception:
                pass

        if not class_found:
            st.error("Class not found for this Course Code. Please check and try again.")
            return

        # Semua sah -> login berjaya.
        st.session_state.logged_in = True
        st.session_state.exam_id = normalised
        st.session_state.class_name = class_name.strip()

        # Simpan status login dalam URL supaya kekal selepas page reload
        # (auto-refresh / F5) -> tak auto logout.
        st.query_params["li"] = "1"
        st.query_params["exam"] = normalised
        st.query_params["cls"] = class_name.strip()

        st.rerun()

