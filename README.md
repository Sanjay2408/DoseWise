# 💊 DoseWise

**A medication companion for older adults and the people who care for them.**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2+-61dafb.svg)](https://reactjs.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agent-orange.svg)](https://github.com/langchain-ai/langgraph)

DoseWise reminds patients to take their medicines, tracks doses, vitals and wellbeing, watches inventory levels, and gives caregivers a clear "what should I look at" summary — powered by a deterministic rule-based agent, with an optional LLM used only to write plain-language summaries (never to make medical decisions).

> DoseWise does not diagnose or prescribe. All escalation decisions are rule-based. Consult healthcare professionals for medical decisions.

## Features

**For the patient**
- Big, simple screens designed for older adults: large text (with an A / A+ / A++ size toggle), big tap targets, plain-language labels ("Take now", "Overdue"), and a full-screen ✓ confirmation after every tap so there's never doubt it registered
- One-tap dose confirmation with automatic inventory decrement
- On-screen reminders when a dose is due, with snooze
- A dedicated "How are you feeling?" screen for wellbeing and vitals (blood pressure, heart rate, temperature)
- Respects `prefers-reduced-motion` and has visible keyboard-focus outlines

**For the caregiver**
- Dashboard with alerts and the AI summary at the top, then trends, inventory, timeline and daily intelligence reports
- Rule-based trend detection (sustained high BP, repeated low wellbeing, low inventory, sugar instability after missed doses)
- Optional email alerts for missed doses and abnormal vitals (SMTP)
- Optional Gemini-written caregiver summaries with a safe rule-based fallback

**Under the hood**
- LangGraph agent: **observe → reason → plan → act** in one deterministic pass per run
- Actions: REMIND (due/missed doses), ESCALATE (abnormal vitals / trends), REORDER (low stock)
- Real accounts: registration + login with bcrypt password hashing and JWT sessions; every API endpoint is scoped to the signed-in user
- Per-user storage in SQLite (no shared state, no patient data in the repo)

## Architecture

```
frontend/  React 18 (CRA)                 backend/  FastAPI (Python 3.10+)
  ├─ pages: Login, Register, Dashboard,     ├─ app/auth.py         bcrypt + JWT
  │         Wellbeing, Setup, Caregiver     ├─ app/api/routes.py   REST endpoints (all authenticated)
  ├─ services/api.js  axios + JWT           ├─ app/agent/          LangGraph observe→reason→plan→act
  └─ services/auth.js session storage       ├─ app/intelligence/   rule-based trends + optional Gemini
                                            ├─ app/medication/     registry, schedule, inventory
                                            ├─ app/notifications/  reminders, escalation, SMTP email
                                            └─ app/storage/        SQLite (users + per-user state), images
```

The agent never loops: each `/api/agent/run` performs exactly one observe→reason→plan→act pass on the caller's own state, off the main thread, with a hard timeout.

## Getting started

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows   (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env       # optional — the app runs fine with everything blank
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm start                    # opens http://localhost:3000
```

### 3. First run

1. Open http://localhost:3000 and **create an account**.
2. Add the patient's details and medications on the **My Meds** (setup) page.
3. The **Home** page shows today's schedule with one big button per medicine.
4. The **Caregiver** page shows alerts, AI summaries, trends and daily reports.

## Environment variables (backend/.env)

All optional — see [backend/.env.example](backend/.env.example) for the full annotated list.

| Variable | Purpose |
|---|---|
| `JWT_SECRET` | Signs login tokens. Auto-generated and persisted if unset. |
| `CORS_ORIGINS` | Allowed frontend origins (default `http://localhost:3000`). |
| `GEMINI_API_KEY` | Enables LLM-written caregiver summaries (falls back to rule-based text without it). |
| `SMTP_USERNAME` / `SMTP_PASSWORD` / `CAREGIVER_EMAIL` | Enables caregiver email alerts. |

For the frontend, `REACT_APP_API_URL` overrides the API base URL (default `http://localhost:8000/api`).

## API overview

All endpoints below require `Authorization: Bearer <token>` and operate on the signed-in user's own data.

| Method & path | What it does |
|---|---|
| `POST /api/auth/register` / `POST /api/auth/login` | Create an account / sign in (returns JWT) |
| `GET /api/state` | Full state (medications enriched with next dose time) |
| `POST /api/setup/medications` | Create or edit profile + medications |
| `POST /api/dose/confirm` | Mark a dose taken, decrement inventory, run the agent |
| `POST /api/vitals/submit` | Record vitals and/or wellbeing |
| `POST /api/agent/run` | One observe→reason→plan→act pass |
| `GET /api/alerts` · `GET /api/vitals/trends` · `GET /api/caregiver/daily-reports` | Caregiver dashboard data |
| `POST /api/inventory/update` · `POST /api/pharmacy/search` | Inventory & reorder helpers |

## Privacy & safety notes

- Patient data lives only in a local SQLite database (`backend/app/storage/dosewise.db`) and per-user image folders — both are gitignored and never committed.
- Passwords are bcrypt-hashed; sessions are signed JWTs.
- The LLM (if enabled) is used **only** to phrase summaries for caregivers. Escalation decisions are made by deterministic rules, and the LLM call has a hard timeout with a rule-based fallback.
