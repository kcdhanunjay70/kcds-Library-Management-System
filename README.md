# Leaf & Ledger — College Library Management System

A complete, responsive college library application built with Flask, MongoDB, HTML, CSS, and JavaScript. It combines a public searchable catalog with a secure librarian dashboard for inventory and circulation.

## Features

- Search books instantly by title, author, ISBN, subject, and category
- Responsive public catalog with availability and shelf locations
- Password-protected admin dashboard and inventory overview
- Add books and safely remove unissued inventory
- Issue books to students with an automatic 14-day due date
- Return books with automatic stock reconciliation
- Full transaction history with student, issue, due, return, and status data
- MongoDB persistence with seeded in-memory fallback for easy demonstrations
- Health API, automated tests, Docker, GitHub Actions, and Render deployment

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Visit `http://localhost:5000`. The development admin credentials are:

```text
Username: admin
Password: admin123
```

Change them before deployment. Start MongoDB locally for persistent storage; without it, the app uses temporary seeded memory storage.

### Windows launcher

PowerShell users can start the project with the included port-aware launcher:

```powershell
.\run-library.ps1
```

If another project already uses port 5000, choose a different port:

```powershell
.\run-library.ps1 -Port 5001
```

The launcher reports a clear error when the selected port is occupied instead of silently opening the wrong application.

## Docker

```bash
docker compose up --build
```

This starts the Flask application and MongoDB with a persistent `library_data` volume.

## Environment variables

| Variable | Purpose | Development default |
| --- | --- | --- |
| `SECRET_KEY` | Signs authenticated sessions | Random each process |
| `MONGO_URI` | MongoDB connection | `mongodb://localhost:27017/college_library` |
| `ADMIN_USERNAME` | Librarian username | `admin` |
| `ADMIN_PASSWORD_HASH` | Werkzeug password hash | Hash of `admin123` |
| `PORT` | Web server port | `5000` |

Generate a secure password hash:

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('your-password'))"
```

## Tests

```bash
python -m pytest -q
```

GitHub Actions runs the same command on every push and pull request to `main`.

## Deploy to Render

1. Create a MongoDB Atlas database and allow Render network access.
2. Create a Render Blueprint from this repository.
3. Supply `MONGO_URI` and `ADMIN_PASSWORD_HASH` when prompted by `render.yaml`.
4. Deploy. Render generates `SECRET_KEY` automatically.

## Project structure

```text
app.py                  Flask application and data layer
templates/              Catalog, login, admin, and transaction views
static/css/style.css    Responsive visual system
static/js/app.js        Search, filters, tables, and modals
tests/test_app.py       Route and circulation tests
run-library.ps1         Port-aware Windows launcher
.github/workflows/      Continuous integration
render.yaml             Render deployment blueprint
Dockerfile              Production container
docker-compose.yml      Local Flask + MongoDB stack
```

## License

Created for educational use.
