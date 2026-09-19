import streamlit as st

from login import login_page
from dashboard import dashboard_page

st.set_page_config(
    page_title="SMART EXAM - Lecturer",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# SESSION STATE
# =========================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "exam_id" not in st.session_state:
    st.session_state.exam_id = ""

if "class_name" not in st.session_state:
    st.session_state.class_name = ""

# =========================================================
# RESTORE LOGIN DARI URL QUERY PARAMS
# =========================================================
# session_state hilang bila page betul-betul reload (F5 / meta-refresh).
# Simpan status login dalam URL supaya boleh "ingat" semula -> tak auto logout.
if not st.session_state.logged_in:
    qp = st.query_params
    if qp.get("li") == "1" and qp.get("exam"):
        st.session_state.logged_in = True
        st.session_state.exam_id = qp.get("exam", "")
        st.session_state.class_name = qp.get("cls", "")

# =========================================================
# ROUTING
# =========================================================

if st.session_state.logged_in:
    dashboard_page()
else:
    login_page()
