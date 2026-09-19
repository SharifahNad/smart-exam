from datetime import datetime, timezone, timedelta
from html import escape

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from firebase_admin import firestore

from firebase_service import db

MALAYSIA = timezone(timedelta(hours=8))

def ic(name, size=20, color="#78716c"):
    return (
        f'<span class="material-icons" '
        f'style="font-size:{size}px;color:{color};vertical-align:middle;">{name}</span>'
    )

import base64
from pathlib import Path

def _file_to_base64(path="assets/logo.png"):
    # Cari logo relatif kepada lokasi fail .py ni (bukan folder semasa),
    # supaya logo keluar bila di-host di Streamlit Cloud.
    base_dir = Path(__file__).parent
    f = base_dir / path
    if f.exists():
        return base64.b64encode(f.read_bytes()).decode()
    return None


# =========================================================
# CSS
# =========================================================

def load_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/icon?family=Material+Icons');

        [data-testid="stToolbar"] { display: none !important; }
        footer { visibility: hidden; }
        [data-testid="stHeader"] { background: transparent !important; box-shadow: none !important; }

        [data-testid="stSidebar"] {
            display: block !important;
            visibility: visible !important;
            transform: none !important;
            margin-left: 0 !important;
            min-width: 250px !important;
            width: 250px !important;
        }
        section[data-testid="stSidebar"] {
            transform: none !important;
            margin-left: 0 !important;
        }
        section[data-testid="stSidebar"] > div { transform: none !important; }

        .stApp { background: #f6f4ef; }
        .block-container { max-width: 1500px; padding: 1.6rem 2.2rem 4rem; }

        [data-testid="stSidebar"] { background: #34170D; }
        [data-testid="stSidebar"] * { color: #e7e5e4; }
        [data-testid="stSidebar"] .stButton > button {
            background: #b42318; color: #fff !important; border: 1px solid #b42318;
            border-radius: 9px; font-weight: 650;
        }
        [data-testid="stSidebar"] .stButton > button:hover { background: #912018; }

        /* Butang di kawasan utama (End Exam) - merah */
        section.main .stButton > button {
            background: #dc2626;
            color: #fff !important;
            border: 1px solid #dc2626;
            border-radius: 9px;
            font-weight: 700;
        }
        section.main .stButton > button:hover { background: #b91c1c; }

        .sb-brand { display:flex; align-items:center; gap:10px; padding:6px 4px 4px; }
        .sb-logo {
            width:40px; height:40px; border-radius:10px; background:#2563eb;
            display:flex; align-items:center; justify-content:center;
            color:#fff !important; font-weight:800; font-size:18px;
        }
        .sb-name { font-weight:800; font-size:16px; color:#fff; }
        .sb-role { font-size:11px; color:#a8a29e; margin-top:1px; }

        .material-icons { line-height: 1; }

        .page-title {
            font-size: 30px; font-weight: 800; color: #1c1917; letter-spacing: -.02em;
            margin: 0; display: flex; align-items: center; gap: 10px;
        }
        .page-subtitle { font-size: 13px; color: #78716c; margin-bottom: 20px; }

        .info-bar {
            display: flex; background: #f1e9db; border: 1px solid #e6dcc8;
            border-radius: 14px; overflow: hidden; margin-bottom: 18px;
        }
        .info-cell { flex: 1; padding: 15px 22px; border-right: 1px solid #e0d5bf; }
        .info-cell:last-child { border-right: none; }
        .info-label {
            font-size: 11px; color: #a1917a; font-weight: 600; text-transform: uppercase;
            letter-spacing: .05em; display: flex; align-items: center; gap: 6px;
        }
        .info-value { font-size: 16px; color: #1c1917; font-weight: 720; margin-top: 4px; }

        .stat-card {
            background: #fff; border: 1px solid #eee6d8; border-radius: 16px;
            padding: 18px 20px; box-shadow: 0 1px 3px rgba(28,25,23,.05);
        }
        .stat-value { font-size: 30px; font-weight: 800; color: #1c1917; line-height: 1.1; margin-top: 8px; }
        .stat-label { font-size: 13px; color: #78716c; margin-top: 2px; }
        .stat-pct { font-size: 13px; color: #12b76a; font-weight: 700; }

        .panel-title {
            font-size: 16px; font-weight: 750; color: #1c1917;
            display: flex; align-items: center; gap: 8px;
        }
        .panel-title.red { color: #dc2626; }
        .panel-sub { font-size: 12px; color: #78716c; margin: 2px 0 10px; }

        .panel {
            background: #fff; border: 1px solid #eee6d8; border-radius: 16px;
            padding: 18px 20px; box-shadow: 0 1px 3px rgba(28,25,23,.05);
        }

        .susp-row {
            display: flex; align-items: center; justify-content: space-between;
            padding: 11px 0; border-bottom: 1px solid #f5f0e6;
        }
        .susp-name { font-weight: 650; color: #1c1917; font-size: 14px; }
        .susp-detail { font-size: 12px; color: #78716c; }
        .susp-time { font-size: 12px; color: #78716c; }
        .susp-tag {
            background: #fef3f2; color: #dc2626; font-size: 11px; font-weight: 700;
            padding: 3px 10px; border-radius: 20px; margin-left: 10px;
        }
        .empty-note { color: #78716c; font-size: 13px; padding: 20px 0; }

        [data-testid="stDataFrame"] { border: 1px solid #eee6d8; border-radius: 12px; }
        hr { border-color: #eee6d8 !important; }

        /* ============ STUDENT LIST TABLE (badge warna) ============ */
        .sl-table {
            width: 100%; border-collapse: collapse; background: #fff;
            border: 1px solid #eee6d8; border-radius: 12px; overflow: hidden;
            font-size: 13.5px;
        }
        .sl-table th {
            background: #f1e9db; color: #7a5a3a; text-align: left;
            padding: 11px 14px; font-weight: 700; font-size: 12px;
            text-transform: uppercase; letter-spacing: .03em;
            border-bottom: 1px solid #e0d5bf; border-right: 1px solid #e6dcc8;
        }
        .sl-table th:last-child { border-right: none; }
        .sl-table td {
            padding: 11px 14px; color: #1c1917;
            border-bottom: 1px solid #f2eadc; border-right: 1px solid #f2eadc;
        }
        .sl-table td:last-child { border-right: none; }
        .sl-table tr:last-child td { border-bottom: none; }
        .sl-table tr:hover td { background: #faf6ee; }

        .badge {
            display: inline-block; padding: 3px 12px; border-radius: 20px;
            font-size: 11.5px; font-weight: 700; letter-spacing: .02em;
        }
        .badge-active   { background: #e6f6ec; color: #12813f; }                        /* hijau  */
        .badge-inactive { background: #fdecec; color: #c0392b; }                        /* merah  */
        .badge-enabled  { background: #ffffff; color: #1c1917; border: 1px solid #e0d5bf; }  /* biasa (hitam/putih) */
        .badge-disabled { background: #fef4d6; color: #b7791f; }                        /* kuning */

        /* ============ SUSPICIOUS GROUP (gabung ikut nama) ============ */
        .sg-card {
            background: #fff; border: 1px solid #eee6d8; border-radius: 14px;
            padding: 0; margin-bottom: 14px; overflow: hidden;
            box-shadow: 0 1px 3px rgba(28,25,23,.05);
        }
        /* buang default marker segi tiga browser */
        .sg-card > summary { list-style: none; cursor: pointer; }
        .sg-card > summary::-webkit-details-marker { display: none; }

        .sg-head {
            display: flex; align-items: center; justify-content: space-between;
            padding: 13px 18px; background: #f9f4ea; border-bottom: 1px solid #eee6d8;
        }
        .sg-head-left { display: flex; align-items: center; gap: 12px; }
        /* chevron yang berputar bila dibuka */
        .sg-chevron {
            transition: transform .2s ease; color: #78716c;
            display: inline-flex; align-items: center;
        }
        .sg-card[open] > summary .sg-chevron { transform: rotate(90deg); }

        .sg-name { font-weight: 750; color: #1c1917; font-size: 15px; }
        .sg-meta { font-size: 12px; color: #78716c; margin-top: 2px; }
        .sg-count {
            background: #fef3f2; color: #dc2626; font-size: 12px; font-weight: 800;
            padding: 4px 12px; border-radius: 20px;
        }
        .sg-item {
            display: flex; align-items: center; justify-content: space-between;
            padding: 10px 18px; border-bottom: 1px solid #f5f0e6;
        }
        .sg-item:last-child { border-bottom: none; }
        .sg-detail { font-size: 13.5px; color: #1c1917; font-weight: 600; }
        .sg-time { font-size: 12px; color: #78716c; }
        </style>
        """,
        unsafe_allow_html=True,
    )

# =========================================================
# HELPERS
# =========================================================

def get_electron_entered_ids(exam_id):
    entered_ids = set()
    try:
        for doc in db.collection("exam_status").where("examId", "==", exam_id).stream():
            item = doc.to_dict()
            sid = str(item.get("studentId", "")).strip()
            if sid:
                entered_ids.add(sid)
    except Exception:
        pass
    return entered_ids

def get_extension_status(exam_id):
    """
    Pulangkan 2 set dari exam_extension_status:
    - browser_ids: student yang BUKA browser
    - ext_active_ids: student yang extension AKTIF (ada hantar data)
    """
    browser_ids = set()
    ext_active_ids = set()
    try:
        for doc in db.collection("exam_extension_status").where("examId", "==", exam_id).stream():
            item = doc.to_dict()
            sid = str(item.get("studentId", "")).strip()
            if not sid:
                continue
            if item.get("browserOpened") is True:
                browser_ids.add(sid)
            if item.get("extensionActive") is True:
                ext_active_ids.add(sid)
    except Exception:
        pass
    return browser_ids, ext_active_ids

def extension_status_label(student_id, browser_ids, ext_active_ids):
    """
    Logik:
    - Tak buka browser -> "Enabled" (biar je, tak salah)
    - Buka browser + extension aktif -> "Enabled"
    - Buka browser TAPI extension tak aktif -> "Disabled" (sus)
    """
    sid = str(student_id).strip()
    if sid not in browser_ids:
        return "Enabled"
    if sid in ext_active_ids:
        return "Enabled"
    return "Disabled"

def _within_today(ts):
    today = datetime.now(MALAYSIA).date()
    if ts is None:
        return True
    try:
        dt = ts if isinstance(ts, datetime) else ts.ToDatetime()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(MALAYSIA).date() == today
    except Exception:
        return True

def get_suspicious_today(exam_id, selected_class="All classes"):
    rows = []
    try:
        for doc in (
            db.collection("exam_monitoring")
            .where("examId", "==", exam_id)
            .where("violation", "==", "Suspicious")
            .stream()
        ):
            e = doc.to_dict()
            if _within_today(e.get("createdAt")):
                rows.append({
                    "name": e.get("studentName", "-"),
                    "pc": e.get("pc", "-"),
                    "className": str(e.get("className", "")).strip(),
                    "detail": e.get("details", e.get("source", "Suspicious activity")),
                    "time": e.get("time", "-"),
                    "_createdAt": e.get("createdAt"),
                })
    except Exception:
        pass

    try:
        for doc in db.collection("face_detection").where("examId", "==", exam_id).stream():
            e = doc.to_dict()
            if e.get("createdAt") is not None and _within_today(e.get("createdAt")):
                rows.append({
                    "name": e.get("studentName", "-"),
                    "pc": e.get("pc", "-"),
                    "className": str(e.get("className", "")).strip(),
                    "detail": e.get("details", "Face detection"),
                    "time": e.get("time", "-"),
                    "_createdAt": e.get("createdAt"),
                })
    except Exception:
        pass

    if selected_class and selected_class != "All classes":
        target = selected_class.strip().casefold()
        rows = [
            r for r in rows
            if (not r["className"]) or (r["className"].casefold() == target)
        ]

    def sort_key(r):
        ts = r.get("_createdAt")
        try:
            dt = ts if isinstance(ts, datetime) else (ts.ToDatetime() if ts else None)
            if dt and dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt or datetime.max.replace(tzinfo=timezone.utc)
        except Exception:
            return datetime.max.replace(tzinfo=timezone.utc)

    rows.sort(key=sort_key, reverse=True)
    return rows

def render_donut(active, not_active):
    total = active + not_active
    fig = go.Figure(data=[go.Pie(
        labels=["Active", "Not Active"],
        values=[active, max(not_active, 0)],
        hole=.66,
        marker=dict(colors=["#22c55e", "#e5e7eb"]),
        textinfo="none",
        sort=False,
    )])
    fig.update_layout(
        showlegend=False,
        margin=dict(t=6, b=6, l=6, r=6),
        height=220,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        annotations=[dict(
            text=f"<b style='font-size:24px'>{active}</b><br>Active<br>(of {total})",
            x=0.5, y=0.5, showarrow=False, font=dict(size=13),
        )],
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# =========================================================
# END EXAM - POP-UP DIALOG
# =========================================================

@st.dialog("End Examination")
def confirm_end_exam_dialog(exam_id):
    st.markdown(
        "Are you sure you want to **end this exam**?"
    )

    col_yes, col_no = st.columns(2)

    if col_yes.button("Yes", use_container_width=True, type="primary"):
        try:
            db.collection("exams").document(exam_id).update({
                "active": False,
                "endedAt": firestore.SERVER_TIMESTAMP
            })
            st.success("Exam ended successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to end the exam: {e}")

    if col_no.button("Cancel", use_container_width=True):
        st.rerun()

# =========================================================
# DASHBOARD PAGE
# =========================================================

def dashboard_page():
    load_css()

    exam_id = st.session_state.get("exam_id", "")
    login_class = st.session_state.get("class_name", "")

    # ---- Sidebar ----
    with st.sidebar:
        _logo = _file_to_base64("assets/logo.png")
        _logo_html = (
            f'<img src="data:image/png;base64,{_logo}" '
            f'style="width:40px;height:40px;border-radius:10px;object-fit:contain;">'
            if _logo
            else '<div class="sb-logo">S</div>'
        )
        st.markdown(
            f"""
            <div class="sb-brand">
                {_logo_html}
                <div>
                    <div class="sb-name">SMART EXAM</div>
                    <div class="sb-role">LECTURER CONSOLE</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()
        st.markdown(f"**Course:** {exam_id if exam_id else '-'}")
        st.markdown(f"**Class:** {login_class if login_class else '-'}")
        st.divider()

        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.pop("exam_id", None)
            st.session_state.pop("class_name", None)
            # Bersihkan URL params supaya tak auto-login semula.
            st.query_params.clear()
            st.rerun()


    # ---- Header (tajuk kiri + End Exam kanan hujung) ----
    now = datetime.now(MALAYSIA)

    head_left, head_right = st.columns([4, 1])

    with head_left:
        st.markdown(
            f'<div class="page-title">{ic("monitor", 30, "#1c1917")} Live Monitoring</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="page-subtitle">Monitor students and suspicious behaviour '
            f'during examinations &nbsp;·&nbsp; {now.strftime("%d %b %Y · %I:%M %p")}</div>',
            unsafe_allow_html=True,
        )

    with head_right:
        if exam_id:
            if st.button("End Exam", use_container_width=True, key="end_exam"):
                confirm_end_exam_dialog(exam_id)

    if not exam_id:
        st.warning("No course selected. Please log in with a Course Code.")
        return

    # ---- Load data ----
    exam_students = []
    try:
        for doc in db.collection("exam_students").where("examId", "==", exam_id).stream():
            exam_students.append(doc.to_dict())
    except Exception:
        pass

    course_name = "-"
    try:
        exam_doc = db.collection("exams").document(exam_id).get()
        if exam_doc.exists:
            course_name = exam_doc.to_dict().get("courseName", "-")
    except Exception:
        pass

    class_students = exam_students
    if login_class:
        matched = [
            s for s in exam_students
            if str(s.get("className", "")).strip().casefold() == login_class.strip().casefold()
        ]
        if matched:
            class_students = matched

    lab_name = class_students[0].get("locationName", "-") if class_students else "-"

    class_student_ids = {
        str(s.get("studentId", "")).strip()
        for s in class_students if str(s.get("studentId", "")).strip()
    }

    entered_ids = get_electron_entered_ids(exam_id)
    browser_ids, ext_active_ids = get_extension_status(exam_id)

    active = len(entered_ids & class_student_ids)
    total = len(class_student_ids)
    not_active = total - active
    active_pct = f"({round(active/total*100)}%)" if total else ""

    # Extension count: student yang statusnya "Enabled" (guna logik).
    ext_count = sum(
        1 for sid in class_student_ids
        if extension_status_label(sid, browser_ids, ext_active_ids) == "Enabled"
    )
    ext_pct = f"({round(ext_count/total*100)}%)" if total else ""

    suspicious = get_suspicious_today(exam_id, login_class if login_class else "All classes")
    suspicious_count = len(suspicious)

    # ---- Info bar ----
    st.markdown(
        f"""
        <div class="info-bar">
            <div class="info-cell"><div class="info-label">{ic("school", 15, "#a1917a")} Course</div>
                <div class="info-value">{escape(str(exam_id))}</div></div>
            <div class="info-cell"><div class="info-label">{ic("description", 15, "#a1917a")} Exam</div>
                <div class="info-value">{escape(str(course_name))}</div></div>
            <div class="info-cell"><div class="info-label">{ic("groups", 15, "#a1917a")} Class</div>
                <div class="info-value">{escape(str(login_class if login_class else "-"))}</div></div>
            <div class="info-cell"><div class="info-label">{ic("science", 15, "#a1917a")} Lab</div>
                <div class="info-value">{escape(str(lab_name))}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- 4 Cards ----
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(
        f'<div class="stat-card">{ic("check_circle", 24, "#12b76a")}'
        f'<div class="stat-value">{active} <span class="stat-pct">{active_pct}</span></div>'
        f'<div class="stat-label">Students Active</div></div>',
        unsafe_allow_html=True,
    )
    c2.markdown(
        f'<div class="stat-card">{ic("warning", 24, "#f79009")}'
        f'<div class="stat-value">{suspicious_count}</div>'
        f'<div class="stat-label">Suspicious Activity</div></div>',
        unsafe_allow_html=True,
    )
    c3.markdown(
        f'<div class="stat-card">{ic("extension", 24, "#7a5af8")}'
        f'<div class="stat-value">{ext_count}/{total} <span class="stat-pct">{ext_pct}</span></div>'
        f'<div class="stat-label">Extension Enabled</div></div>',
        unsafe_allow_html=True,
    )
    c4.markdown(
        f'<div class="stat-card">{ic("group", 24, "#a1917a")}'
        f'<div class="stat-value">{total}</div>'
        f'<div class="stat-label">Total Students</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ---- Donut + Suspicious (3 latest) ----
    left, right = st.columns(2)

    with left:
        st.markdown(
            f'<div class="panel-title">{ic("groups", 18, "#1c1917")} Student Status</div>'
            f'<div class="panel-sub">Active vs Not Active</div>',
            unsafe_allow_html=True,
        )
        render_donut(active, not_active)

    with right:
        susp_html = (
            '<div class="panel">'
            f'<div class="panel-title red">{ic("error", 18, "#dc2626")} Recent Suspicious Behaviour</div>'
            '<div class="panel-sub">Latest 3 suspicious activities detected</div>'
        )
        if suspicious:
            for r in suspicious[:3]:
                susp_html += (
                    '<div class="susp-row">'
                    '<div>'
                    f'<div class="susp-name">{escape(str(r["detail"]))}</div>'
                    f'<div class="susp-detail">{escape(str(r["name"]))} · {escape(str(r["pc"]))}</div>'
                    '</div>'
                    '<div>'
                    f'<span class="susp-time">{ic("schedule", 14)} {escape(str(r["time"]))}</span>'
                    '<span class="susp-tag">Suspicious</span>'
                    '</div>'
                    '</div>'
                )
        else:
            susp_html += '<div class="empty-note">No suspicious behaviour detected today.</div>'
        susp_html += '</div>'
        st.markdown(susp_html, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ---- Student List (JADUAL HTML + badge warna, Status & Extension di 2 kolum terakhir) ----
    with st.expander("Student List", expanded=True):
        if class_students:
            sorted_students = sorted(
                class_students,
                key=lambda s: (
                    str(s.get("className", "")).strip().casefold(),
                    str(s.get("studentId", "")).strip(),
                ),
            )

            table_html = (
                '<table class="sl-table">'
                '<thead><tr>'
                '<th>Bil</th><th>Name</th><th>Student ID</th>'
                '<th>Class</th><th>Location</th>'
                '<th>Status</th><th>Extension</th>'
                '</tr></thead><tbody>'
            )

            for i, s in enumerate(sorted_students, start=1):
                sid = str(s.get("studentId", "")).strip()

                is_active = sid in entered_ids
                status_badge = (
                    '<span class="badge badge-active">Active</span>'
                    if is_active
                    else '<span class="badge badge-inactive">Not Active</span>'
                )

                ext_label = extension_status_label(sid, browser_ids, ext_active_ids)
                ext_badge = (
                    '<span class="badge badge-enabled">Enabled</span>'
                    if ext_label == "Enabled"
                    else '<span class="badge badge-disabled">Disabled</span>'
                )

                table_html += (
                    '<tr>'
                    f'<td>{i}</td>'
                    f'<td>{escape(str(s.get("studentName", "-")))}</td>'
                    f'<td>{escape(str(s.get("studentId", "-")))}</td>'
                    f'<td>{escape(str(s.get("className", "-")))}</td>'
                    f'<td>{escape(str(s.get("locationName", "-")))}</td>'
                    f'<td>{status_badge}</td>'
                    f'<td>{ext_badge}</td>'
                    '</tr>'
                )

            table_html += '</tbody></table>'
            st.markdown(table_html, unsafe_allow_html=True)
        else:
            st.info("No students registered for this course yet.")

    # ---- Full Suspicious List (GROUP GABUNG IKUT NAMA STUDENT - DROPDOWN) ----
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    with st.expander("All Suspicious Behaviour", expanded=False):
        if suspicious:
            # Gabung ikut nama student (kekalkan susunan terbaru dulu)
            grouped = {}
            order = []
            for r in suspicious:
                name = str(r["name"]).strip() or "-"
                if name not in grouped:
                    grouped[name] = {"pc": r["pc"], "items": []}
                    order.append(name)
                grouped[name]["items"].append(r)

            groups_html = ""
            for name in order:
                g = grouped[name]
                count = len(g["items"])
                # setiap group = <details> yang boleh klik untuk expand/collapse
                groups_html += (
                    '<details class="sg-card">'
                    '<summary>'
                    '<div class="sg-head">'
                    '<div class="sg-head-left">'
                    f'<span class="sg-chevron">{ic("chevron_right", 22, "#78716c")}</span>'
                    '<div>'
                    f'<div class="sg-name">{escape(str(name))}</div>'
                    f'<div class="sg-meta">{ic("computer", 13)} {escape(str(g["pc"]))}</div>'
                    '</div>'
                    '</div>'
                    f'<div class="sg-count">{count} alert{"s" if count != 1 else ""}</div>'
                    '</div>'
                    '</summary>'
                )
                for r in g["items"]:
                    cls = f' · {escape(str(r["className"]))}' if r["className"] else ""
                    groups_html += (
                        '<div class="sg-item">'
                        f'<div class="sg-detail">{escape(str(r["detail"]))}{cls}</div>'
                        f'<div class="sg-time">{ic("schedule", 13)} {escape(str(r["time"]))}</div>'
                        '</div>'
                    )
                groups_html += '</details>'

            st.markdown(groups_html, unsafe_allow_html=True)
        else:
            st.info("No suspicious behaviour detected today.")
