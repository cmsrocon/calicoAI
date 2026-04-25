# calicoAI

calicoAI is a multi-topic news monitor that fetches articles from trusted sources, consolidates duplicate coverage into single story entries, runs each story through an LLM pipeline, and presents the result in a searchable interface with topic scoping, balanced summaries, source-document links, entity and theme tagging, trends, and graph exploration.

---

## What it does

- Fetches RSS and HTML sources per topic.
- Merges duplicate coverage of the same story into one canonical entry.
- Preserves multiple source-document links on the canonical story.
- Generates summaries, why-it-matters context, pros, cons, and a balanced view that highlights differences in framing or opinion across sources.
- Tags stories with entities and themes.
- Shows trends and a graph view globally or per topic.
- Tracks live ingestion progress, token usage, and estimated LLM cost.

---

## Table of contents

1. [Prerequisites](#prerequisites)
2. [Getting the code](#getting-the-code)
3. [Backend setup](#backend-setup)
4. [Frontend setup](#frontend-setup)
5. [API keys and providers](#api-keys-and-providers)
6. [First run](#first-run)
7. [Daily automation](#daily-automation)
8. [Environment variables](#environment-variables)
9. [Architecture](#architecture)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Install these first:

- Python 3.11 or 3.12
- Node.js 20 LTS
- Git

Verify:

```powershell
python --version
node --version
npm --version
git --version
```

Python 3.13+ is not recommended for this project.

---

## Getting the code

```powershell
git clone https://github.com/YOUR_USERNAME/calicoAI.git
cd calicoAI
```

Replace `YOUR_USERNAME/calicoAI` with the real repository URL.

---

## Backend setup

Run all commands in `backend`:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

The backend API explorer will be available at `http://localhost:8000/docs`.

---

## Frontend setup

Open a second terminal and run all commands in `frontend`:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

---

## API keys and providers

calicoAI needs an LLM for story distillation, tagging, topic seeding, and trend generation.

### Anthropic

Add to `backend/.env`:

```env
ANTHROPIC_API_KEY=sk-ant-...
```

Default model: `claude-sonnet-4-6`

### OpenAI

Add to `backend/.env`:

```env
OPENAI_API_KEY=sk-proj-...
```

Then switch the provider in Settings.

### Ollama

Install Ollama locally and point the app at the local OpenAI-compatible endpoint.

---

## First run

Make sure both servers are running:

- Backend on `8000`
- Frontend on `5173`

Then:

1. Open `http://localhost:5173`
2. Go to `Settings` and run `Test connection`
3. Review topic sources in `Settings`
4. Use the header `Refresh` control to refresh the current topic or all topics
5. Wait for ingestion to complete

After the first successful run:

- `Daily News` fills with canonical story entries instead of repeated duplicate coverage
- each story can expose multiple source documents in the detail panel
- the balanced view calls out where sources agree and where they differ
- `Entities`, `Themes`, and `Trends` populate from processed stories
- `Graph` shows linked entities and themes globally or within the selected topic

---

## Daily automation

The backend runs an automatic ingestion daily at `06:00` UTC by default.

To change the schedule:

1. Open `Settings`
2. Change `Schedule hour` and `Schedule minute`
3. Save

The scheduler restarts automatically.

---

## Environment variables

Create `backend/.env` from `backend/.env.example`.

| Variable | Default | Description |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | - | Required for Anthropic |
| `OPENAI_API_KEY` | - | Required for OpenAI |
| `MINIMAX_API_KEY` | - | Required for MiniMax |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Override if Ollama runs elsewhere |
| `DATABASE_URL` | `sqlite+aiosqlite:///./ginger.db` | SQLite database path |

---

## Architecture

```text
calicoAI/
|-- backend/
|   |-- alembic/
|   |-- app/
|   |   |-- api/
|   |   |-- models/
|   |   |-- schemas/
|   |   |-- services/
|   |   |-- utils/
|   |   `-- main.py
|   `-- seeds/
`-- frontend/
    `-- src/
        |-- api/
        |-- components/
        |-- pages/
        |-- store/
        `-- types/
```

### Core backend services

- `scraper_service.py`: fetches RSS and HTML sources
- `dedup_service.py`: exact dedup plus semantic story clustering
- `llm_service.py`: provider abstraction and JSON-safe prompting
- `ingestion_service.py`: orchestration for fetch, dedup, relevance, distillation, tagging, and trends
- `trend_service.py`: builds overall, entity, and theme trend narratives

### Frontend views

- `Daily News`: canonical stories with balanced summaries and source links
- `Entities`: recurring tagged entities
- `Themes`: recurring themes
- `Trends`: topic, entity, and theme trend narratives
- `Graph`: node-link view of entity and theme relationships, globally or per topic

### Ingestion pipeline

| Stage | What happens | LLM calls |
| --- | --- | --- |
| 1 - Fetch | Downloads active RSS and HTML sources in parallel | 0 |
| 2 - Hash dedup | Removes exact duplicates already stored | 0 |
| 3 - Semantic dedup | Groups near-duplicate coverage into story bundles | 1 batch |
| 4 - Relevance filter | Scores each story bundle for topic relevance | 1 per story bundle |
| 5 - AI analysis | Distills each story bundle into one balanced story entry with source links, summary, pros, cons, and tags | 1 per relevant story bundle |
| 5b - Complete incomplete | Reprocesses failed or partial story entries | 1 per incomplete story |
| 6 - Trend analysis | Builds trend narratives per topic, entity, and theme | 1 per active entity or theme plus overall summaries |
| 7 - Finalise | Writes run stats, costs, and summary metadata | 0 |

### Story consolidation

calicoAI does not try to show every article separately when several sources cover the same underlying story.

Instead it:

- detects near-duplicate coverage
- keeps one canonical story entry
- stores multiple source-document links on that story
- asks the LLM to produce a balanced summary across the grouped coverage
- uses the balanced view to surface differences in interpretation, criticism, or emphasis

---

## Troubleshooting

### PowerShell blocks `Activate.ps1`

Run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### `alembic upgrade head` fails

Make sure the backend virtual environment is active before running migrations.

### The frontend cannot load data

Make sure the backend is running:

```powershell
cd backend
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

### Articles appear without summaries

Run `Settings -> Test connection` and confirm the configured provider returns valid JSON. Failed or partial stories are retried on later runs.

### Ports 8000 or 5173 are already in use

Inspect the port:

```powershell
netstat -ano | findstr :8000
netstat -ano | findstr :5173
```

Then stop the conflicting process or switch ports.

---

## Local checklist

- Python installed
- Node installed
- Repo cloned
- Backend virtualenv created and activated
- Backend dependencies installed
- `.env` created
- Alembic migrations applied
- Backend running on `8000`
- Frontend dependencies installed
- Frontend running on `5173`

