# SMART EXAM Admin V2

This version keeps the original `ADMIN` application unchanged and introduces the revised workflow:

1. Register a session using only its name and status.
2. Register an examination using its course code as the examination ID. Default time is 08:30–10:30.
3. Add one or more locations by name; Firebase creates the internal location reference.
4. Upload an `.xlsx` or `.csv` roster for each location.
5. Review registered students by location, audit duplicate Student IDs, and tick one or more mistaken registrations for deletion.
6. Review live monitoring events.

A completed session can be permanently deleted from Overview. The administrator must re-enter the Admin secret code; deletion removes its examinations, locations, rosters and monitoring records.

Overview also contains a collapsed development-database reset panel. It requires the Admin secret code, the exact phrase `RESET FIREBASE`, and a final acknowledgement before recursively deleting all Firestore collections.

The roster must contain these exact column names:

- `Student ID`
- `Student Name`
- `Class`

## Run

```powershell
cd "C:\Users\HP\Desktop\SMART EXAM\ADMIN_V2"
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

For local development, the app uses `../ADMIN/firebase_config.json` when no local credential file exists. You can instead set `SMART_EXAM_FIREBASE_CREDENTIALS` to the service-account JSON path.
