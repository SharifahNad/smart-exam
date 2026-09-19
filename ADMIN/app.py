import streamlit as st

from dashboard import dashboard_page
from login import login_page

st.set_page_config(
    page_title="SMART EXAM - Admin",
    page_icon="🛡️",
    layout="wide",
)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# =========================================================
# RESTORE LOGIN DARI URL QUERY PARAMS
# =========================================================
# session_state hilang bila page reload penuh (F5 / auto-refresh).
# Simpan penanda login dalam URL supaya boleh "ingat" semula -> tak auto logout.
if not st.session_state.logged_in:
    if st.query_params.get("li") == "1":
        st.session_state.logged_in = True

if st.session_state.logged_in:
    dashboard_page()
else:
    login_page()
