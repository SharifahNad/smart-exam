import streamlit as st
import base64
from pathlib import Path

ADMIN_USERNAME = "admin"
ADMIN_SECRET = "SMARTEXAM2026"

def _file_to_base64(path="assets/logo.png"):
    """Baca fail dan tukar ke base64 (embed dalam HTML, selamat untuk hosting)."""
    base_dir = Path(__file__).parent
    f = base_dir / path
    if f.exists():
        return base64.b64encode(f.read_bytes()).decode()
    return None

def login_page():

    logo_b64 = _file_to_base64("assets/logo.png")

    st.markdown("""
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Orbitron:wght@700;800;900&display=swap');

    [data-testid="stSidebar"] { display: none; }
    [data-testid="stHeader"] { display: none; }
    [data-testid="stToolbar"] { display: none; }
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

    /* Label - BESAR & jelas */
    [data-testid="stTextInput"] label p {
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #4a4030 !important;
        letter-spacing: 0.3px;
    }

    /* Input field - SANGAT BESAR & panjang */
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

    /* Butang - BESAR emas */
    .stButton > button {
        background: linear-gradient(135deg, #a8842f 0%, #7d5f1c 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        letter-spacing: 1px !important;
        min-height: 4rem !important;
        font-family: 'Poppins', sans-serif !important;
        margin-top: 20px;
    }
    .stButton > button:hover {
        filter: brightness(1.08);
        box-shadow: 0 10px 28px rgba(125, 95, 28, 0.4);
    }
    .stButton > button p, .stButton > button span {
        color: #ffffff !important;
        font-size: 18px !important;
    }

    .login-note { color: #a89c84; font-size: 12px; text-align: center; margin-top: 26px; letter-spacing: 0.5px; }

    </style>
    """, unsafe_allow_html=True)

    # --- Header: heksagon logo + tajuk ---
    if logo_b64:
        st.markdown(
            f'<div class="logo-wrap">'
            f'  <div class="logo-hex">'
            f'    <div class="logo-hex-inner">'
            f'      <img src="data:image/png;base64,{logo_b64}" alt="logo">'
            f'    </div>'
            f'  </div>'
            f'  <div class="brand-name"><span class="brand-accent">SMART</span> EXAM</div>'
            f'  <div class="login-subtitle">Admin Login</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="logo-wrap">'
            '  <div class="brand-name"><span class="brand-accent">SMART</span> EXAM</div>'
            '  <div class="login-subtitle">Admin Console</div>'
            '</div>',
            unsafe_allow_html=True
        )

    username = st.text_input(
        "Username",
        placeholder="Enter admin username"
    )

    secret = st.text_input(
        "Secret code",
        type="password",
        placeholder="Enter admin secret code"
    )

    if st.button(
        "SIGN IN TO ADMIN CONSOLE",
        use_container_width=True,
        type="primary"
    ):

        if username == ADMIN_USERNAME and secret == ADMIN_SECRET:
            st.session_state.logged_in = True
            # Simpan penanda login dalam URL supaya kekal selepas reload.
            st.query_params["li"] = "1"
            st.rerun()
        else:
            st.error("Invalid username or secret code.")


    st.markdown(
        '<div class="login-note">Authorized personnel only · SMART EXAM Admin</div>',
        unsafe_allow_html=True
    )
