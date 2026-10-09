# AI Smart Cleaner

Flask-based smart waste reporting and task management project.

## Requirements
- Python 3.12 or 3.13 recommended
- pip

Python 3.15 compatibility with all dependencies has not been verified. Use Python 3.12/3.13 for a predictable local setup.

## Windows PowerShell setup

From this project folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks activation, run commands with `.\.venv\Scripts\python.exe` instead of activating the environment.

## Initialize the database

Use either the Flask CLI commands below or the equivalent direct commands (`python run.py init-db` and `python run.py seed-data`). The entry point supports both forms; commands with arguments run the CLI instead of starting the web server:

```powershell
python -m flask --app run:app init-db
# or: python run.py init-db
```

Optional development/demo seed data:

```powershell
python -m flask --app run:app seed-data
# or: python run.py seed-data
```

**Security note:** `seed-data` creates predictable demo credentials. Use only for a local demonstration; do not expose those accounts on a public deployment. For a real admin account, use:

```powershell
python -m flask --app run:app create-admin
```

The command interactively asks for username, email, password, and full name.

## Start the application

```powershell
python run.py
```

Then open http://127.0.0.1:5000 in your browser.

## Tests

```powershell
python -m pytest -v
```

Use the project virtual environment's Python for all commands.

## Configuration and uploads
- `.env.example` contains example settings only. Never commit real `.env` secrets.
- SQLite data is stored under `instance/smart_cleaner.db` by default.
- Uploads are stored under `uploads/`.
- Back up the database and uploaded evidence together. Do not copy the `.venv` directory when sharing the project.

## Known verification status
This package has been cleaned of its bundled virtual environment, Python bytecode caches, pytest cache, and local SQLite database. Automated tests must be run in the configured local virtual environment; they have not been verified in this packaging environment.
