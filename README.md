# GingerAI

AI landscape monitor — fetches news from configured sources daily, runs every article through an LLM pipeline (relevance filtering, summarisation, vendor/sector tagging), and surfaces the results in a browsable interface with trends and cost tracking.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Getting the code](#getting-the-code)
3. [Backend setup](#backend-setup)
4. [Frontend setup](#frontend-setup)
5. [API keys and LLM providers](#api-keys-and-llm-providers)
6. [First run](#first-run)
7. [Daily automation](#daily-automation)
8. [Environment variable reference](#environment-variable-reference)
9. [Architecture overview](#architecture-overview)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Install these before you start. All are free.

### Python 3.11 or 3.12

Download the **Windows installer** from https://www.python.org/downloads/

During installation:
- ✅ Check **"Add Python to PATH"** on the first screen
- ✅ Check **"Install for all users"** (optional but recommended)

Verify in a new terminal:
```
python --version
```
Expected: `Python 3.11.x` or `Python 3.12.x`

> **Not 3.13** — some async SQLAlchemy internals have compatibility issues with 3.13 at the time of writing.

### Node.js 20 LTS

Download from https://nodejs.org — choose the **LTS** release for Windows.

Verify:
```
node --version
npm --version
```

### Git

Download from https://git-scm.com/download/win — use all default options during install.

Verify:
```
git --version
```

---

## Getting the code

Open **Command Prompt** or **PowerShell** and clone the repository:

```
git clone https://github.com/YOUR_USERNAME/gingerAI.git
cd gingerAI
```

Replace `YOUR_USERNAME/gingerAI` with the actual repository URL.

---

## Backend setup

All commands in this section are run from the `backend` folder.

### 1. Open a terminal in the backend folder

```
cd backend
```

### 2. Create a Python virtual environment

```
python -m venv .venv
```

This creates a `.venv` folder inside `backend`. It is gitignored and must be created on every new machine.

### 3. Activate the virtual environment

**Command Prompt:**
```
.venv\Scripts\activate.bat
```

**PowerShell:**
```
.venv\Scripts\Activate.ps1
```

> If PowerShell blocks the script with an execution policy error, run this first (once per machine):
> ```
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

Your prompt will change to show `(.venv)` when the environment is active.

### 4. Install Python dependencies

```
pip install -r requirements.txt
```

This installs FastAPI, SQLAlchemy, Anthropic SDK, OpenAI SDK, APScheduler, feedparser, and all other backend dependencies.

### 5. Create the environment file

```
copy .env.example .env
```

Then open `.env` in any text editor (Notepad is fine) and fill in your API key. See [API keys and LLM providers](#api-keys-and-llm-providers) below.

### 6. Create the database and run migrations

```
.venv\Scripts\alembic upgrade head
```

This creates `ginger.db` (a SQLite file) in the `backend` folder and applies all schema migrations. Re-run this command any time you pull new changes — it is safe to run multiple times.

### 7. Start the backend server

```
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

The backend stays running in this terminal. Leave it open.

**API explorer:** http://localhost:8000/docs

---

## Frontend setup

Open a **second** terminal window. All commands here are run from the `frontend` folder.

### 1. Open a terminal in the frontend folder

```
cd frontend
```

(From the repo root: `cd gingerAI\frontend`)

### 2. Install JavaScript dependencies

```
npm install
```

This installs React, Vite, TailwindCSS, Tanstack Query, and all other frontend packages into `node_modules`. This folder is gitignored and must be created on every new machine.

### 3. Start the development server

```
npm run dev
```

You should see:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
```

Open http://localhost:5173 in your browser.

---

## API keys and LLM providers

GingerAI needs an LLM to analyse articles. The default provider is Anthropic (Claude). You need at least one key.

### Option A — Anthropic (Claude) — recommended

1. Create an account at https://console.anthropic.com
2. Go to **API Keys** and create a new key
3. Add to your `backend/.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-...
   ```

The default model is `claude-sonnet-4-6`. Cost is roughly **$0.10–$0.50 per ingestion run** depending on the number of sources and articles.

### Option B — OpenAI

1. Create an account at https://platform.openai.com
2. Add billing under **Settings → Billing**
3. Create an API key under **API keys**
4. Add to your `backend/.env`:
   ```
   OPENAI_API_KEY=sk-proj-...
   ```
5. In the app, go to **Settings → LLM Configuration** and switch the provider to `openai` and model to `gpt-4o-mini` (cheapest) or `gpt-4o`.

> ChatGPT Plus / Pro subscriptions do **not** include API access. The API is billed separately per token.

### Option C — Ollama (free, runs locally)

1. Download and install Ollama from https://ollama.com
2. Pull a model: `ollama pull llama3.2` (or `qwen2.5`, `mistral`, etc.)
3. Ollama starts automatically on http://localhost:11434
4. In the app, switch provider to `ollama` and set the model name to match what you pulled

Local models are free but slower and produce lower-quality structured JSON. Expect more incomplete articles.

---

## First run

Both servers must be running (backend on 8000, frontend on 5173).

1. Open http://localhost:5173
2. Go to **Settings** → scroll to **LLM Configuration** → click **Test connection** to verify your API key works
3. Go to **Settings** → scroll to **Sources** — you should see a list of pre-seeded RSS feeds. Add or remove sources as needed.
4. Click the **Refresh** button in the top-right header to trigger your first ingestion
5. The button changes to a spinning **Running…** indicator. Click it to open a live progress panel showing:
   - Current pipeline stage (Fetching → Deduplication → Relevance filtering → AI analysis → Trends)
   - Per-item progress ("AI analysis 12/40: OpenAI announces…")
   - Live LLM call count and estimated cost
6. After a few minutes (longer on the first run — every article needs LLM processing), the status changes to **success** and the **Daily News** tab populates
7. Click any article to open its detail panel. Articles that are not yet fully processed show a yellow banner listing what is still pending — they are automatically completed on the next run

---

## Daily automation

The backend schedules an automatic ingestion at **06:00 every day** (UTC). No action is needed.

To change the schedule:
1. Go to **Settings → LLM Configuration**
2. Change the **Schedule hour** and **Schedule minute** fields
3. The scheduler restarts automatically on save

The schedule persists in the SQLite database, not the `.env` file, so it survives deployments.

---

## Environment variable reference

Create `backend/.env` by copying `backend/.env.example`. All variables are optional except you need at least one LLM key.

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required if using Claude (default provider) |
| `OPENAI_API_KEY` | — | Required if switching provider to `openai` |
| `MINIMAX_API_KEY` | — | Required if switching to MiniMax |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Override if Ollama runs on a different port |
| `DATABASE_URL` | `sqlite+aiosqlite:///./ginger.db` | Path to the SQLite database file |

---

## Architecture overview

```
gingerAI/
├── backend/                 Python / FastAPI
│   ├── app/
│   │   ├── api/             REST endpoints (news, vendors, verticals, ingestion, trends, settings)
│   │   ├── models/          SQLAlchemy ORM models
│   │   ├── schemas/         Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── ingestion_service.py   7-stage pipeline orchestrator
│   │   │   ├── llm_service.py         LLM abstraction (Anthropic / OpenAI / Ollama)
│   │   │   ├── scraper_service.py     RSS + HTML fetching
│   │   │   ├── dedup_service.py       Hash + semantic deduplication
│   │   │   ├── trend_service.py       Trend analysis
│   │   │   ├── vendor_service.py      Vendor CRUD
│   │   │   └── vertical_service.py    Sector CRUD
│   │   ├── scheduler.py     APScheduler daily trigger
│   │   └── main.py          FastAPI app + lifespan startup
│   ├── alembic/             Database migrations
│   └── seeds/               Default RSS sources
└── frontend/                React / TypeScript / Vite / TailwindCSS
    └── src/
        ├── api/             Axios API client functions
        ├── components/      UI components (layout, news, vendors, trends…)
        ├── pages/           Top-level page components
        ├── store/           Zustand state (active tab, filters)
        └── types/           TypeScript interfaces
```

### Ingestion pipeline (7 stages)

| Stage | What happens | LLM calls |
|---|---|---|
| 1 — Fetch | Downloads all active RSS/HTML sources in parallel | 0 |
| 2 — Hash dedup | Removes articles already stored with full processing | 0 |
| 3 — Semantic dedup | Sends similar-title pairs to LLM to catch near-duplicates | 1 batch |
| 4 — Relevance filter | Scores every article 0–1 for AI industry relevance, drops <0.4 | 1 per article |
| 5 — AI analysis | Full LLM processing: summary, why-it-matters, pros/cons, vendor tags, sector tags | 1 per relevant article |
| 5b — Complete incomplete | Re-runs stage 5 on any articles from previous runs that failed processing | 1 per incomplete article |
| 6 — Trend analysis | Generates narrative trend summaries per vendor, sector, and overall | 1 per active vendor/sector + 1 overall |
| 7 — Finalise | Saves token counts, estimated cost, and run summary to database | 0 |

### Database

SQLite file at `backend/ginger.db`. Not committed to git. Back this file up if you want to preserve your article history.

Key tables: `news_items`, `vendors`, `verticals`, `ingestion_runs`, `sources`, `trends`, `app_settings`.

---

## Troubleshooting

### `python` is not recognised

Python was not added to PATH during installation. Either reinstall Python and check "Add to PATH", or use the full path: `C:\Users\YOU\AppData\Local\Programs\Python\Python312\python.exe`.

### PowerShell blocks `.venv\Scripts\Activate.ps1`

Run once: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### `alembic upgrade head` fails with "No module named alembic"

The virtual environment is not active. Run `.venv\Scripts\activate.bat` (Command Prompt) or `.venv\Scripts\Activate.ps1` (PowerShell) first.

### Backend starts but articles have no summaries

The LLM key is missing or invalid. Check:
1. `backend/.env` exists (not `.env.example`)
2. The key starts with the right prefix (`sk-ant-` for Anthropic, `sk-proj-` for OpenAI)
3. Go to **Settings → LLM Configuration → Test connection**

The first ingestion saves articles with `is_processed = false` if the LLM call fails. The next run automatically retries all incomplete articles (Stage 5b). Check the processing error by clicking an article in the Daily News tab.

### Frontend shows "Failed to fetch" or blank pages

The backend is not running. Start it with `.venv\Scripts\uvicorn app.main:app --reload --port 8000` from the `backend` folder with the virtual environment active.

### Port 8000 or 5173 already in use

Kill whatever is using the port:
```
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```
Or start on a different port: `uvicorn app.main:app --port 8001` and update `frontend/src/api/client.ts` to match.

### Running on a different machine — checklist

- [ ] Python 3.11 or 3.12 installed with PATH enabled
- [ ] Node.js 20 LTS installed
- [ ] `git clone` completed
- [ ] `cd backend && python -m venv .venv` run
- [ ] Virtual environment activated
- [ ] `pip install -r requirements.txt` completed
- [ ] `backend/.env` created from `.env.example` with at least one LLM API key
- [ ] `.venv\Scripts\alembic upgrade head` completed (creates `ginger.db`)
- [ ] Backend running: `.venv\Scripts\uvicorn app.main:app --reload --port 8000`
- [ ] `cd frontend && npm install` completed
- [ ] Frontend running: `npm run dev`
- [ ] http://localhost:5173 opens in browser
