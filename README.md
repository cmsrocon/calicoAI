# GingerAI

AI landscape monitoring — daily ingestion, LLM analysis, vendor/vertical tracking.

## Quick Start

### 1. Backend

```bash
cd backend

# Create and activate virtual environment (already done)
# .venv\Scripts\activate   (Windows)

# Copy env and add your API key
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY=sk-ant-...

# Run migrations (already done, re-run if schema changes)
.venv\Scripts\alembic upgrade head

# Start backend
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

Backend runs at http://localhost:8000  
API docs at http://localhost:8000/docs

### 2. Frontend

Requires Node.js 18+ — download from https://nodejs.org

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173

### 3. First Run

1. Open http://localhost:5173
2. Go to **Settings** → verify your sources are listed
3. Go to **Settings** → **LLM Configuration** → click "Test connection"
4. Click **Refresh** in the top bar to run your first ingestion
5. News items appear in the **Daily News** tab within a few minutes

## Daily Automation

The backend automatically ingests at 06:00 every day (configurable in Settings → LLM Configuration).

## Environment Variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Required for Claude (default provider) |
| `OPENAI_API_KEY` | Required if switching to OpenAI |
| `DATABASE_URL` | SQLite path (default: `sqlite+aiosqlite:///./ginger.db`) |
