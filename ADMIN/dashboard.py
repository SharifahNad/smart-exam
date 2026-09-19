from datetime import datetime, time
from html import escape
from pathlib import Path
import base64
import re

import pandas as pd
import streamlit as st
from firebase_admin import firestore

from firebase_service import db
from login import ADMIN_SECRET


def _logo_base64(path="assets/logo.png"):
    """Read the logo file and return base64 (embed in HTML). None if missing."""
    f = Path(path)
    if f.exists():
        return base64.b64encode(f.read_bytes()).decode()
    return None


def render_monitoring_html(rows):
    """Render the live monitoring rows as an HTML table.

    For any row whose Violation is "Suspicious", ONLY three cells are
    highlighted red: Student Name, Student ID and PC. All other cells stay
    normal. Non-suspicious rows are shown normally.
    """
    header_cells = [
        "Student Name", "Student ID", "PC",
        "Course", "Location", "Source", "Violation", "Details", "Time",
    ]

    html = [
        "<div style='overflow-x:auto;'>",
        "<table style='width:100%; border-collapse:collapse; font-size:14px;'>",
        "<thead><tr>",
    ]
    for col in header_cells:
        html.append(
            "<th style='text-align:left; padding:10px; "
            "border-bottom:2px solid #e4e7ec; color:#475467; "
            "font-weight:700; white-space:nowrap;'>" + escape(col) + "</th>"
        )
    html.append("</tr></thead><tbody>")

    for row in rows:
        suspicious = str(row.get("Violation", "")).strip().casefold() == "suspicious"
        red = "color:#dc2626; font-weight:700;" if suspicious else ""
        base = "padding:10px; border-bottom:1px solid #f0f1f3;"

        def cell(value, highlight=False):
            style = base + (red if highlight else "")
            return f"<td style='{style}'>{escape(str(value))}</td>"

        html.append("<tr>")
        # The three highlighted-when-suspicious columns:
        html.append(cell(row.get("Student Name", "-"), highlight=True))
        html.append(cell(row.get("Student ID", "-"), highlight=True))
        html.append(cell(row.get("PC", "-"), highlight=True))
        # The rest stay normal:
        html.append(cell(row.get("Course", "-")))
        html.append(cell(row.get("Location", "-")))
        html.append(cell(row.get("Source", "-")))
        html.append(cell(row.get("Violation", "-")))
        html.append(cell(row.get("Details", "-")))
        html.append(cell(row.get("Time", "-")))
        html.append("</tr>")

    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)


REQUIRED_ROSTER_COLUMNS = {
    "student id": "studentId",
    "student name": "studentName",
    "class": "className",
}


def load_design_system():
    st.markdown(
        """
        <style>
        :root {
            --se-navy: #101828;
            --se-slate: #475467;
            --se-muted: #667085;
            --se-line: #e4e7ec;
            --se-blue: #b8912f;
            --se-blue-soft: #f5eddb;
        }
        .stApp { background: #f7f3ea; }
        [data-testid="stAppViewContainer"] { background: #f7f3ea; }
        .block-container {
            max-width: 1480px;
            padding: 2.25rem 2.5rem 4rem;
        }
        h1, h2, h3 { color: var(--se-navy); letter-spacing: -.025em; }
        h2 { font-size: 1.65rem !important; font-weight: 720 !important; }
        h3 { font-size: 1.08rem !important; font-weight: 680 !important; }
        p, label, [data-testid="stCaptionContainer"] { color: var(--se-muted); }
        [data-testid="stSidebar"] {
            background: #322614;
            border-right: 1px solid #241b0e;
            min-width: 272px;
        }
        [data-testid="stSidebar"] .block-container { padding: 1.7rem 1rem; }
        [data-testid="stSidebar"] * { color: #e8dfce; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            border-radius: 9px;
            padding: .55rem .65rem;
            transition: background .15s ease;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background: #4a3a22; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
            background: #b8912f;
            color: white;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) * {
            color: #ffffff !important;
        }
        .brand-lockup { padding: 0 .55rem 1rem; }
        .brand-mark {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 38px;
            height: 38px;
            border-radius: 10px;
            background: #b8912f;
            color: white !important;
            font-weight: 800;
            margin-right: 10px;
        }
        /* Logo transparent (tiada bingkai) */
        .brand-hexagon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-right: 10px;
            vertical-align: middle;
            background: transparent;
        }
        .brand-logo-img {
            width: 44px;
            height: 44px;
            object-fit: contain;
            background: transparent;
        }
        .brand-name { color: #ffffff !important; font-weight: 730; font-size: 18px; }
        .brand-version { color: #c9bda3 !important; font-size: 11px; margin: 8px 0 0 49px; }
        .page-kicker {
            color: #b8912f;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: .08em;
            text-transform: uppercase;
            margin-bottom: 4px;
        }
        [data-testid="stMetric"] {
            background: white;
            border: 1px solid var(--se-line);
            border-radius: 13px;
            padding: 18px 20px;
            box-shadow: 0 1px 2px rgba(16, 24, 40, .04);
        }
        [data-testid="stMetricLabel"] { color: var(--se-muted); font-weight: 600; }
        [data-testid="stMetricValue"] { color: var(--se-navy); font-weight: 730; }
        [data-testid="stForm"], [data-testid="stExpander"] {
            background: white;
            border: 1px solid var(--se-line);
            border-radius: 13px;
            padding: 18px;
            box-shadow: 0 1px 2px rgba(16, 24, 40, .035);
        }
        [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
            border: 1px solid var(--se-line);
            border-radius: 12px;
            overflow: hidden;
            background: white;
        }
        /* All buttons: blue background with white text (readable everywhere) */
        .stButton > button, [data-testid="stFormSubmitButton"] > button {
            border-radius: 9px;
            font-weight: 650;
            min-height: 2.65rem;
            background: #c0392b;
            color: #ffffff !important;
            border: 1px solid #c0392b;
            box-shadow: 0 1px 2px rgba(16, 24, 40, .08);
        }
        .stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
            background: #a5301f;
            border-color: #a5301f;
            color: #ffffff !important;
        }
        /* Force the label text (span/p) colour too, so it never disappears */
        .stButton > button p, [data-testid="stFormSubmitButton"] > button p,
        .stButton > button span, [data-testid="stFormSubmitButton"] > button span {
            color: #ffffff !important;
        }
        /* Primary button: same blue + white text */
        .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"] {
            background: #c0392b;
            border: 1px solid #c0392b;
            color: #ffffff !important;
        }
        .stButton > button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
            background: #a5301f;
            border-color: #a5301f;
            color: #ffffff !important;
        }
        /* Disabled button: light grey bg with dark-grey (readable) text + border,
           so the label never disappears when a button is disabled. */
        .stButton > button:disabled,
        .stButton > button[disabled],
        [data-testid="stFormSubmitButton"] > button:disabled,
        [data-testid="stFormSubmitButton"] > button[disabled] {
            background: #eef1f5 !important;
            color: #98a2b3 !important;
            border: 1px solid #d0d5dd !important;
            box-shadow: none !important;
        }
        .stButton > button:disabled p, .stButton > button:disabled span,
        .stButton > button[disabled] p, .stButton > button[disabled] span,
        [data-testid="stFormSubmitButton"] > button:disabled p,
        [data-testid="stFormSubmitButton"] > button:disabled span {
            color: #98a2b3 !important;
        }
        /* Sidebar button (Logout): same orange-red as all buttons */
        [data-testid="stSidebar"] .stButton > button {
            background: #c0392b;
            color: #ffffff !important;
            border: 1px solid #c0392b;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            background: #a5301f;
            border-color: #a5301f;
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] .stButton > button p,
        [data-testid="stSidebar"] .stButton > button span {
            color: #ffffff !important;
        }
        /* Text inputs, password, number, textarea, select: clear border + white bg */
        [data-baseweb="input"] > div,
        [data-baseweb="select"] > div,
        [data-baseweb="textarea"] > div,
        .stTextInput > div > div,
        .stNumberInput > div > div,
        .stDateInput > div > div,
        .stTimeInput > div > div {
            border-radius: 9px !important;
            border: 1.5px solid #cbd2dc !important;
            background: #ffffff !important;
        }
        /* The actual typed text — make it dark & readable */
        .stTextInput input,
        .stNumberInput input,
        .stDateInput input,
        .stTimeInput input,
        [data-baseweb="input"] input,
        textarea {
            color: #101828 !important;
            background: #ffffff !important;
        }
        /* Input label text — clearly visible */
        .stTextInput label, .stNumberInput label, .stSelectbox label,
        .stDateInput label, .stTimeInput label, .stTextArea label,
        .stFileUploader label, .stCheckbox label, .stRadio label {
            color: #344054 !important;
            font-weight: 600 !important;
        }
        /* Highlight focused input so the user sees where they are typing */
        [data-baseweb="input"]:focus-within > div,
        .stTextInput > div > div:focus-within {
            border-color: #b8912f !important;
            box-shadow: 0 0 0 3px rgba(184, 145, 47, .18) !important;
        }
        /* Checkboxes: visible box with border */
        [data-testid="stCheckbox"] label span:first-child,
        .stCheckbox [data-baseweb="checkbox"] div:first-child {
            border: 1.5px solid #98a2b3 !important;
            background: #ffffff !important;
        }
        /* File uploader dropzone: clear dashed border */
        [data-testid="stFileUploaderDropzone"] {
            border: 1.5px dashed #cbd2dc !important;
            background: #ffffff !important;
        }
        /* Data editor / dataframe: clear border */
        [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
            border: 1px solid var(--se-line) !important;
            border-radius: 12px;
        }
        [data-testid="stAlert"] { border-radius: 10px; border-width: 1px; }
        hr { border-color: var(--se-line) !important; margin: 1.7rem 0 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def normalize_id(value):
    return re.sub(r"[^A-Za-z0-9_-]", "-", str(value).strip()).upper()


def load_collection(name):
    rows = []
    for document in db.collection(name).stream():
        row = document.to_dict()
        row["_documentId"] = document.id
        rows.append(row)
    return rows


def load_collection_where(name, field_name, field_value):
    """Load only the documents whose `field_name` matches `field_value`.

    This performs the filtering in Firestore instead of streaming the whole
    collection and filtering in Python. It sharply reduces Firestore document
    reads for large collections such as exam_students.
    """
    rows = []
    query = db.collection(name).where(field_name, "==", field_value)
    for document in query.stream():
        row = document.to_dict()
        row["_documentId"] = document.id
        rows.append(row)
    return rows


def exam_label(exam):
    return exam.get("courseCode", exam.get("examId", exam["_documentId"]))


def location_label(location):
    location_name = location.get("locationName", "Unnamed location")
    class_name = location.get("className", "")
    if class_name:
        return f"{class_name} → {location_name}"
    return location_name


def location_time(location, exam=None):
    """Return a 'HH:MM - HH:MM' time string for a class/location.

    Prefers the location's own start/end time. For older records that have no
    per-location time, falls back to the exam-level time (if provided).
    """
    start = str(location.get("startTime", "")).strip()
    end = str(location.get("endTime", "")).strip()
    if not start and exam:
        start = str(exam.get("startTime", "")).strip()
    if not end and exam:
        end = str(exam.get("endTime", "")).strip()
    return f"{start or '-'} - {end or '-'}"


def delete_documents_by_field(collection_name, field_name, field_value):
    deleted = 0

    while True:
        documents = list(
            db.collection(collection_name)
            .where(field_name, "==", field_value)
            .limit(400)
            .stream()
        )

        if not documents:
            break

        batch = db.batch()
        for document in documents:
            batch.delete(document.reference)
        batch.commit()
        deleted += len(documents)

    return deleted


def delete_documents_by_ids(collection_name, document_ids):
    deleted = 0
    unique_ids = list(dict.fromkeys(document_ids))

    for start in range(0, len(unique_ids), 400):
        batch = db.batch()
        chunk = unique_ids[start:start + 400]
        for document_id in chunk:
            batch.delete(db.collection(collection_name).document(document_id))
        batch.commit()
        deleted += len(chunk)

    return deleted


def update_session_name_in_collection(collection_name, old_name, new_name):
    updated = 0

    while True:
        documents = list(
            db.collection(collection_name)
            .where("sessionName", "==", old_name)
            .limit(400)
            .stream()
        )

        if not documents:
            break

        batch = db.batch()
        for document in documents:
            batch.update(document.reference, {"sessionName": new_name})
        batch.commit()
        updated += len(documents)

    return updated


def rename_session(session, new_name):
    old_name = session["sessionName"]
    if old_name == new_name:
        return

    for collection_name in [
        "exams",
        "exam_locations",
        "exam_students",
        "exam_monitoring",
    ]:
        update_session_name_in_collection(collection_name, old_name, new_name)

    db.collection("sessions").document(session["_documentId"]).update({
        "sessionName": new_name,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    })


def clear_session_data(session):
    session_name = session["sessionName"]
    deleted = {}

    # Delete dependent data before deleting the parent session document.
    for collection_name in [
        "exam_monitoring",
        "exam_students",
        "exam_locations",
        "exams",
    ]:
        deleted[collection_name] = delete_documents_by_field(
            collection_name,
            "sessionName",
            session_name,
        )

        # Clean records made by an earlier ADMIN_V2 build as well.
        legacy_session_id = session.get("sessionId")
        if legacy_session_id:
            deleted[collection_name] += delete_documents_by_field(
                collection_name,
                "sessionId",
                legacy_session_id,
            )

    db.collection("sessions").document(session["_documentId"]).delete()
    deleted["sessions"] = 1
    return deleted


def reset_development_database():
    deleted = {}

    # recursive_delete also removes any nested subcollections.
    for collection in list(db.collections()):
        deleted[collection.id] = db.recursive_delete(collection)

    return dict(sorted(deleted.items()))


def parse_roster(uploaded_file):
    if uploaded_file.name.lower().endswith(".csv"):
        frame = pd.read_csv(uploaded_file, dtype=str)
    else:
        frame = pd.read_excel(uploaded_file, dtype=str, engine="openpyxl")

    frame.columns = [str(column).strip().lower() for column in frame.columns]
    missing = [column for column in REQUIRED_ROSTER_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(
            "Missing required columns: " + ", ".join(column.title() for column in missing)
        )

    frame = frame[list(REQUIRED_ROSTER_COLUMNS)].rename(columns=REQUIRED_ROSTER_COLUMNS)
    frame = frame.fillna("")
    for column in frame.columns:
        frame[column] = frame[column].astype(str).str.strip()

    frame = frame[frame["studentId"] != ""].copy()
    if frame.empty:
        raise ValueError("The roster contains no Student ID values.")

    duplicate_ids = frame[frame["studentId"].duplicated(keep=False)]["studentId"].unique()
    if len(duplicate_ids):
        raise ValueError("Duplicate Student ID values: " + ", ".join(duplicate_ids[:10]))

    empty_details = frame[(frame["studentName"] == "") | (frame["className"] == "")]
    if not empty_details.empty:
        raise ValueError("Every row must contain Student ID, Student Name and Class.")

    return frame


# Excel/CSV columns expected for bulk examination upload (Fasa 4).
REQUIRED_EXAM_COLUMNS = {
    "course code": "courseCode",
    "course name": "courseName",
    "session": "sessionName",
    "class": "className",
    "location": "locationName",
    "date": "examDate",
    "start": "startTime",
    "end": "endTime",
}


def parse_exam_file(uploaded_file):
    """Read the bulk examination Excel/CSV into a normalised DataFrame.

    Raises ValueError with a clear message if required columns are missing.
    Row-level validation is done separately in validate_exam_rows().
    """
    if uploaded_file.name.lower().endswith(".csv"):
        frame = pd.read_csv(uploaded_file, dtype=str)
    else:
        frame = pd.read_excel(uploaded_file, dtype=str, engine="openpyxl")

    frame.columns = [str(column).strip().lower() for column in frame.columns]
    missing = [column for column in REQUIRED_EXAM_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(column.title() for column in missing)
        )

    frame = frame[list(REQUIRED_EXAM_COLUMNS)].rename(columns=REQUIRED_EXAM_COLUMNS)
    frame = frame.fillna("")
    for column in frame.columns:
        frame[column] = frame[column].astype(str).str.strip()

    return frame


def _normalise_time(value):
    """Accept common time formats and return HH:MM, or None if invalid.

    Handles messy real-world spreadsheet values such as:
      "8.30 a.m", "11.30 a.m", "2.00 p.m", "(8.30 am", "5.00p.m",
      "08:30", "8:30 AM", "0830", "8AM", "8.30", "14:30", "2 pm".
    """
    text = str(value).strip().upper()

    # Detect AM/PM markers even when written as "a.m", "p.m", "a m", etc.
    is_am = False
    is_pm = False
    if "A" in text and "M" in text and text.index("A") < text.index("M"):
        is_am = True
    if "P" in text and "M" in text and text.index("P") < text.index("M"):
        is_pm = True

    # Keep only digits and the first separator; drop brackets, letters, spaces.
    digits = "".join(ch if ch.isdigit() else " " for ch in text).split()
    if not digits:
        return None

    hour = None
    minute = 0
    if len(digits) == 1:
        block = digits[0]
        if len(block) <= 2:          # "8", "14"
            hour = int(block)
        elif len(block) == 3:        # "830" -> 8:30
            hour, minute = int(block[0]), int(block[1:])
        elif len(block) == 4:        # "0830" / "1430"
            hour, minute = int(block[:2]), int(block[2:])
        else:
            return None
    else:                            # "8" "30"  (from "8.30" / "8:30")
        hour = int(digits[0])
        minute = int(digits[1])

    if minute >= 60:
        return None

    # Apply 12-hour -> 24-hour conversion when AM/PM is present.
    if is_pm and hour < 12:
        hour += 12
    elif is_am and hour == 12:
        hour = 0

    if not (0 <= hour <= 23):
        return None

    return f"{hour:02d}:{minute:02d}"


def validate_exam_rows(frame, existing_exam_locations):
    """Validate each row of the uploaded exam file.

    Returns (valid_records, errors) where:
      * valid_records: list of dicts ready to import, with a `_duplicate` flag
      * errors: list of dicts {row, courseCode, message}

    A row is a duplicate when the same examId already has the same
    class + location (either already in Firestore, or earlier in this file).
    """
    valid_records = []
    errors = []

    # Build a set of existing (examId, class, location) keys already in Firestore.
    seen_keys = set()
    for location in existing_exam_locations:
        key = (
            str(location.get("examId", "")).casefold(),
            str(location.get("className", "")).strip().casefold(),
            str(location.get("locationName", "")).strip().casefold(),
        )
        seen_keys.add(key)

    for position, (_, row) in enumerate(frame.iterrows(), start=2):
        # start=2 -> row 1 is the header in the spreadsheet
        course_code = normalize_id(row["courseCode"])
        course_name = row["courseName"].strip()
        session_name = row["sessionName"].strip()
        class_name = row["className"].strip()
        location_name = row["locationName"].strip()
        exam_date = row["examDate"].strip()
        start_time = _normalise_time(row["startTime"])
        end_time = _normalise_time(row["endTime"])

        row_errors = []
        if not course_code:
            row_errors.append("Course Code is missing")
        if not course_name:
            row_errors.append("Course Name is missing")
        if not session_name:
            row_errors.append("Session is missing")
        if not class_name:
            row_errors.append("Class is missing")
        if not location_name:
            row_errors.append("Location is missing")
        if not exam_date:
            row_errors.append("Exam Date is missing")
        if start_time is None:
            row_errors.append("Start Time is invalid")
        if end_time is None:
            row_errors.append("End Time is invalid")
        if start_time and end_time and end_time <= start_time:
            row_errors.append("Start time must be before end time")

        if row_errors:
            errors.append({
                "row": position,
                "courseCode": course_code or "-",
                "message": "; ".join(row_errors),
            })
            continue

        key = (course_code.casefold(), class_name.casefold(), location_name.casefold())
        is_duplicate = key in seen_keys
        seen_keys.add(key)

        valid_records.append({
            "row": position,
            "courseCode": course_code,
            "courseName": course_name,
            "sessionName": session_name,
            "className": class_name,
            "locationName": location_name,
            "examDate": exam_date,
            "startTime": start_time,
            "endTime": end_time,
            "_duplicate": is_duplicate,
        })

    return valid_records, errors


def import_exam_records(records):
    """Import validated exam records into Firestore.

    Creates/updates the exam document (keyed by course code) and adds one
    exam_locations document per class/location. Duplicate class/location rows
    (flagged during validation) are skipped. Returns a summary dict.
    """
    summary = {"exams": 0, "locations": 0, "skipped": 0}
    exams_written = set()

    for record in records:
        if record.get("_duplicate"):
            summary["skipped"] += 1
            continue

        exam_id = record["courseCode"]

        # Create the exam document once per course code (first time we see it).
        # NOTE: time (startTime/endTime) now lives on each class/location, since
        # one subject can run at different times for different classes (e.g. a
        # morning session for some classes and an afternoon session for others).
        # We keep the exam's own startTime/endTime as a first-row fallback only
        # (used by older code / displays that expect an exam-level time).
        if exam_id not in exams_written:
            exam_ref = db.collection("exams").document(exam_id)
            if not exam_ref.get().exists:
                exam_ref.set({
                    "examId": exam_id,
                    "courseCode": exam_id,
                    "courseName": record["courseName"],
                    "sessionName": record["sessionName"],
                    "examDate": record["examDate"],
                    "startTime": record["startTime"],   # fallback (first row)
                    "endTime": record["endTime"],       # fallback (first row)
                    "enrollmentKey": "",   # Admin sets this later under Examinations
                    "active": True,
                    "createdAt": firestore.SERVER_TIMESTAMP,
                })
                summary["exams"] += 1
            exams_written.add(exam_id)

        location_ref = db.collection("exam_locations").document()
        location_ref.set({
            "locationId": location_ref.id,
            "examId": exam_id,
            "sessionName": record["sessionName"],
            "courseCode": exam_id,
            "className": record["className"],
            "locationName": record["locationName"],
            "startTime": record["startTime"],   # per class/location time
            "endTime": record["endTime"],       # per class/location time
            "createdAt": firestore.SERVER_TIMESTAMP,
        })
        summary["locations"] += 1

    return summary


def upload_exams_page():
    st.subheader("Bulk exam registration")
    st.caption(
        "Register many examinations at once. Required columns: Course Code, "
        "Course Name, Session, Class, Location, Date, Start, End."
    )

    uploaded_file = st.file_uploader("Excel or CSV exam file", type=["xlsx", "csv"])
    if uploaded_file is None:
        return

    try:
        frame = parse_exam_file(uploaded_file)
    except Exception as error:
        st.error(str(error))
        return

    existing_locations = load_collection("exam_locations")
    valid_records, errors = validate_exam_rows(frame, existing_locations)

    duplicate_count = sum(1 for r in valid_records if r.get("_duplicate"))
    importable_count = len(valid_records) - duplicate_count

    # ---- PREVIEW ----
    st.subheader("Import preview")
    cols = st.columns(3)
    cols[0].metric("Ready to import", importable_count)
    cols[1].metric("Duplicates (will skip)", duplicate_count)
    cols[2].metric("Rows with errors", len(errors))

    if errors:
        st.error("Some rows contain errors and will not be imported:")
        st.dataframe(
            pd.DataFrame(errors).rename(columns={
                "row": "Row",
                "courseCode": "Course Code",
                "message": "Error",
            }),
            hide_index=True,
            use_container_width=True,
        )

    if valid_records:
        preview_rows = [{
            "Row": r["row"],
            "Course": r["courseCode"],
            "Course Name": r["courseName"],
            "Session": r["sessionName"],
            "Class": r["className"],
            "Location": r["locationName"],
            "Date": r["examDate"],
            "Time": f"{r['startTime']} - {r['endTime']}",
            "Status": "Duplicate (skip)" if r["_duplicate"] else "New",
        } for r in valid_records]
        st.subheader("Valid rows")
        st.dataframe(pd.DataFrame(preview_rows), hide_index=True, use_container_width=True)

    # ---- CONFIRM ----
    if importable_count == 0:
        st.warning("There is nothing new to import.")
        return

    st.divider()
    if st.button(
        f"Confirm import ({importable_count} new class/location rows)",
        type="primary",
    ):
        summary = import_exam_records(valid_records)
        st.success(
            f"Import complete. Created {summary['exams']} examination(s), "
            f"added {summary['locations']} class/location(s), "
            f"skipped {summary['skipped']} duplicate(s)."
        )


def overview_page():
    sessions = load_collection("sessions")
    exams = load_collection("exams")
    locations = load_collection("exam_locations")
    students = load_collection("exam_students")

    st.header("System overview")
    columns = st.columns(4)
    columns[0].metric("Sessions", len(sessions))
    columns[1].metric("Examinations", len(exams))
    columns[2].metric("Locations", len(locations))
    columns[3].metric("Registered students", len(students))

    if exams:
        st.subheader("Registered examinations")
        st.caption("Select an examination to view its details.")

        view_map = {
            f"{item.get('courseCode', item['_documentId'])} · "
            f"{item.get('courseName', '-')}": item
            for item in sorted(
                exams,
                key=lambda x: str(x.get("courseCode", x.get("_documentId", ""))),
            )
        }
        picked_label = st.selectbox(
            "Examination",
            ["— Select an examination —"] + list(view_map),
            key="overview_exam_view",
        )

        if picked_label in view_map:
            picked = view_map[picked_label]
            with st.container(border=True):
                detail_a = st.columns(2)
                detail_a[0].markdown(
                    f"**Course**\n\n{picked.get('courseCode', picked['_documentId'])}"
                )
                detail_a[1].markdown(
                    f"**Course Name**\n\n{picked.get('courseName', '-')}"
                )
                detail_b = st.columns(2)
                detail_b[0].markdown(
                    f"**Session**\n\n{picked.get('sessionName', '-')}"
                )
                detail_b[1].markdown(
                    f"**Date**\n\n{picked.get('examDate', '-')}"
                )
                detail_c = st.columns(2)
                detail_c[0].markdown(
                    f"**Time**\n\n{picked.get('startTime', '-')} - {picked.get('endTime', '-')}"
                )
                _active = bool(picked.get("active", False))
                _color = "#16a34a" if _active else "#dc2626"
                _text = "Open" if _active else "Closed"
                detail_c[1].markdown(
                    f"**Status**\n\n<span style='color:{_color}; font-weight:700;'>{_text}</span>",
                    unsafe_allow_html=True,
                )

        # ---- Quick open/close toggle via dropdown ---------------------------
        st.subheader("Open / close examinations")
        st.caption(
            "Open lets students log in; Closed blocks all logins. "
            "Use this to open an exam when it starts and close it when it ends."
        )

        toggle_map = {
            f"{item.get('courseCode', item['_documentId'])} · "
            f"{item.get('courseName', '-')}": item
            for item in sorted(
                exams,
                key=lambda x: str(x.get("courseCode", x.get("_documentId", ""))),
            )
        }
        chosen_label = st.selectbox(
            "Examination",
            list(toggle_map),
            key="toggle_active_select",
        )
        chosen_exam = toggle_map[chosen_label]
        is_active = bool(chosen_exam.get("active", False))

        status_col, button_col, _spacer = st.columns([1.3, 1, 5])
        status_text = "Open" if is_active else "Closed"
        status_color = "#16a34a" if is_active else "#dc2626"
        status_col.markdown(
            f"**Current status:** "
            f"<span style='color:{status_color}; font-weight:700;'>{status_text}</span>",
            unsafe_allow_html=True,
        )
        button_text = "Close examination" if is_active else "Open examination"
        if button_col.button(
            button_text,
            key=f"toggle_active_{chosen_exam['_documentId']}",
        ):
            db.collection("exams").document(chosen_exam["_documentId"]).update({
                "active": not is_active,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            })
            st.rerun()
    else:
        st.info("Create a session, then register the first examination.")

    st.divider()
    st.subheader("Delete completed session")
    completed_sessions = [
        session for session in sessions
        if not session.get("active", False)
    ]

    if not completed_sessions:
        st.info("There are no completed sessions. Mark a session as inactive first.")
    else:
        st.warning(
            "Deleting a completed session permanently removes its examinations, "
            "locations, student rosters and monitoring records."
        )
        completed_map = {
            session.get("sessionName", "Unnamed session"): session
            for session in completed_sessions
        }
        selected_name = st.selectbox(
            "Completed session",
            list(completed_map),
            key="overview_delete_session",
        )
        password = st.text_input(
            "Re-enter Admin secret code",
            type="password",
            key="overview_delete_password",
        )

        if st.button("Permanently delete completed session", type="primary"):
            if password != ADMIN_SECRET:
                st.error("Incorrect Admin secret code.")
            else:
                deleted = clear_session_data(completed_map[selected_name])
                st.success(
                    f"Deleted {selected_name} and {sum(deleted.values())} related documents."
                )
                st.rerun()

    # ---- ADD RESTRICTED AI / APP -------------------------------------------
    st.divider()
    with st.expander("➕ Add restricted AI / App"):
        st.caption(
            "Add a new AI/app that isn't blocked yet (e.g. a new tool). "
            "Students who open it during an exam will be flagged as Suspicious."
        )

        with st.form("add_restricted_app_form", clear_on_submit=True):
            col_n, col_w = st.columns(2)
            ai_name = col_n.text_input("Name", placeholder="Perplexity")
            ai_website = col_w.text_input("Website", placeholder="perplexity.ai")
            add_ai = st.form_submit_button("Add AI", type="primary")

        if add_ai:
            clean_name = ai_name.strip()
            # Normalise website to a bare hostname: drop scheme, www., trailing slash.
            clean_web = (
                ai_website.strip().lower()
                .replace("https://", "")
                .replace("http://", "")
                .replace("www.", "")
                .strip("/")
            )
            if not clean_name:
                st.error("Name is required.")
            elif not clean_web:
                st.error("Website is required (e.g. perplexity.ai).")
            else:
                # Duplicate check against existing restricted apps.
                existing = load_collection("restricted_apps")
                dup = any(
                    str(item.get("website", "")).strip().lower() == clean_web
                    for item in existing
                )
                if dup:
                    st.error(f"{clean_web} is already in the restricted list.")
                else:
                    ref = db.collection("restricted_apps").document()
                    ref.set({
                        "name": clean_name,
                        "website": clean_web,
                        "createdAt": firestore.SERVER_TIMESTAMP,
                    })
                    st.success(f"Added {clean_name} ({clean_web}) to the restricted list.")
                    st.rerun()

        restricted = load_collection("restricted_apps")
        if restricted:
            st.markdown("**Restricted list**")
            for item in sorted(restricted, key=lambda x: str(x.get("name", "")).lower()):
                row = st.columns([3, 3, 1])
                row[0].write(item.get("name", "-"))
                row[1].write(item.get("website", "-"))
                if row[2].button("Remove", key=f"rm_ai_{item['_documentId']}"):
                    db.collection("restricted_apps").document(item["_documentId"]).delete()
                    st.rerun()
        else:
            st.caption("No custom restricted apps yet. The built-in list still applies.")

    st.divider()
    with st.expander("Danger zone · Reset development database"):
        st.error(
            "This permanently deletes every collection and document in the connected "
            "Firestore database. The Firebase project and credentials remain available."
        )
        reset_password = st.text_input(
            "Re-enter Admin secret code",
            type="password",
            key="reset_database_password",
        )
        reset_phrase = st.text_input(
            'Type "RESET FIREBASE"',
            key="reset_database_phrase",
        )
        reset_acknowledged = st.checkbox(
            "I understand that this operation cannot be undone.",
            key="reset_database_acknowledgement",
        )

        reset_ready = (
            reset_password == ADMIN_SECRET
            and reset_phrase == "RESET FIREBASE"
            and reset_acknowledged
        )

        if st.button(
            "Reset development database",
            type="primary",
            disabled=not reset_ready,
            key="reset_database_button",
        ):
            with st.spinner("Deleting Firestore data..."):
                deleted = reset_development_database()

            if deleted:
                st.success(
                    f"Development database reset complete. Deleted {sum(deleted.values())} "
                    "documents across: " + ", ".join(deleted)
                )
            else:
                st.info("The development database was already empty.")
            st.rerun()


def sessions_page():
    st.header("1. Register session")
    st.caption(
        "Create a session before registering courses and examinations."
    )

    with st.form("session_form", clear_on_submit=True):
        session_name = st.text_input("Session name", placeholder="Final Examination 2026")
        active = st.selectbox("Status", ["Active", "Completed"]) == "Active"
        submitted = st.form_submit_button("Register session", type="primary")

    if submitted:
        clean_name = session_name.strip()
        existing_sessions = load_collection("sessions")
        existing_names = {
            str(item.get("sessionName", "")).strip().casefold()
            for item in existing_sessions
        }

        if not clean_name:
            st.error("Session Name is required.")
        elif clean_name.casefold() in existing_names:
            st.error("That Session Name already exists.")
        else:
            if active:
                batch = db.batch()
                for session in existing_sessions:
                    if session.get("active", False):
                        reference = db.collection("sessions").document(
                            session["_documentId"]
                        )
                        batch.update(reference, {
                            "active": False,
                            "updatedAt": firestore.SERVER_TIMESTAMP,
                        })
                batch.commit()

            session_reference = db.collection("sessions").document()
            session_reference.set({
                "sessionName": clean_name,
                "active": active,
                "createdAt": firestore.SERVER_TIMESTAMP,
            })
            st.success(f"Session {clean_name} registered.")
            st.rerun()

    sessions = load_collection("sessions")
    if sessions:
        st.subheader("Edit sessions")
        editable_rows = [{
            "_documentId": item["_documentId"],
            "Session Name": item.get("sessionName", ""),
            "Status": "Active" if item.get("active", False) else "Completed",
        } for item in sessions]

        edited_sessions = st.data_editor(
            pd.DataFrame(editable_rows),
            hide_index=True,
            use_container_width=True,
            column_config={
                "_documentId": None,
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["Active", "Completed"],
                    required=True,
                ),
            },
            num_rows="fixed",
            key="session_editor",
        )

        if st.button("Save session changes", type="primary"):
            clean_names = [
                str(value).strip()
                for value in edited_sessions["Session Name"]
            ]
            folded_names = [name.casefold() for name in clean_names]
            active_count = sum(
                1 for value in edited_sessions["Status"]
                if value == "Active"
            )

            if any(not name for name in clean_names):
                st.error("Session Name cannot be empty.")
            elif len(folded_names) != len(set(folded_names)):
                st.error("Session names must be unique.")
            elif active_count > 1:
                st.error("Only one session can be Active at a time.")
            else:
                original_map = {
                    item["_documentId"]: item
                    for item in sessions
                }
                for _, row in edited_sessions.iterrows():
                    session = original_map[row["_documentId"]]
                    new_name = str(row["Session Name"]).strip()
                    rename_session(session, new_name)
                    db.collection("sessions").document(row["_documentId"]).update({
                        "active": row["Status"] == "Active",
                        "updatedAt": firestore.SERVER_TIMESTAMP,
                    })

                st.success("Session table updated.")
                st.rerun()


def exams_page():
    st.header("2. Register examination")
    sessions = load_collection("sessions")
    if not sessions:
        st.warning("Register a session first.")
        return

    session_map = {item.get("sessionName", "Unnamed session"): item for item in sessions}
    with st.form("exam_form", clear_on_submit=True):
        session_choice = st.selectbox("Session", list(session_map))
        course_code = st.text_input(
            "Course code",
            placeholder="DFK50083",
            help="The course code is also used as the examination ID.",
        )
        course_name = st.text_input("Course name")
        enrollment_key = st.text_input("Enrollment key", type="password")
        col3, col4, col5 = st.columns(3)
        exam_date = col3.date_input("Exam date")
        start_time = col4.time_input("Start time", value=time(8, 30))
        end_time = col5.time_input("End time", value=time(10, 30))
        active = st.checkbox("Active", value=True)
        submitted = st.form_submit_button("Register examination", type="primary")

    if submitted:
        document_id = normalize_id(course_code)
        selected_session = session_map[session_choice]
        if not all([document_id, course_name.strip(), enrollment_key.strip()]):
            st.error("All examination fields are required.")
        elif end_time <= start_time:
            st.error("End time must be later than start time.")
        elif db.collection("exams").document(document_id).get().exists:
            st.error("That course already has a registered examination.")
        else:
            db.collection("exams").document(document_id).set({
                "examId": document_id,
                "sessionName": selected_session["sessionName"],
                "courseCode": document_id,
                "courseName": course_name.strip(),
                "enrollmentKey": enrollment_key.strip(),
                "examDate": exam_date.isoformat(),
                "startTime": start_time.strftime("%H:%M"),
                "endTime": end_time.strftime("%H:%M"),
                "active": active,
                "createdAt": firestore.SERVER_TIMESTAMP,
            })
            st.success(f"Examination for {document_id} registered.")
            st.rerun()

    exams = load_collection("exams")
    if exams:
        st.subheader("Edit registered examinations")
        st.caption("Correct the table cells, then select Save examination changes.")

        editable_rows = []
        for exam in exams:
            editable_rows.append({
                "_documentId": exam["_documentId"],
                "Session": exam.get("sessionName", "-"),
                "Course Code": exam.get("courseCode", exam["_documentId"]),
                "Course Name": exam.get("courseName", ""),
                "Exam Date": exam.get("examDate", ""),
                "Start Time": exam.get("startTime", "08:30"),
                "End Time": exam.get("endTime", "10:30"),
                "Active": exam.get("active", True),
            })

        edited_exams = st.data_editor(
            pd.DataFrame(editable_rows),
            hide_index=True,
            use_container_width=True,
            disabled=["Session", "Course Code"],
            column_config={"_documentId": None},
            num_rows="fixed",
            key="exam_editor",
        )

        if st.button("Save examination changes", type="primary"):
            errors = []
            for _, row in edited_exams.iterrows():
                start_value = str(row["Start Time"]).strip()
                end_value = str(row["End Time"]).strip()
                try:
                    start_parsed = datetime.strptime(start_value, "%H:%M")
                    end_parsed = datetime.strptime(end_value, "%H:%M")
                except ValueError:
                    errors.append(f"{row['Course Code']}: use HH:MM for start and end time")
                    continue
                if end_parsed <= start_parsed:
                    errors.append(f"{row['Course Code']}: end time must be after start time")
                    continue
                if not str(row["Course Name"]).strip() or not str(row["Exam Date"]).strip():
                    errors.append(f"{row['Course Code']}: course name and date are required")
                    continue

                db.collection("exams").document(row["_documentId"]).update({
                    "courseName": str(row["Course Name"]).strip(),
                    "examDate": str(row["Exam Date"]).strip(),
                    "startTime": start_value,
                    "endTime": end_value,
                    "active": bool(row["Active"]),
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                })

            if errors:
                st.error("\n".join(errors))
            else:
                st.success("Examination table updated.")
                st.rerun()

        with st.expander("Replace an enrollment key"):
            key_exam_map = {
                item.get("courseCode", item["_documentId"]): item["_documentId"]
                for item in exams
            }
            key_exam = st.selectbox(
                "Course",
                list(key_exam_map),
                key="key_exam",
            )
            replacement_key = st.text_input("New enrollment key", type="password")
            if st.button("Update enrollment key"):
                if not replacement_key.strip():
                    st.error("Enter a new enrollment key.")
                else:
                    db.collection("exams").document(key_exam_map[key_exam]).update({
                        "enrollmentKey": replacement_key.strip(),
                        "updatedAt": firestore.SERVER_TIMESTAMP,
                    })
                    st.success("Enrollment key updated.")


def locations_page():
    st.header("3. Add examination locations")
    exams = load_collection("exams")
    if not exams:
        st.warning("Register an examination first.")
        return

    st.caption(
        "One examination can have many classes/locations. Add each class and "
        "its location; repeat to add more."
    )

    exam_map = {exam_label(item): item for item in exams}
    with st.form("location_form", clear_on_submit=True):
        exam_choice = st.selectbox("Examination", list(exam_map))
        col_class, col_location = st.columns(2)
        class_name = col_class.text_input("Class", placeholder="DDT1A")
        location_name = col_location.text_input("Location name", placeholder="Lab 1")
        submitted = st.form_submit_button("Add class / location", type="primary")

    if submitted:
        exam = exam_map[exam_choice]
        clean_class = class_name.strip()
        clean_name = location_name.strip()

        # A class/location is a duplicate only when the SAME exam already has the
        # same class AND the same location. Different classes may share a lab, and
        # a class may (in theory) appear once per exam only.
        duplicate = any(
            item.get("examId") == exam.get("examId")
            and str(item.get("className", "")).strip().casefold() == clean_class.casefold()
            and str(item.get("locationName", "")).strip().casefold() == clean_name.casefold()
            for item in load_collection_where("exam_locations", "examId", exam.get("examId"))
        )

        if not clean_class:
            st.error("Class is required.")
        elif not clean_name:
            st.error("Location name is required.")
        elif duplicate:
            st.error("That class/location already exists for this examination.")
        else:
            location_reference = db.collection("exam_locations").document()
            location_reference.set({
                "locationId": location_reference.id,
                "examId": exam["examId"],
                "sessionName": exam["sessionName"],
                "courseCode": exam["courseCode"],
                "className": clean_class,
                "locationName": clean_name,
                "createdAt": firestore.SERVER_TIMESTAMP,
            })
            st.success(f"Added {clean_class} → {clean_name}.")
            st.rerun()

    locations = load_collection("exam_locations")
    if locations:
        location_rows = [{
            "Course": item.get("courseCode", "-"),
            "Class": item.get("className", "-"),
            "Location": item.get("locationName", "-"),
        } for item in locations]
        st.dataframe(pd.DataFrame(location_rows), hide_index=True, use_container_width=True)


def roster_page():
    st.header("4. Upload location roster")
    st.caption("Required Excel columns: Student ID, Student Name, Class")

    exams = load_collection("exams")
    locations = load_collection("exam_locations")
    if not exams or not locations:
        st.warning("Register an examination and at least one location first.")
        return

    exam_map = {exam_label(item): item for item in exams}
    exam_choice = st.selectbox("Examination", list(exam_map))
    exam = exam_map[exam_choice]
    matching_locations = [item for item in locations if item.get("examId") == exam.get("examId")]
    if not matching_locations:
        st.warning("This examination has no locations.")
        return

    location_map = {location_label(item): item for item in matching_locations}
    location_choice = st.selectbox("Location", list(location_map))
    location = location_map[location_choice]
    uploaded_file = st.file_uploader("Excel or CSV roster", type=["xlsx", "csv"])

    if uploaded_file is None:
        return

    try:
        roster = parse_roster(uploaded_file)
    except Exception as error:
        st.error(str(error))
        return

    st.success(f"Validated {len(roster)} students.")
    st.dataframe(roster, hide_index=True, use_container_width=True)

    if st.button("Import students", type="primary", use_container_width=True):
        # Only read this examination's registrations, not every student in the
        # whole exam_students collection.
        existing_students = load_collection_where(
            "exam_students", "examId", exam.get("examId")
        )
        existing_by_student = {}
        for item in existing_students:
            student_key = normalize_id(item.get("studentId", ""))
            existing_by_student.setdefault(student_key, []).append(item)

        conflicts = []
        for student_id in roster["studentId"]:
            student_key = normalize_id(student_id)
            assigned_locations = {
                item.get("locationId")
                for item in existing_by_student.get(student_key, [])
            }
            if assigned_locations and assigned_locations != {location["locationId"]}:
                conflicts.append(student_id)

        if conflicts:
            st.error(
                "Students already assigned to another location: "
                + ", ".join(conflicts[:20])
            )
            return

        batch = db.batch()
        for row in roster.to_dict("records"):
            student_id = normalize_id(row["studentId"])
            registration_id = f"{exam['examId']}_{student_id}"
            reference = db.collection("exam_students").document(registration_id)
            batch.set(reference, {
                "registrationId": registration_id,
                "sessionName": exam["sessionName"],
                "examId": exam["examId"],
                "courseCode": exam["courseCode"],
                "locationId": location["locationId"],
                "locationName": location["locationName"],
                "studentId": student_id,
                "studentName": row["studentName"],
                "className": row["className"],
                "status": "registered",
                "updatedAt": firestore.SERVER_TIMESTAMP,
            })
        batch.commit()
        st.success(f"Imported {len(roster)} students into {location['locationName']}.")


def registered_students_page():
    st.header("Registered students")
    st.caption("Review rosters by examination and location, audit duplicates, or remove mistaken registrations.")

    exams = load_collection("exams")

    if not exams:
        st.info("No examinations are registered.")
        return

    exam_map = {exam_label(item): item for item in exams}
    exam_choice = st.selectbox("Examination", list(exam_map), key="students_exam")
    exam = exam_map[exam_choice]

    # Query only the selected examination's students and locations in Firestore,
    # instead of loading the full collections and filtering in Python. This keeps
    # Firestore document reads proportional to one examination, not the whole DB.
    exam_students = load_collection_where(
        "exam_students", "examId", exam.get("examId")
    )
    exam_locations = load_collection_where(
        "exam_locations", "examId", exam.get("examId")
    )

    st.metric("Students registered for this examination", len(exam_students))

    if not exam_students:
        st.info("No students have been uploaded for this examination.")
        return

    audit_frame = pd.DataFrame([{
        "Student ID": normalize_id(item.get("studentId", "")),
        "Student Name": item.get("studentName", "-"),
        "Location": item.get("locationName", "-"),
        "Location ID": item.get("locationId", "-"),
    } for item in exam_students])

    duplicate_mask = audit_frame.duplicated(subset=["Student ID"], keep=False)
    duplicate_rows = audit_frame[duplicate_mask].sort_values("Student ID")
    if not duplicate_rows.empty:
        st.error(
            f"Duplicate audit failed: {duplicate_rows['Student ID'].nunique()} "
            "student(s) are registered more than once for this examination."
        )
        st.dataframe(
            duplicate_rows.drop(columns=["Location ID"]),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.success("Duplicate audit passed: each Student ID appears only once in this examination.")

    location_map = {
        item.get("locationName", "Unnamed location"): item
        for item in exam_locations
    }
    selected_location_name = st.selectbox(
        "View location",
        ["All locations"] + list(location_map),
        key="students_location",
    )

    if selected_location_name == "All locations":
        displayed_students = exam_students
    else:
        selected_location = location_map[selected_location_name]
        displayed_students = [
            item for item in exam_students
            if item.get("locationId") == selected_location.get("locationId")
        ]

    # Sort by class then student ID for a stable, readable list, then number them.
    displayed_students = sorted(
        displayed_students,
        key=lambda s: (
            str(s.get("className", "")).strip().casefold(),
            normalize_id(s.get("studentId", "")),
        ),
    )

    display_rows = [{
        "Bil": position,
        "Select": False,
        "_documentId": item["_documentId"],
        "Student ID": item.get("studentId", "-"),
        "Student Name": item.get("studentName", "-"),
        "Class": item.get("className", "-"),
        "Location": item.get("locationName", "-"),
        "Subject": item.get("courseCode", exam.get("examId", "-")),
        "Status": item.get("status", "registered"),
    } for position, item in enumerate(displayed_students, start=1)]

    st.subheader(f"Student list · {selected_location_name}")
    if display_rows:
        selection_key = normalize_id(
            f"{exam.get('examId')}_{selected_location_name}"
        )
        selected_table = st.data_editor(
            pd.DataFrame(display_rows),
            hide_index=True,
            use_container_width=True,
            disabled=["Bil", "Student ID", "Student Name", "Class", "Location", "Subject", "Status"],
            column_config={
                "_documentId": None,
                "Bil": st.column_config.NumberColumn("Bil", width="small"),
                "Select": st.column_config.CheckboxColumn(
                    "Select",
                    help="Tick students to delete",
                    default=False,
                ),
            },
            num_rows="fixed",
            key=f"student_delete_table_{selection_key}",
        )

        selected_rows = selected_table[selected_table["Select"]]
        selected_count = len(selected_rows)
        st.caption(f"{selected_count} student(s) selected")

        confirm_selected = st.checkbox(
            "I confirm that I want to delete the selected student registrations.",
            key=f"confirm_selected_{selection_key}",
        )
        if st.button(
            f"Delete selected ({selected_count})",
            disabled=selected_count == 0 or not confirm_selected,
            key=f"delete_selected_{selection_key}",
        ):
            deleted = delete_documents_by_ids(
                "exam_students",
                selected_rows["_documentId"].tolist(),
            )
            st.success(f"Deleted {deleted} selected student registration(s).")
            st.rerun()
    else:
        st.info("No students are registered in this location.")

    if selected_location_name != "All locations":
        st.divider()
        st.subheader("Delete all students in this location")
        st.warning(
            f"This removes all {len(displayed_students)} student registrations from "
            f"{selected_location_name}. The examination and location remain."
        )
        confirm_all = st.text_input(
            'Type "DELETE ALL" to confirm',
            key="confirm_delete_location_students",
        )
        if st.button("Delete all students in selected location", type="primary"):
            if confirm_all != "DELETE ALL":
                st.error('Enter "DELETE ALL" exactly.')
            else:
                deleted = delete_documents_by_field(
                    "exam_students",
                    "locationId",
                    location_map[selected_location_name]["locationId"],
                )
                st.success(f"Deleted {deleted} student registrations.")
                st.rerun()

    # ---- EDIT STUDENT (move class/location) ---------------------------------
    st.divider()
    with st.expander("Edit a student (move class / location)"):
        st.caption(
            "Use this when a lab is full and a student must be moved to another "
            "location. Only Class and Location change — the student's ID and "
            "subject stay the same."
        )

        if not exam_locations:
            st.info("Add at least one class/location to this examination first.")
        else:
            student_options = {
                f"{s.get('studentId', '-')} · {s.get('studentName', '-')} "
                f"({s.get('className', '-')} → {s.get('locationName', '-')})": s
                for s in displayed_students
            }
            if not student_options:
                st.info("No students to edit in this view.")
            else:
                pick = st.selectbox(
                    "Student",
                    list(student_options),
                    key="edit_student_pick",
                )
                student = student_options[pick]

                loc_choices = {location_label(loc): loc for loc in exam_locations}
                # Default the dropdown to the student's current location if possible.
                current_loc_label = None
                for label, loc in loc_choices.items():
                    if loc.get("locationId") == student.get("locationId"):
                        current_loc_label = label
                        break

                with st.form(f"edit_student_form_{student['_documentId']}"):
                    new_class = st.text_input(
                        "Class",
                        value=student.get("className", ""),
                    )
                    new_loc_label = st.selectbox(
                        "Location",
                        list(loc_choices),
                        index=(
                            list(loc_choices).index(current_loc_label)
                            if current_loc_label in loc_choices else 0
                        ),
                    )
                    save_student = st.form_submit_button("Save changes", type="primary")

                if save_student:
                    if not new_class.strip():
                        st.error("Class is required.")
                    else:
                        target_loc = loc_choices[new_loc_label]
                        db.collection("exam_students").document(
                            student["_documentId"]
                        ).update({
                            "className": new_class.strip(),
                            "locationId": target_loc.get("locationId"),
                            "locationName": target_loc.get("locationName"),
                            "updatedAt": firestore.SERVER_TIMESTAMP,
                        })
                        st.success(
                            f"Moved {student.get('studentId', '-')} to "
                            f"{new_class.strip()} → {target_loc.get('locationName')}."
                        )
                        st.rerun()

    # ---- ADD STUDENT --------------------------------------------------------
    st.divider()
    with st.expander("Add a student"):
        st.caption(
            "Add a student who was left out of the roster, without re-uploading "
            "the whole Excel file."
        )

        if not exam_locations:
            st.info("Add at least one class/location to this examination first.")
        else:
            add_loc_choices = {location_label(loc): loc for loc in exam_locations}
            with st.form("add_student_form", clear_on_submit=True):
                add_id = st.text_input("Student ID", placeholder="13DIT24F001")
                add_name = st.text_input("Student name")
                add_class = st.text_input("Class", placeholder="DDT1B")
                add_loc_label = st.selectbox("Location", list(add_loc_choices))
                add_submit = st.form_submit_button("Add student", type="primary")

            if add_submit:
                student_id = normalize_id(add_id)
                errors = []
                if not student_id:
                    errors.append("Student ID is required.")
                if not add_name.strip():
                    errors.append("Student name is required.")
                if not add_class.strip():
                    errors.append("Class is required.")

                registration_id = f"{exam['examId']}_{student_id}"
                if student_id and db.collection("exam_students").document(
                    registration_id
                ).get().exists:
                    errors.append("That student is already registered for this examination.")

                if errors:
                    st.error("\n".join(errors))
                else:
                    target_loc = add_loc_choices[add_loc_label]
                    db.collection("exam_students").document(registration_id).set({
                        "registrationId": registration_id,
                        "sessionName": exam.get("sessionName", ""),
                        "examId": exam.get("examId"),
                        "courseCode": exam.get("courseCode", exam.get("examId")),
                        "locationId": target_loc.get("locationId"),
                        "locationName": target_loc.get("locationName"),
                        "studentId": student_id,
                        "studentName": add_name.strip(),
                        "className": add_class.strip(),
                        "status": "registered",
                        "updatedAt": firestore.SERVER_TIMESTAMP,
                    })
                    st.success(
                        f"Added {student_id} ({add_name.strip()}) to "
                        f"{target_loc.get('locationName')}."
                    )
                    st.rerun()


def remove_examination(exam):
    """Delete an examination and everything that depends on it.

    Removes the exam document plus its locations, student registrations and
    monitoring records, so no orphaned data is left behind.
    """
    exam_id = exam.get("examId", exam.get("_documentId"))
    deleted = {}

    for collection_name in [
        "exam_monitoring",
        "exam_students",
        "exam_locations",
    ]:
        deleted[collection_name] = delete_documents_by_field(
            collection_name, "examId", exam_id
        )

    db.collection("exams").document(exam["_documentId"]).delete()
    deleted["exams"] = 1
    return deleted


def registered_exams_page():
    st.subheader("Registered examinations")
    st.caption(
        "Every examination that has been created. Search, then select one to "
        "view its full details and class/location list."
    )

    exams = load_collection("exams")
    if not exams:
        st.info("No examinations are registered yet. Create one under Examinations.")
        return

    locations = load_collection("exam_locations")

    # Count how many class/location rows belong to each examination.
    location_count_by_exam = {}
    for location in locations:
        exam_id = location.get("examId")
        if exam_id:
            location_count_by_exam[exam_id] = location_count_by_exam.get(exam_id, 0) + 1

    search = st.text_input(
        "Search",
        placeholder="Course code or course name",
        key="registered_exams_search",
    ).strip().casefold()

    def matches(exam):
        if not search:
            return True
        haystack = " ".join([
            str(exam.get("courseCode", "")),
            str(exam.get("courseName", "")),
            str(exam.get("sessionName", "")),
        ]).casefold()
        return search in haystack

    filtered_exams = [exam for exam in exams if matches(exam)]
    filtered_exams = sorted(
        filtered_exams,
        key=lambda e: str(e.get("courseCode", e.get("examId", ""))).casefold(),
    )

    if not filtered_exams:
        st.warning("No examinations match your search.")
        return

    table_rows = [{
        "Course": exam.get("courseCode", exam["_documentId"]),
        "Course Name": exam.get("courseName", "-"),
        "Session": exam.get("sessionName", "-"),
        "Date": exam.get("examDate", "-"),
        "Time": f"{exam.get('startTime', '-')} - {exam.get('endTime', '-')}",
        "Locations": location_count_by_exam.get(exam.get("examId"), 0),
        "Active": "Yes" if exam.get("active", False) else "No",
    } for exam in filtered_exams]

    st.dataframe(pd.DataFrame(table_rows), hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("View examination details")

    exam_map = {exam_label(exam): exam for exam in filtered_exams}
    view_choice = st.selectbox(
        "Examination",
        list(exam_map),
        key="registered_exams_view_choice",
    )
    selected_exam = exam_map[view_choice]

    if st.button("View details", type="primary", key="registered_exams_view_button"):
        st.session_state["registered_exams_viewing"] = selected_exam.get("examId")

    if st.session_state.get("registered_exams_viewing") == selected_exam.get("examId"):
        with st.container(border=True):
            st.markdown(f"### {selected_exam.get('courseCode', '-')} · {selected_exam.get('courseName', '-')}")

            detail_cols = st.columns(2)
            detail_cols[0].markdown(f"**Session**\n\n{selected_exam.get('sessionName', '-')}")
            detail_cols[1].markdown(f"**Date**\n\n{selected_exam.get('examDate', '-')}")

            detail_cols2 = st.columns(2)
            detail_cols2[0].markdown(
                f"**Time**\n\n{selected_exam.get('startTime', '-')} - {selected_exam.get('endTime', '-')}"
            )

            # ---- Enrollment Key + inline Add/Edit button --------------------
            current_key = str(selected_exam.get("enrollmentKey", "") or "").strip()
            with detail_cols2[1]:
                key_label_col, key_button_col = st.columns([3, 1])
                key_label_col.markdown(
                    f"**Enrollment Key**\n\n{current_key if current_key else '-'}"
                )
                edit_key_state = f"editing_key_{selected_exam.get('examId')}"
                button_text = "Edit" if current_key else "Add"
                if key_button_col.button(
                    button_text,
                    key=f"toggle_key_{selected_exam.get('examId')}",
                ):
                    st.session_state[edit_key_state] = not st.session_state.get(
                        edit_key_state, False
                    )

                if st.session_state.get(edit_key_state, False):
                    with st.form(f"inline_key_form_{selected_exam.get('examId')}"):
                        new_key = st.text_input(
                            "Enrollment key",
                            value=current_key,
                            key=f"inline_key_input_{selected_exam.get('examId')}",
                        )
                        save_key = st.form_submit_button("Save", type="primary")
                    if save_key:
                        if not new_key.strip():
                            st.error("Enter an enrollment key.")
                        else:
                            db.collection("exams").document(
                                selected_exam["_documentId"]
                            ).update({
                                "enrollmentKey": new_key.strip(),
                                "updatedAt": firestore.SERVER_TIMESTAMP,
                            })
                            st.session_state[edit_key_state] = False
                            st.success("Enrollment key saved.")
                            st.rerun()

            st.markdown("**Classes / Locations**")
            exam_locations = load_collection_where(
                "exam_locations", "examId", selected_exam.get("examId")
            )
            # Firestore does not guarantee order without order_by, so sort here
            # for a stable, readable list: by time (morning first), then class.
            exam_locations = sorted(
                exam_locations,
                key=lambda loc: (
                    str(loc.get("startTime", "")).strip(),
                    str(loc.get("className", "")).strip().casefold(),
                ),
            )
            if exam_locations:
                location_rows = [{
                    "Class": item.get("className", "-"),
                    "Location": item.get("locationName", "-"),
                    "Time": location_time(item, selected_exam),
                } for item in exam_locations]
                st.dataframe(
                    pd.DataFrame(location_rows),
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.info("No classes/locations added for this examination yet.")

    # ---- EDIT EXAMINATION ---------------------------------------------------
    st.divider()
    with st.expander("Edit examination"):
        st.caption("Course code is the examination ID and cannot be changed.")

        sessions = load_collection("sessions")
        session_names = [s.get("sessionName", "") for s in sessions if s.get("sessionName")]
        current_session = selected_exam.get("sessionName", "")
        if current_session and current_session not in session_names:
            session_names = [current_session] + session_names

        with st.form(f"edit_exam_form_{selected_exam.get('examId')}"):
            st.text_input(
                "Course code (fixed)",
                value=selected_exam.get("courseCode", ""),
                disabled=True,
            )
            edit_course_name = st.text_input(
                "Course name",
                value=selected_exam.get("courseName", ""),
            )
            edit_session = st.selectbox(
                "Session",
                session_names if session_names else [current_session],
                index=(session_names.index(current_session) if current_session in session_names else 0),
            )
            edit_date = st.text_input(
                "Exam date (YYYY-MM-DD)",
                value=selected_exam.get("examDate", ""),
            )
            edit_key = st.text_input(
                "Enrollment key",
                value=selected_exam.get("enrollmentKey", ""),
            )
            edit_active = st.checkbox("Active", value=selected_exam.get("active", False))
            save_changes = st.form_submit_button("Save changes", type="primary")

        if save_changes:
            errors = []
            if not edit_course_name.strip():
                errors.append("Course name is required.")
            if not edit_date.strip():
                errors.append("Exam date is required.")
            if not edit_key.strip():
                errors.append("Enrollment key is required.")

            if errors:
                st.error("\n".join(errors))
            else:
                update_payload = {
                    "courseName": edit_course_name.strip(),
                    "examDate": edit_date.strip(),
                    "enrollmentKey": edit_key.strip(),
                    "active": bool(edit_active),
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                }
                # Keep sessionName consistent across dependent collections.
                if edit_session and edit_session != current_session:
                    update_payload["sessionName"] = edit_session
                    for dependent in ["exam_locations", "exam_students", "exam_monitoring"]:
                        for doc in load_collection_where(
                            dependent, "examId", selected_exam.get("examId")
                        ):
                            db.collection(dependent).document(doc["_documentId"]).update(
                                {"sessionName": edit_session}
                            )

                db.collection("exams").document(selected_exam["_documentId"]).update(update_payload)
                st.success("Examination details updated.")
                st.rerun()

        # ---- EDIT CLASS/LOCATION TIMES (per class/location) -----------------
        st.markdown("**Edit class/location times**")
        st.caption(
            "Each class/location has its own time. Change the Start/End cells "
            "(use HH:MM), then Save class/location times."
        )
        edit_locations = load_collection_where(
            "exam_locations", "examId", selected_exam.get("examId")
        )
        edit_locations = sorted(
            edit_locations,
            key=lambda loc: (
                str(loc.get("startTime", "")).strip(),
                str(loc.get("className", "")).strip().casefold(),
            ),
        )
        if edit_locations:
            loc_rows = [{
                "_documentId": loc["_documentId"],
                "Class": loc.get("className", "-"),
                "Location": loc.get("locationName", "-"),
                "Start": str(loc.get("startTime", selected_exam.get("startTime", ""))).strip(),
                "End": str(loc.get("endTime", selected_exam.get("endTime", ""))).strip(),
            } for loc in edit_locations]

            edited_locs = st.data_editor(
                pd.DataFrame(loc_rows),
                hide_index=True,
                use_container_width=True,
                disabled=["Class", "Location"],
                column_config={"_documentId": None},
                num_rows="fixed",
                key=f"edit_locs_{selected_exam.get('examId')}",
            )

            if st.button(
                "Save class/location times",
                key=f"save_loc_times_{selected_exam.get('examId')}",
            ):
                loc_errors = []
                for _, r in edited_locs.iterrows():
                    s = str(r["Start"]).strip()
                    e = str(r["End"]).strip()
                    try:
                        sp = datetime.strptime(s, "%H:%M")
                        ep = datetime.strptime(e, "%H:%M")
                        if ep <= sp:
                            loc_errors.append(f"{r['Class']}: end must be after start")
                            continue
                    except ValueError:
                        loc_errors.append(f"{r['Class']}: use HH:MM for time")
                        continue
                    db.collection("exam_locations").document(r["_documentId"]).update({
                        "startTime": s,
                        "endTime": e,
                        "updatedAt": firestore.SERVER_TIMESTAMP,
                    })

                if loc_errors:
                    st.error("\n".join(loc_errors))
                else:
                    st.success("Class/location times updated.")
                    st.rerun()
        else:
            st.info("No classes/locations to edit for this examination.")

    # ---- REMOVE EXAMINATION (with confirmation) -----------------------------
    st.divider()
    with st.expander("Remove examination"):
        st.warning(
            "Removing an examination permanently deletes it along with its "
            "classes/locations, student registrations and monitoring records."
        )
        st.markdown(
            f"**{selected_exam.get('courseCode', '-')}** · "
            f"{selected_exam.get('courseName', '-')} · "
            f"{selected_exam.get('sessionName', '-')}"
        )

        confirm_remove = st.checkbox(
            "I understand this cannot be undone.",
            key=f"confirm_remove_{selected_exam.get('examId')}",
        )
        if st.button(
            "Remove examination",
            type="primary",
            disabled=not confirm_remove,
            key=f"remove_exam_button_{selected_exam.get('examId')}",
        ):
            deleted = remove_examination(selected_exam)
            st.session_state.pop("registered_exams_viewing", None)
            st.success(
                f"Removed {selected_exam.get('courseCode', '-')} and "
                f"{sum(deleted.values())} related document(s)."
            )
            st.rerun()


@st.fragment(run_every="10s")
def live_monitoring_table(exam_id, selected_class="All classes"):
    if exam_id == "All examinations":
        st.caption(f"Live · refreshed {datetime.now().strftime('%H:%M:%S')}")
        st.info("Select an examination to view its latest monitoring events.")
        return

    from datetime import timedelta, timezone
    from google.cloud.firestore_v1.field_path import FieldPath

    rows_by_exam = st.session_state.setdefault(
        "live_monitoring_rows_by_exam",
        {},
    )
    last_created_at_by_exam = st.session_state.setdefault(
        "live_monitoring_last_created_at_by_exam",
        {},
    )
    initialized_exams = st.session_state.setdefault(
        "live_monitoring_initialized_exams",
        set(),
    )
    cursor_by_exam = st.session_state.setdefault(
        "live_monitoring_cursor_by_exam",
        {},
    )
    empty_since_by_exam = st.session_state.setdefault(
        "live_monitoring_empty_since_by_exam",
        {},
    )

    cached_rows = rows_by_exam.setdefault(exam_id, [])
    cursor_snapshot = cursor_by_exam.get(exam_id)
    document_id_field = FieldPath.document_id()

    try:
        if exam_id not in initialized_exams:
            query = (
                db.collection("exam_monitoring")
                .where("examId", "==", exam_id)
                .order_by("createdAt", direction=firestore.Query.DESCENDING)
                .order_by(document_id_field, direction=firestore.Query.DESCENDING)
                .limit(50)
            )
            documents = list(query.stream())
            documents.reverse()
            initialized_exams.add(exam_id)

            if not documents:
                empty_since_by_exam[exam_id] = (
                    datetime.now(timezone.utc) - timedelta(seconds=30)
                )
        elif cursor_snapshot is not None:
            query = (
                db.collection("exam_monitoring")
                .where("examId", "==", exam_id)
                .order_by("createdAt", direction=firestore.Query.ASCENDING)
                .order_by(document_id_field, direction=firestore.Query.ASCENDING)
                .start_after(cursor_snapshot)
                .limit(50)
            )
            documents = list(query.stream())
        else:
            empty_since = empty_since_by_exam[exam_id]
            query = (
                db.collection("exam_monitoring")
                .where("examId", "==", exam_id)
                .where("createdAt", ">", empty_since)
                .order_by("createdAt", direction=firestore.Query.ASCENDING)
                .order_by(document_id_field, direction=firestore.Query.ASCENDING)
                .limit(50)
            )
            documents = list(query.stream())

        known_document_ids = {
            row["_documentId"]
            for row in cached_rows
        }

        # A document written with createdAt = serverTimestamp() can briefly have
        # a null createdAt before the server resolves it. We must NOT advance the
        # cursor past such a document, or once its timestamp resolves it could
        # fall behind the ">" window and be skipped forever (a missed violation).
        # So: add rows to the display, but only move the cursor to the newest
        # document that already has a resolved (non-null) createdAt.
        newest_resolved_document = None

        for document in documents:
            if document.id not in known_document_ids:
                event = document.to_dict()
                cached_rows.append({
                    "_documentId": document.id,
                    "Course": event.get(
                        "courseCode",
                        event.get("examId", "-"),
                    ),
                    "Location": event.get("locationName", event.get("locationId", "-")),
                    "Student ID": event.get("student", event.get("studentId", "-")),
                    "Student Name": event.get("studentName", "-"),
                    "PC": event.get("pc", "-"),
                    "Source": event.get("source", "-"),
                    "Violation": event.get("violation", "-"),
                    "Details": event.get("details", "-"),
                    "Time": event.get("time", "-"),
                    "_className": str(event.get("className", "")).strip(),
                    "_createdAt": event.get("createdAt"),
                })
                known_document_ids.add(document.id)

            # Track the newest document whose createdAt is already resolved.
            if document.get("createdAt") is not None:
                newest_resolved_document = document

        # Only advance the cursor to a document with a resolved timestamp. Any
        # document still showing a null createdAt stays "before" the cursor and
        # will be picked up (and de-duplicated by document ID) on a later refresh.
        if newest_resolved_document is not None:
            last_created_at_by_exam[exam_id] = newest_resolved_document.get("createdAt")
            cursor_by_exam[exam_id] = newest_resolved_document
            empty_since_by_exam.pop(exam_id, None)

        cached_rows[:] = cached_rows[-50:]
        rows_by_exam[exam_id] = cached_rows

    except Exception as error:
        st.error(
            "Unable to load incremental monitoring records. "
            "Firestore may require an examId + createdAt composite index. "
            "Open the link in the error below to create it."
        )
        st.code(str(error))

    # ---- FACE DETECTION ----------------------------------------------------
    # Read head-down events from the face_detection collection and merge them
    # into the Admin live view too. Simple where(examId) query (no order_by) so
    # no extra composite index is needed.
    face_rows = []
    try:
        for fdoc in db.collection("face_detection").where("examId", "==", exam_id).stream():
            fevent = fdoc.to_dict()
            face_rows.append({
                "_documentId": fdoc.id,
                "_className": str(fevent.get("className", "")).strip(),
                "_createdAt": fevent.get("createdAt"),
                "Student Name": fevent.get("studentName", "-"),
                "Student ID": fevent.get("studentId", "-"),
                "PC": fevent.get("pc", "-"),
                "Course": fevent.get("courseCode", fevent.get("examId", "-")),
                "Location": fevent.get("locationName", fevent.get("locationId", "-")),
                "Source": "Face Detection",
                "Violation": "Suspicious",
                "Details": fevent.get("details", "-"),
                "Time": fevent.get("time", "-"),
            })
    except Exception:
        pass

    # Combine monitoring + face detection.
    combined = list(cached_rows) + face_rows

    # Sort ALL rows by createdAt (server timestamp) so monitoring and face
    # detection events appear in the correct chronological order, newest first.
    def _sort_key(row):
        ts = row.get("_createdAt")
        try:
            dt = ts if isinstance(ts, datetime) else (ts.ToDatetime() if ts else None)
        except Exception:
            dt = None
        # Rows without a resolved timestamp are treated as "now" (just created).
        if dt is None:
            return datetime.max.replace(tzinfo=None)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt

    combined.sort(key=_sort_key, reverse=True)   # newest first

    # Apply the class filter (if a specific class is selected) before display.
    if selected_class and selected_class != "All classes":
        target = selected_class.strip().casefold()
        combined = [
            row for row in combined
            if str(row.get("_className", "")).strip().casefold() == target
        ]

    rows = [
        {
            key: value
            for key, value in row.items()
            if key not in ("_documentId", "_className", "_createdAt")
        }
        for row in combined
    ]

    st.caption(f"Live · refreshed {datetime.now().strftime('%H:%M:%S')}")
    if rows:
        render_monitoring_html(rows)
    else:
        st.info("No monitoring events found.")


def monitoring_page():
    st.header("Live monitoring")
    exams = load_collection("exams")
    exam_ids = ["All examinations"] + [item.get("examId", item["_documentId"]) for item in exams]
    selected_exam = st.selectbox("Filter by examination", exam_ids)

    # Class filter: list the classes defined for the selected examination.
    selected_class = "All classes"
    if selected_exam != "All examinations":
        exam_locations = load_collection_where("exam_locations", "examId", selected_exam)
        class_names = sorted({
            str(loc.get("className", "")).strip()
            for loc in exam_locations
            if str(loc.get("className", "")).strip()
        })
        selected_class = st.selectbox(
            "Filter by class",
            ["All classes"] + class_names,
        )

    live_monitoring_table(selected_exam, selected_class)


def _create_examination_section():
    """CREATE EXAMINATION with an inline draft list of class/location rows.

    The class/location rows are collected in st.session_state before the exam is
    created. On "Create examination" we write the exam document plus one
    exam_locations document per drafted class/location (keeping the existing
    collection structure so Student/roster/monitoring are unaffected).
    """
    st.subheader("Create examination")

    sessions = load_collection("sessions")
    if not sessions:
        st.warning("Register a session first (under Sessions).")
        return

    session_names = [s.get("sessionName", "") for s in sessions if s.get("sessionName")]

    # Draft list of {className, locationName} held in session_state.
    draft = st.session_state.setdefault("create_exam_locations", [])

    # --- Add a class/location (with its own time) to the draft ---------------
    st.markdown("**Classes / locations for this examination**")
    st.caption(
        "Each class/location has its own start and end time, so one subject can "
        "run a morning session for some classes and an afternoon session for others."
    )
    add_cols = st.columns([2, 2, 1.3, 1.3, 1])
    new_class = add_cols[0].text_input("Class", key="draft_class", placeholder="DDT1A")
    new_location = add_cols[1].text_input("Location", key="draft_location", placeholder="Lab 1")
    new_start = add_cols[2].time_input("Start", value=time(8, 30), key="draft_start")
    new_end = add_cols[3].time_input("End", value=time(11, 30), key="draft_end")
    add_cols[4].markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
    if add_cols[4].button("+ Add", key="draft_add"):
        c = new_class.strip()
        loc = new_location.strip()
        if not c or not loc:
            st.warning("Enter both class and location before adding.")
        elif new_end <= new_start:
            st.warning("End time must be after start time.")
        elif any(
            d["className"].casefold() == c.casefold()
            and d["locationName"].casefold() == loc.casefold()
            for d in draft
        ):
            st.warning("That class/location is already in the list.")
        else:
            draft.append({
                "className": c,
                "locationName": loc,
                "startTime": new_start.strftime("%H:%M"),
                "endTime": new_end.strftime("%H:%M"),
            })
            st.rerun()

    if draft:
        head = st.columns([2, 2, 2, 1])
        head[0].markdown("**Class**")
        head[1].markdown("**Location**")
        head[2].markdown("**Time**")
        head[3].markdown("**​**")
        for index, item in enumerate(list(draft)):
            row = st.columns([2, 2, 2, 1])
            row[0].write(item["className"])
            row[1].write(item["locationName"])
            row[2].write(f"{item.get('startTime', '-')} - {item.get('endTime', '-')}")
            if row[3].button("Remove", key=f"draft_remove_{index}"):
                draft.pop(index)
                st.rerun()
    else:
        st.caption("No class/location added yet. Add at least one above.")

    st.divider()

    # --- Examination details + Create ----------------------------------------
    with st.form("create_exam_form"):
        session_choice = st.selectbox("Session", session_names)
        course_code = st.text_input("Course code", placeholder="DFK40473")
        course_name = st.text_input("Course name", placeholder="Web Development")
        enrollment_key = st.text_input("Enrollment key", type="password")
        exam_date = st.date_input("Exam date")
        active = st.checkbox("Active", value=True)
        create = st.form_submit_button("Create examination", type="primary")

    if create:
        document_id = normalize_id(course_code)
        errors = []
        if not document_id:
            errors.append("Course code is required.")
        if not course_name.strip():
            errors.append("Course name is required.")
        if not enrollment_key.strip():
            errors.append("Enrollment key is required.")
        if not draft:
            errors.append("Add at least one class/location (with its time).")
        if document_id and db.collection("exams").document(document_id).get().exists:
            errors.append("That course already has a registered examination.")

        if errors:
            st.error("\n".join(errors))
        else:
            # Exam-level time is a fallback only; the first drafted row's time is
            # used so older displays still show something sensible.
            fallback_start = draft[0].get("startTime", "08:30")
            fallback_end = draft[0].get("endTime", "11:30")

            db.collection("exams").document(document_id).set({
                "examId": document_id,
                "sessionName": session_choice,
                "courseCode": document_id,
                "courseName": course_name.strip(),
                "enrollmentKey": enrollment_key.strip(),
                "examDate": exam_date.isoformat(),
                "startTime": fallback_start,
                "endTime": fallback_end,
                "active": active,
                "createdAt": firestore.SERVER_TIMESTAMP,
            })
            for item in draft:
                location_ref = db.collection("exam_locations").document()
                location_ref.set({
                    "locationId": location_ref.id,
                    "examId": document_id,
                    "sessionName": session_choice,
                    "courseCode": document_id,
                    "className": item["className"],
                    "locationName": item["locationName"],
                    "startTime": item.get("startTime", fallback_start),
                    "endTime": item.get("endTime", fallback_end),
                    "createdAt": firestore.SERVER_TIMESTAMP,
                })

            st.session_state["create_exam_locations"] = []
            st.success(
                f"Examination {document_id} created with {len(draft)} class/location(s)."
            )
            st.rerun()


def examination_page():
    st.header("Examination")
    st.caption(
        "Create examinations (with their classes/locations), bulk-upload via "
        "Excel, and manage every registered examination — all in one place."
    )

    tab_create, tab_upload, tab_registered = st.tabs([
        "Create examination",
        "Upload exam file",
        "Registered examinations",
    ])

    with tab_create:
        _create_examination_section()

    with tab_upload:
        upload_exams_page()

    with tab_registered:
        registered_exams_page()


def dashboard_page():
    load_design_system()

    with st.sidebar:
        logo_b64 = _logo_base64()
        if logo_b64:
            brand_mark = (
                f'<span class="brand-hexagon">'
                f'<img class="brand-logo-img" src="data:image/png;base64,{logo_b64}" alt="logo">'
                f'</span>'
            )
        else:
            brand_mark = '<span class="brand-mark">S</span>'

        st.markdown(
            f"""
            <div class="brand-lockup">
                {brand_mark}
                <span class="brand-name">SMART EXAM</span>
                <div class="brand-version">ADMIN CONSOLE</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div class='page-kicker'>Workspace</div>", unsafe_allow_html=True)
        page = st.radio(
            "Navigation",
            [
                "Overview",
                "Sessions",
                "Examination",
                "Roster Upload",
                "Registered Students",
                "Live Monitoring",
            ],
            format_func=lambda item: {
                "Overview": "▦   Overview",
                "Sessions": "◷   Sessions",
                "Examination": "▤   Examination",
                "Roster Upload": "⇧   Roster Upload",
                "Registered Students": "♙   Registered Students",
                "Live Monitoring": "◉   Live Monitoring",
            }[item],
            label_visibility="collapsed",
        )
        st.divider()
        st.caption("Signed in as Administrator")
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.session_token = ""
            # Bersihkan URL params supaya tak auto-login semula.
            st.query_params.clear()
            st.rerun()


    pages = {
        "Overview": overview_page,
        "Sessions": sessions_page,
        "Examination": examination_page,
        "Roster Upload": roster_page,
        "Registered Students": registered_students_page,
        "Live Monitoring": monitoring_page,
    }
    pages[page]()
