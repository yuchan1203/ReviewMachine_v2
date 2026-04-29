# ReviewMachine V2

This repository has been migrated from a Streamlit single-file app to a FastAPI backend with a static frontend.

How to run

1. Activate your venv:

```powershell
& .\venv\Scripts\Activate.ps1
```

2. Install dependencies (if not already installed):

```powershell
python -m pip install -r requirements.txt
```

3. Run the FastAPI server:

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

4. Open the frontend: http://127.0.0.1:8000/app/

Notes

- Streamlit-specific code was removed and replaced with server-side helpers. `web_app.py` remains as a migration shim explaining the new run method.
- Analysis results can be downloaded via `GET /download/analyzed/{app_id}` and stats via `GET /stats/{app_id}`.
