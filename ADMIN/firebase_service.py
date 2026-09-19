import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

try:
    import streamlit as st
except ImportError:
    st = None

def _credential_from_secrets():
    """Ambil kredential dari Streamlit Secrets kalau ada.

    Untuk hosting (Streamlit Cloud): letak kredential dalam Secrets bawah
    seksyen [firebase], supaya firebase_config.json tak perlu masuk GitHub.
    Pulangkan None kalau secrets tiada / tak berkaitan.
    """
    if st is None:
        return None
    try:
        if "firebase" in st.secrets:
            return dict(st.secrets["firebase"])
    except Exception:
        # st.secrets boleh raise kalau tiada fail secrets langsung.
        pass
    return None

def _credential_path():
    configured_path = os.environ.get("SMART_EXAM_FIREBASE_CREDENTIALS")
    if configured_path:
        return Path(configured_path).expanduser().resolve()

    local_path = Path(__file__).with_name("firebase_config.json")
    if local_path.exists():
        return local_path

    development_path = Path(__file__).parent.parent / "ADMIN" / "firebase_config.json"
    if development_path.exists():
        return development_path

    raise FileNotFoundError(
        "Firebase credentials not found. Set them in Streamlit Secrets under "
        "[firebase], place firebase_config.json in ADMIN_V2, or set "
        "SMART_EXAM_FIREBASE_CREDENTIALS."
    )

def get_db():
    if not firebase_admin._apps:
        # 1) Cuba Streamlit Secrets dulu (hosting).
        secret_info = _credential_from_secrets()
        if secret_info:
            cred = credentials.Certificate(secret_info)
        else:
            # 2) Fallback ke fail tempatan (development).
            cred = credentials.Certificate(str(_credential_path()))
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = get_db()
