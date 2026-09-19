import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

try:
    import streamlit as st
except ImportError:
    st = None

def _credential_from_secrets():
    if st is None:
        return None
    try:
        if "firebase" in st.secrets:
            return dict(st.secrets["firebase"])
    except Exception:
        pass
    return None

def get_db():
    if not firebase_admin._apps:
        secret_info = _credential_from_secrets()
        if secret_info:
            cred = credentials.Certificate(secret_info)
        else:
            # Fallback fail tempatan (development)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            firebase_file = os.path.join(base_dir, "firebase_config.json")
            cred = credentials.Certificate(firebase_file)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = get_db()
