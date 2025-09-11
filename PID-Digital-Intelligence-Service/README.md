PID Digital Intelligence - API & Frontend

Quick start

1. Create and activate a virtual environment (optional but recommended)

   - python -m venv .venv
   - .venv\\Scripts\\activate (Windows)

2. Install dependencies

   - pip install -r requirements.txt

3. Postgres setup

   - Ensure a Postgres instance is available
   - Default URL: postgresql+psycopg2://postgres:postgres@localhost:5432/pid_db
   - Override via env var DATABASE_URL
   - Create DB if not exists: createdb pid_db (or via pgAdmin)

4. Run the API

   - python api.py
   - Health check: GET http://localhost:8000/health
   - Process image: POST http://localhost:8000/process (form-data key: file)

5. Open the demo frontend
   - Open index.html in a browser
   - For local dev it calls http://localhost:8000

Notes

- Models expected at: best.pt and trocr-finetuned-pid-final/final
- Adjust paths inside pipeline_core.py if needed
- Streamlit app (app.py) remains for interactive exploration
